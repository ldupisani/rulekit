"""Tracing is an opt-out that must not change what the engine reads.

`Reading.record` snapshots a reversible before/after feature diff on every
mutation. Only the designer (`engine.trace`) and `Reading.undo` read those
diffs — a bench does not, and snapshotting them was 61% of bench wall-clock.
So `solve(..., tracing=False)` skips the snapshots.

The invariant these tests pin: tracing changes the TRACE, never the ANSWER.
Synthetic strings only (NEVER benchmark items).
"""

import pytest

from rulekit.kernel.engine import solve
from rulekit.kernel.model import Reading, Unit, Word

TEXTS = [
    "Tom has 3 apples. How many apples does Tom have?",
    "Tom has 10 coins. Tom finds 3 coins. Tom lost 2 coins. How many coins does Tom have?",
    "Mary has twice as many pens as Tom. Tom has 4 pens. How many pens does Mary have?",
    "Tom has 5 marbles. How many rocks does Tom have?",  # declines
]


@pytest.mark.parametrize("text", TEXTS)
def test_answer_identical_with_and_without_tracing(text, registry):
    traced = solve(text, registry, tracing=True).answer
    untraced = solve(text, registry, tracing=False).answer
    assert (traced.kind, traced.value) == (untraced.kind, untraced.value)
    assert traced.reason == untraced.reason


@pytest.mark.parametrize("text", TEXTS)
def test_facts_identical_with_and_without_tracing(text, registry):
    """The fact store is what answer.py consumes — it must not move."""
    traced = solve(text, registry, tracing=True)
    untraced = solve(text, registry, tracing=False)
    assert [repr(f) for f in traced.store.facts] == [repr(f) for f in untraced.store.facts]


def test_decisions_still_recorded_without_tracing(registry):
    """Only the diffs go away. The decision log itself stays intact."""
    text = TEXTS[1]
    traced = solve(text, registry, tracing=True)
    untraced = solve(text, registry, tracing=False)

    def spine(result):
        return [
            (d.seq, d.kind, d.target_uid, d.rule_id)
            for r in result.premises
            for d in r.decisions
        ]

    assert spine(traced) == spine(untraced)
    assert spine(untraced), "expected a non-empty decision log"


def test_diffs_present_when_tracing_and_empty_when_not(registry):
    traced = solve(TEXTS[1], registry, tracing=True)
    untraced = solve(TEXTS[1], registry, tracing=False)
    assert any(d.before or d.after for r in traced.premises for d in r.decisions)
    assert not any(d.before or d.after for r in untraced.premises for d in r.decisions)


def test_trace_survives_when_tracing_on(registry):
    """The designer's consumer still gets its events."""
    assert solve(TEXTS[1], registry, tracing=True).trace()


def test_undo_refuses_on_an_untraced_reading():
    """Loud failure, not silent corruption: there is no diff to restore from."""
    reading = Reading("synthetic", tracing=False)
    unit = reading.new_unit((Word("x", 0),))
    reading.units.append(unit)
    decision = reading.record("annotate", unit, {"sense": "noun"}, "test")
    with pytest.raises(RuntimeError, match="tracing=False"):
        reading.undo(decision)


def test_undo_still_works_when_tracing_on():
    """Undo restores the recorded `before` value.

    Note it restores None rather than removing a previously-absent key: `before`
    and `after` are built from the same `changes` keys, so undo's pop-branch
    (`key not in decision.after`) is unreachable. Pre-existing behaviour, pinned
    here as-is — this change only stops SNAPSHOTTING the diffs, it does not
    touch what undo does with them.
    """
    reading = Reading("synthetic", tracing=True)
    unit = reading.new_unit((Word("x", 0),))
    reading.units.append(unit)
    reading.record("annotate", unit, {"sense": "noun"}, "test")
    decision = reading.record("annotate", unit, {"sense": "verb"}, "test")
    reading.undo(decision)
    assert unit.features["sense"] == "noun"


def test_mutable_feature_is_snapshotted_not_aliased():
    """The immutable fast path must not leak into mutable values.

    A list feature stored in `before` has to be a copy; if it aliased the live
    value, later mutation would rewrite history and undo would restore garbage.
    """
    reading = Reading("synthetic", tracing=True)
    unit = reading.new_unit((Word("x", 0),))
    reading.units.append(unit)
    reading.record("annotate", unit, {"tags": ["a"]}, "test")
    decision = reading.record("annotate", unit, {"tags": ["a", "b"]}, "test")
    unit.features["tags"].append("c")  # mutate the live value after the fact
    assert decision.before["tags"] == ["a"]
    assert decision.after["tags"] == ["a", "b"]
