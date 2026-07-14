"""Increment 116 — the deixis seam: one primitive for the hand-written acceptance tests.

`docs/deixis.md` shows rulekit resolves referents at ~15 sites, each hand-writing the
SAME rule: "exactly one candidate in scope, else decline". That rule was never chosen as
a precision policy — it is the ONLY policy available with no reference point (origo) to
measure distance from, because unranked candidates can only be counted, not compared.

`kernel/deixis.py` supplies the missing primitive:

    resolve(candidates, origo, distance, filters) -> winner | None

with STRICT-DOMINANCE arbitration (nearest wins iff strictly nearer than every other
survivor; ties decline).

THE PROPERTY THESE TESTS EXIST TO PIN:

    Under a CONSTANT distance, strict dominance is unsatisfiable with 2+ survivors, so
    `resolve` degenerates EXACTLY to "unique candidate, or decline".

That is what makes migrating a site provably 0-DIFF (verified: dev-train, dev-holdout
and suite snapshots byte-identical). The real metrics are switched on later, one gated
increment each — the refactor and the behaviour change never ride together.

Synthetic only (NEVER benchmark items).
"""

import pytest

from rulekit.kernel import deixis
from rulekit.kernel.engine import solve


def _ref(dim, key, span=None, sentence=None, payload=None):
    return deixis.Referent(dimension=dim, key=key, span=span, sentence=sentence, payload=payload)


# ---------------------------------------------------------------------------
# The equivalence: constant distance == "unique candidate, or decline"
# ---------------------------------------------------------------------------


def test_one_candidate_binds():
    winner = deixis.resolve([_ref(deixis.PERSON, "sam")], deixis.Origo(), deixis.constant)
    assert winner is not None and winner.key == "sam"


def test_no_candidate_declines():
    assert deixis.resolve([], deixis.Origo(), deixis.constant) is None


@pytest.mark.parametrize("n", [2, 3, 5])
def test_two_or_more_candidates_decline_under_the_constant_metric(n):
    """THE LOAD-BEARING PROPERTY. Constant distance -> no strict dominance -> decline.

    This is what makes the migration byte-identical to the fifteen hand-written
    `len(candidates) == 1` tests. If this ever passes with a winner, every migrated
    site silently starts committing on ambiguity.
    """
    cands = [_ref(deixis.PERSON, f"name{i}", span=(i, i)) for i in range(n)]
    assert deixis.resolve(cands, deixis.Origo(span=(0, 0)), deixis.constant) is None


# ---------------------------------------------------------------------------
# Dimension typing — a TIME word must never be a PERSON antecedent
# ---------------------------------------------------------------------------


def test_a_candidate_of_another_dimension_is_not_a_rival():
    """The bug class increment 88 fixed by hand for weekdays, made unrepresentable.

    A time expression polluting the person antecedent pool is exactly what broke
    pronoun binding for weekday adjuncts. With typed referents the time candidate is
    not in the person's candidate set at all, so the person binds uniquely.
    """
    cands = [_ref(deixis.PERSON, "sam"), _ref(deixis.TIME, "monday")]
    winner = deixis.resolve(cands, deixis.Origo(), deixis.constant, dimension=deixis.PERSON)
    assert winner is not None and winner.key == "sam"


def test_dimension_filtering_can_still_leave_ambiguity():
    cands = [_ref(deixis.PERSON, "sam"), _ref(deixis.PERSON, "rita"), _ref(deixis.TIME, "monday")]
    assert deixis.resolve(cands, deixis.Origo(), deixis.constant, dimension=deixis.PERSON) is None


# ---------------------------------------------------------------------------
# Strict dominance, once a real metric is switched on
# ---------------------------------------------------------------------------


def test_token_distance_picks_the_strictly_nearest():
    origo = deixis.Origo(span=(10, 10))
    cands = [_ref(deixis.PERSON, "far", span=(1, 1)), _ref(deixis.PERSON, "near", span=(9, 9))]
    winner = deixis.resolve(cands, origo, deixis.token_distance)
    assert winner is not None and winner.key == "near"


def test_an_exact_tie_declines_even_with_a_real_metric():
    """Ties are ambiguity. Ambiguity declines.

    deixis.md §6: any change that makes arbitration LESS strict is a confident-wrong
    factory. Equidistant candidates must never produce a winner.
    """
    origo = deixis.Origo(span=(5, 5))
    cands = [_ref(deixis.PERSON, "left", span=(3, 3)), _ref(deixis.PERSON, "right", span=(7, 7))]
    assert deixis.resolve(cands, origo, deixis.token_distance) is None


# ---------------------------------------------------------------------------
# Filters are precision-only: they may only SHRINK a candidate set
# ---------------------------------------------------------------------------


def test_a_filter_can_disambiguate_but_never_invent_a_candidate():
    cands = [_ref(deixis.PERSON, "sam"), _ref(deixis.PERSON, "rita")]
    assert deixis.resolve(cands, deixis.Origo(), deixis.constant) is None
    only_sam = deixis.resolve(
        cands, deixis.Origo(), deixis.constant, filters=(lambda c, o: c.key == "sam",)
    )
    assert only_sam is not None and only_sam.key == "sam"
    # a filter that rejects everything declines — it cannot conjure a referent
    assert (
        deixis.resolve(cands, deixis.Origo(), deixis.constant, filters=(lambda c, o: False,))
        is None
    )


def test_resolution_is_deterministic_regardless_of_candidate_order():
    """A set's iteration order must never be able to decide a binding."""
    origo = deixis.Origo(span=(10, 10))
    a = _ref(deixis.PERSON, "far", span=(1, 1))
    b = _ref(deixis.PERSON, "near", span=(9, 9))
    assert deixis.resolve([a, b], origo, deixis.token_distance).key == "near"
    assert deixis.resolve([b, a], origo, deixis.token_distance).key == "near"


# ---------------------------------------------------------------------------
# The migrated sites still behave exactly as before (end-to-end)
# ---------------------------------------------------------------------------


def test_a_unique_antecedent_still_binds_end_to_end(registry):
    text = "Sam has 12 apples. He found 5 apples. How many apples does Sam have?"
    assert solve(text, registry).answer.value == 17


def test_two_rival_names_still_decline_end_to_end(registry):
    """Ambiguous pronoun -> no binding -> decline. Unchanged by the migration."""
    text = "Sam has 12 apples. Rita has 3 apples. He found 5 apples. How many apples does Sam have?"
    result = solve(text, registry)
    assert result.answer.kind != "number", "committed on an ambiguous pronoun"
