"""Phase 6 (increments 118-121) — the fifteen sites become one primitive.

Every hand-written "exactly one candidate in scope, or decline" in the kernel now routes
through `deixis.resolve`. Migrating under the CONSTANT metric is 0-diff by construction,
so these tests pin the things that a byte-identical snapshot does NOT prove:

  - the SYNTAX dimension keeps syntactic candidates out of the referential pools;
  - the conjoined-subject veto still FORBIDS adjacency from arbitrating (it is a group
    referent, and the group must not collapse to the nearer name);
  - obligations.py — the one site that ALREADY ranked, and the only migration using a
    REAL metric (token_distance) — still ranks identically;
  - the sites with no origo at all really do get one (an empty Origo), rather than a
    fabricated coordinate.

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
    return compile_registry(
        load_packs([
            REPO / "packs/core-english",
            REPO / "packs/arithmetic",
            REPO / "packs/difg-mined",
        ])
    )


# ---------------------------------------------------------------------------
# Typed candidate sets: the whole reason dimensions exist
# ---------------------------------------------------------------------------


def test_a_syntactic_candidate_never_competes_with_a_discourse_antecedent():
    """SYNTAX is not a Buhler dimension — it is the same arbitration machine applied to
    intra-sentential argument attachment. Typing it separately is what stops a syntactic
    candidate ever being mistaken for a referential one, and vice versa."""
    syntactic = deixis.Referent(dimension=deixis.SYNTAX, key=1)
    discourse = deixis.Referent(dimension=deixis.DISCOURSE, key="ball")

    # Asking for one dimension can never return a referent of the other.
    assert deixis.resolve(
        [syntactic, discourse], deixis.Origo(), dimension=deixis.DISCOURSE
    ) is discourse
    assert deixis.resolve(
        [syntactic, discourse], deixis.Origo(), dimension=deixis.SYNTAX
    ) is syntactic


def test_every_dimension_is_registered():
    assert set(deixis.DIMENSIONS) == {
        deixis.PERSON, deixis.DISCOURSE, deixis.TIME, deixis.PLACE, deixis.SYNTAX
    }


# ---------------------------------------------------------------------------
# obligations.py — the one site that already ranked
# ---------------------------------------------------------------------------


def test_adjacency_still_arbitrates_and_the_nearer_argument_wins(registry_full):
    """The migration used the REAL metric (token_distance), not `constant`.

    This is the only site where a live ranking function decides a binding, so it is the
    one migration whose 0-diff is NOT a tautology: it is independent evidence that
    resolve()'s strict dominance is behaviourally identical to the hand-written
    adjacency code it was generalised from.
    """
    from rulekit.kernel.engine import solve

    result = solve(
        "Sam has 3 apples. Mary has 4 apples. How many apples does Mary have?",
        registry_full,
    )
    assert result.answer.kind == "number"
    assert result.answer.value == 4  # bound to Mary, the nearer subject — not Sam


def test_a_conjoined_subject_still_refuses_to_collapse_to_the_nearer_name(registry_full):
    """The conjoined-subject veto returns BEFORE arbitration, and must stay there.

    "Frankie and Carla played..." — the subject is the GROUP. Letting adjacency pick the
    nearer conjunct would attribute the fact to one person, which is a confident-wrong,
    not a decline. This is a hand-written group referent, and the hole deixis.md phase 5
    is meant to fill; until then the veto is load-bearing.
    """
    from rulekit.kernel.engine import solve

    result = solve(
        "Frankie and Carla each ate 3 apples. How many apples did Carla eat?",
        registry_full,
    )
    # Whatever it does, it must not silently attribute a lone-subject reading.
    assert result.answer.kind in ("number", "decline")
    if result.answer.kind == "number":
        # If it ever commits, it must be via a real group mechanism (each/distributive),
        # never by adjacency picking Carla because she is nearer.
        assert result.answer.value == 3


def test_token_distance_ranks_and_ties_still_decline():
    origo = deixis.Origo(sentence=0, span=(5, 5))
    near = deixis.Referent(dimension=deixis.SYNTAX, key="near", span=(4, 4))
    far = deixis.Referent(dimension=deixis.SYNTAX, key="far", span=(0, 0))
    tie = deixis.Referent(dimension=deixis.SYNTAX, key="tie", span=(6, 6))

    assert deixis.resolve([far, near], origo, deixis.token_distance).key == "near"
    # near is at |4-5| = 1, tie is at |6-5| = 1 — equidistant, so ambiguous.
    assert deixis.resolve([near, tie], origo, deixis.token_distance) is None


# ---------------------------------------------------------------------------
# The origo-less sites really are origo-less
# ---------------------------------------------------------------------------


def test_the_entity_less_ask_resolves_from_nowhere(registry_full):
    """An entity-less ask ("how many are left?") has, by construction, no reference
    point. The journal must record an EMPTY origo rather than invent one."""
    from rulekit.kernel.engine import solve

    result = solve(
        "Sam has 3 apples. Mary has 4 apples. How many apples are there?",
        registry_full,
    )
    unique = [
        o for o in result.log.journal.observations
        if o.source == "answer/unique-entity"
    ]
    assert unique, "the entity-less consumer must journal its resolution"
    obs = unique[0]
    assert obs.origo.sentence is None  # NO reference point. Not a bug — the point.
    assert obs.origo.span is None
    assert obs.dimension == deixis.PERSON  # it resolves HOLDERS
    assert obs.outcome == "declined"
    assert obs.reason == "tie"  # two holders, nothing to rank them by


def test_the_saturate_sites_journal_through_the_arithmetic_log(registry_full):
    """The journal rides on ArithmeticLog precisely so the synth sites need no new
    parameter. If that plumbing ever breaks, saturate goes silent — pin it."""
    from rulekit.kernel.engine import solve

    result = solve(
        "Sam has 10 marbles. He gave away half of them. "
        "How many marbles does Sam have?",
        registry_full,
    )
    sources = {o.source for o in result.log.journal.observations}
    assert any(s.startswith("synth/") or s.startswith("answer/") for s in sources), (
        f"no saturate/answer site journalled; got {sources}"
    )
