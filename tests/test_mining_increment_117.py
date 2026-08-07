"""Increment 117 — the deixis journal: recording what the engine THREW AWAY.

The Decision trace records MUTATIONS (target, before, after). A decline mutates nothing,
so it is structurally invisible to it: the designer can show every binding that
succeeded and not one that failed. But the declines are where all the information is —
at most of the fifteen resolution sites the entire candidate set is discarded with no
record kept anywhere, and nothing computes distance because, modulo obligations.py,
nothing has an origo to measure from.

`deixis.resolve` now takes an optional `journal`. THE TWO PROPERTIES THESE TESTS PIN:

  1. IT CANNOT CHANGE THE READING. `journal=None` is the default and takes a path that
     does exactly what the function did before the journal existed; and even WITH a
     journal attached, the returned winner is identical. Recording is observation, not
     participation. (Proven at the corpus level too: dev-train + dev-holdout snapshots
     byte-identical to main.)

  2. IT COSTS BENCH NOTHING. `solve(tracing=False)` builds no journal at all, so the
     recording path is never entered. This is not a micro-optimisation — trace
     snapshotting was once 61% of bench wall-clock, and that lesson is load-bearing.

Synthetic only (NEVER benchmark items).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import deixis

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def registry_full():
    """All packs. The end-to-end cases need the mined lexicon; the conftest `registry`
    fixture deliberately loads only core-english + arithmetic."""
    return compile_registry(
        load_packs([
            REPO / "packs/core-english",
            REPO / "packs/arithmetic",
            REPO / "packs/difg-mined",
        ])
    )


def person(key, sentence=None, span=None, payload=None):
    return deixis.Referent(
        dimension=deixis.PERSON, key=key, payload=payload, sentence=sentence, span=span
    )


def origo(sentence=1, span=(0, 0)):
    return deixis.Origo(sentence=sentence, span=span)


# ---------------------------------------------------------------------------
# 1. The journal cannot change the verdict
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "candidates",
    [
        [],
        [person("sam")],
        [person("sam"), person("mary")],
        [person("sam"), person("mary"), person("ann")],
    ],
    ids=["empty", "unique", "two", "three"],
)
def test_journal_never_changes_the_winner(candidates):
    """Recording is observation, not participation.

    The same candidate set must resolve identically whether or not anyone is watching.
    This is the whole safety argument for attaching a journal to a shared kernel
    primitive: it is a pure side-channel.
    """
    silent = deixis.resolve(list(candidates), origo(), deixis.constant)
    watched = deixis.resolve(
        list(candidates), origo(), deixis.constant, journal=deixis.Journal()
    )
    assert (silent is None) == (watched is None)
    if silent is not None:
        assert silent.key == watched.key


def test_untraced_solve_builds_no_journal(registry_full):
    """bench runs with tracing=False and must pay ZERO for the journal."""
    from rulekit.kernel.engine import solve

    text = "Sam has 3 apples. He found 5 more apples. How many apples does Sam have?"
    assert solve(text, registry_full, tracing=False).log.journal is None
    assert solve(text, registry_full, tracing=True).log.journal is not None


def test_untraced_and_traced_agree_on_the_answer(registry_full):
    """The journal must not perturb the answer it is watching."""
    from rulekit.kernel.engine import solve

    text = "Sam has 3 apples. He found 5 more apples. How many apples does Sam have?"
    quiet = solve(text, registry_full, tracing=False)
    loud = solve(text, registry_full, tracing=True)
    assert quiet.answer.kind == loud.answer.kind
    assert quiet.answer.value == loud.answer.value


# ---------------------------------------------------------------------------
# 2. The silent path calls nothing extra
#
# The recording path is allowed to call `distance` for candidates the silent path
# short-circuits past — that is why purity is a documented contract. But the SILENT
# path must not gain a single call, or bench pays for a feature it never uses.
# ---------------------------------------------------------------------------


def test_silent_path_makes_no_extra_distance_calls():
    calls = []

    def counting(referent, org):
        calls.append(referent.key)
        return 0

    # A lone survivor short-circuits before any ranking: zero distance calls.
    deixis.resolve([person("sam")], origo(), counting)
    assert calls == []


def test_silent_path_calls_each_filter_once_per_candidate():
    calls = []

    def keep(referent, org):
        calls.append(referent.key)
        return True

    deixis.resolve([person("a"), person("b")], origo(), deixis.constant, filters=[keep])
    assert calls == ["a", "b"]


def test_recording_path_calls_each_filter_once_per_candidate():
    """Recording must not double-call a filter to both decide AND attribute.

    Pure filters make a double call unobservable today — but it would silently become a
    behaviour change the day someone writes a stateful one.
    """
    calls = []

    def keep(referent, org):
        calls.append(referent.key)
        return True

    deixis.resolve(
        [person("a"), person("b")],
        origo(),
        deixis.constant,
        filters=[keep],
        journal=deixis.Journal(),
    )
    assert calls == ["a", "b"]


# ---------------------------------------------------------------------------
# 3. The decline reasons — the vocabulary the viewer renders
# ---------------------------------------------------------------------------


def test_reason_no_candidates():
    j = deixis.Journal()
    assert deixis.resolve([], origo(), journal=j) is None
    (obs,) = j.observations
    assert obs.outcome == "declined"
    assert obs.reason == "no-candidates"


def test_reason_tie_is_what_a_flat_field_produces():
    """Under the constant metric two candidates can NEVER be told apart.

    This is the thesis: with no reference point, "more than one" can only mean
    "ambiguous". The journal is what finally makes that visible.
    """
    j = deixis.Journal()
    assert deixis.resolve([person("sam"), person("mary")], origo(), journal=j) is None
    (obs,) = j.observations
    assert obs.reason == "tie"
    assert obs.arbitration is None
    assert [c.distance for c in obs.candidates] == [0, 0]


def test_reason_filtered_out():
    j = deixis.Journal()

    def never(referent, org):
        return False

    assert deixis.resolve(
        [person("sam")], origo(), filters=[never], journal=j
    ) is None
    (obs,) = j.observations
    assert obs.reason == "filtered-out"
    (cand,) = obs.candidates
    assert cand.eliminated_by == "filter:never"
    # Never ranked, so it has no distance — and says so rather than implying it lost.
    assert cand.distance is None


def test_reason_dimension_mismatch_is_the_month_bug_fingerprint():
    """A TIME referent competing to be a PERSON antecedent.

    This is docs/deixis.md §4 in miniature — a month name pollutes the person pool
    because referents carry no dimension type. `dimension-mismatch` is the ONLY
    observable that names that bug class, which is why it is worth distinguishing from
    a plain empty candidate set.
    """
    j = deixis.Journal()
    march = deixis.Referent(dimension=deixis.TIME, key="march")
    assert deixis.resolve(
        [march], origo(), dimension=deixis.PERSON, journal=j
    ) is None
    (obs,) = j.observations
    assert obs.reason == "dimension-mismatch"
    assert obs.candidates[0].eliminated_by == "dimension"


def test_a_win_under_the_constant_metric_is_always_unique_never_dominant():
    """100% "unique" is the proof that no real metric is live yet.

    The first "dominant" observation that ever appears is the moment one was switched
    on — which must be its own gated increment with its own TEST look.
    """
    j = deixis.Journal()
    assert deixis.resolve([person("sam")], origo(), deixis.constant, journal=j).key == "sam"
    (obs,) = j.observations
    assert obs.outcome == "bound"
    assert obs.arbitration == "unique"
    assert obs.metric == "constant"


def test_dominant_arbitration_appears_only_with_a_real_metric():
    j = deixis.Journal()
    near = person("near", sentence=0, span=(4, 4))
    far = person("far", sentence=0, span=(0, 0))
    winner = deixis.resolve(
        [far, near], origo(span=(5, 5)), deixis.token_distance, journal=j
    )
    assert winner.key == "near"
    (obs,) = j.observations
    assert obs.arbitration == "dominant"
    assert obs.metric == "token_distance"


# ---------------------------------------------------------------------------
# 4. Honest degradation — the rule that keeps the viewer truthful
# ---------------------------------------------------------------------------


def test_a_bare_string_candidate_records_no_position():
    """Most sites resolve over bare measure/entity strings with no span at all.

    The record must say `None`, not invent (0, 0). A viewer that fabricated a position
    for these would be drawing a field the engine does not have.
    """
    j = deixis.Journal()
    bare = deixis.Referent(dimension=deixis.DISCOURSE, key="ball")
    deixis.resolve([bare], origo(), dimension=deixis.DISCOURSE, journal=j)
    (cand,) = j.observations[0].candidates
    assert cand.span is None
    assert cand.sentence is None
    assert cand.uid is None


def test_a_unit_backed_candidate_recovers_its_uid_without_importing_model():
    class FakeUnit:
        uid = 7

    j = deixis.Journal()
    deixis.resolve(
        [person("sam", sentence=0, span=(3, 3), payload=FakeUnit())], origo(), journal=j
    )
    (cand,) = j.observations[0].candidates
    assert cand.uid == 7
    assert cand.span == (3, 3)
    assert cand.sentence == 0


# ---------------------------------------------------------------------------
# 5. The fixpoint repeat problem
#
# resolve() runs inside document.py's round loop. A binding that SUCCEEDS is skipped on
# later rounds — but a DECLINE is retried every single round, so every INTERESTING
# resolution is the repeated one. Naive appending would bury the reader.
# ---------------------------------------------------------------------------


def test_identical_repeats_collapse_into_one_row_with_a_count():
    j = deixis.Journal()
    for round_no in range(1, 6):
        j.round = round_no
        deixis.resolve([person("sam"), person("mary")], origo(), journal=j)
    (obs,) = j.observations
    assert obs.attempts == 5
    assert obs.round == 1  # the round it was FIRST seen


def test_a_changed_candidate_set_is_a_new_row_not_a_repeat():
    """The transition is the only thing worth watching.

    "Two candidates in round 1, one in round 2" is where the reading actually happened.
    Deduping on the call site alone would erase exactly that.
    """
    j = deixis.Journal()
    j.round = 1
    deixis.resolve([person("sam"), person("mary")], origo(), journal=j)
    j.round = 2
    deixis.resolve([person("sam")], origo(), journal=j)

    assert len(j.observations) == 2
    first, second = j.observations
    assert first.outcome == "declined" and first.reason == "tie" and first.round == 1
    assert second.outcome == "bound" and second.winner == "sam" and second.round == 2


def test_the_document_loop_journals_the_real_decline(registry_full):
    """End to end: ordinary discourse with two prior names stays ambiguous.

    With no typed gender/person compatibility and no question-local assumption,
    recency is not enough evidence to select an antecedent. The field remains flat.
    """
    from rulekit.kernel.engine import solve

    result = solve(
        "Sam has 3 apples. Mary has 4 apples. She found 5 more apples. "
        "How many apples does Mary have?",
        registry_full,
    )
    ties = [
        o
        for o in result.log.journal.observations
        if o.source == "bind-discourse" and o.reason == "tie"
    ]
    assert ties
    obs = ties[0]
    assert obs.dimension == deixis.PERSON
    assert {c.key for c in obs.candidates} == {"sam", "mary"}
    assert all(c.distance == 0 for c in obs.candidates)
