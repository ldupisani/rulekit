"""Increment 27 (negation-decline-guard): negated-clause quantities
(negation-blind fold). Before this increment the Quantity fold ignored
negation entirely — "Tom does not have 5 apples" committed 5.0 as a
confident-wrong (the `negates` obligation only covers the copula shape
'is not', never the auxiliary shape 'does not VERB'). This adds a
`negation` category (members: not/never — already-known, already
`negator`-sense words, none quarantined) and a clause-scoped check in
learn.py: whenever a negation-category token sits in the SAME CLAUSE as
the verb whose Quantity is about to be folded, that verb's contribution
is withheld entirely (decline-only; never computes negated semantics).
The guard is scoped by the existing complementizer clause boundary, not
the whole sentence, so an unrelated negation elsewhere in the sentence
must not blank an otherwise-fine fold on a different clause's verb.

Synthetic only."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import solve

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def full_registry():
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", mined])
    )


def test_positive_control_still_folds(full_registry):
    # sanity: an un-negated holding folds exactly as before this increment
    r = solve("Tom has 5 apples. How many apples does Tom have?", full_registry)
    assert r.answer.kind == "number"
    assert r.answer.value == 5


def test_auxiliary_negation_declines_the_holding(full_registry):
    # "does not have" — the `negates` obligation (copula-only, 'is not')
    # never bound this shape; before this increment it silently committed
    # 5.0. Must now decline instead of folding a negated count.
    r = solve(
        "Tom does not have 5 apples. How many apples does Tom have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_never_declines_the_event(full_registry):
    r = solve(
        "Tom never has 5 apples. How many apples does Tom have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_negated_purchase_declines_the_spend(full_registry):
    # the guard reaches the purchase-total branch too (dobj_is_count with
    # is_purchase_verb), not just the bare 'have' shape.
    r = solve(
        "Tom does not buy 5 apples at $2 each. How much does Tom spend?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_unnegated_purchase_still_computes(full_registry):
    r = solve(
        "Tom buys 5 apples at $2 each. How much does Tom spend?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 10


def test_negation_in_a_different_clause_does_not_blank_the_fold(full_registry):
    # decline-safety / scoping: 'not' negates 'know' in the MAIN clause;
    # the embedded 'that'-clause has its OWN verb ('has') with its own
    # subject and object, entirely unrelated to the negation. The guard
    # must stay clause-local (via the existing complementizer boundary)
    # and NOT blank this fold just because an unrelated negation exists
    # elsewhere in the same sentence.
    r = solve(
        "Mary does not know that Tom has 5 pens. How many pens does Tom have?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 5
