"""The distributive-container guard on the `single-entity` consumer.

SYNTHETIC ONLY (constitution rule 3). No GSM8K or ASDiv string appears here — the
mechanism is exercised on invented containers (tables/plates, boxes/pens), never
the benchmark item that surfaced it.

WHY IT EXISTS. A cross-corpus (ASDiv) confident-wrong: "There were 150 shelves.
Each shelf had 15 books. How many books were on the shelves?" The engine
synthesizes the correct group total (2250) AND folds the resolved container's own
per-container rate (15) — and committed the RATE. GSM8K could not reveal it (its
ask shapes happen not to resolve a counted container as the fold entity). The
sibling `unique-entity` consumer already declines this exact GroupTotal collision;
`single-entity` lacked the guard.

THE TIGHTNESS INVARIANT (the second test) is the load-bearing one: the guard must
NOT fire for a NAMED holder whose own fold is correct and merely coexists with an
unrelated document total — else it would break every legitimate named fold. The
container signature (the entity is itself a counted thing) is what keeps it tight.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import GroupTotal


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/gsm8k")).registry


def test_counted_container_with_group_total_declines(reg):
    """The core case. A counted container ('20 tables') holds a per-container
    rate ('each table had 6 plates') and saturate synthesizes the whole
    (GroupTotal plate=120). Folding the container's own 6 is a confident wrong —
    the guard declines instead."""
    r = solve(
        "There were 20 tables. Each table had 6 plates. How many plates were on the tables?",
        reg, tracing=False,
    )
    # the mechanism actually engaged: the whole was synthesized...
    assert any(g.measure == "plate" and g.value == 120.0 for g in r.store.by_kind(GroupTotal))
    # ...and the per-container rate was NOT committed as the answer.
    assert not r.answer.committed, f"committed {r.answer.value!r} (the per-container rate)"
    assert "counted container" in (r.answer.reason or "")


def test_named_holder_with_unrelated_total_still_commits(reg):
    """THE TIGHTNESS INVARIANT. A GroupTotal for the asked measure coexists, but
    the named holder is NOT a counted container — its own fold is correct and must
    survive. If this ever declines, the guard has gone as broad as the entity-less
    one and would break legitimate named folds."""
    r = solve(
        "There are 90 apples altogether. Rina has 5 apples. How many apples does Rina have?",
        reg, tracing=False,
    )
    assert any(g.measure == "apple" for g in r.store.by_kind(GroupTotal)), \
        "precondition: a group total for the asked measure must exist"
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == 5.0


def test_plain_single_entity_unaffected(reg):
    """Regression floor: with no group total in play the guard is inert."""
    r = solve("Rina has 5 apples. How many apples does Rina have?", reg, tracing=False)
    assert r.answer.committed
    assert r.answer.value == 5.0
