"""Mining candidate capacity-ask-overmatch: ask/how-many-capacity's `verb`
slot narrowed from `type: verb` (any verb) to `cat: purchase`.

The capacity ask ("how many X can/will/must WHO VERB (with $B)?") used to
gate ONLY on the `modal` token (can/could/should/may/might/must/will/would)
plus a bare verb slot — which is satisfied by essentially any verb at all.
Because it therefore matched almost every modal-phrased "how many" question
regardless of subject matter, it won ask-specificity over every other ask
and then unconditionally declined on its own semantic precondition ("N
price facts known for X — a capacity ask needs exactly one"), masking
whatever OTHER consumer (an ordinary event fold, a remainder/goal-deficit
consumer, a rate-span consumer) could otherwise have been consulted for a
question that was never about money at all.

The fix requires the verb to be a member of the `purchase` category (buy/
buys/bought/buying/purchase/purchases/purchased/order/orders/ordered —
packs/difg-mined/categories/semantic.yaml) — exactly the verbs the
capacity consumer's own semantics (budget divided by unit price) are
about, and the same category `_purchase_total`/the remaining-budget
subtraction already use elsewhere in answer.py to recognise a genuine
purchase. This is a pure ask-specificity narrowing: no consumer logic in
answer.py changed. A question whose verb is a genuine purchase verb still
reaches the (unchanged) capacity consumer; every other verb now falls
through ask-specificity to whichever other ask can serve it, or to no ask
at all — never into a wrong commit, since nothing about how any consumer
computes an answer changed. Synthetic only."""

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


def test_genuine_capacity_ask_explicit_budget_unaffected(full_registry):
    # regression: a real purchase verb ("buy") with the ask's own "with $B"
    # tail must still reach the capacity consumer exactly as before
    r = solve(
        "Kites cost 3 dollars each. How many kites can Farid buy with 12 dollars?",
        full_registry,
    )
    assert r.answer.value == 4


def test_genuine_capacity_ask_budget_from_holding_unaffected(full_registry):
    # regression: the budget-from-entity's-own-money-holding path (no "with
    # $B" tail at all) must also still reach the capacity consumer
    r = solve(
        "Kites cost 3 dollars each. Farid has 12 dollars. "
        "How many kites can Farid buy?",
        full_registry,
    )
    assert r.answer.value == 4


def test_purchase_verb_with_no_price_fact_still_declines(full_registry):
    # decline-safety regression: a genuine purchase verb still reaches the
    # capacity consumer's own precondition and declines when no Price fact
    # exists for the asked item — completely unaffected by the narrowing
    r = solve(
        "Farid has 12 dollars. How many kites can Farid buy?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_future_modal_remainder_ask_no_longer_masked_by_capacity(full_registry):
    # THE FIX: an ordinary state-plus-event fold, asked with a future-modal
    # remainder question ("how many X will WHO have left") — the same
    # premises resolve through the plain 'does' form already; before this
    # candidate, the 'will' form matched ask/how-many-capacity instead
    # (its bare `type: verb` slot swallowed the 'have' verb here) and died
    # on "0 price facts known for 'marble'" despite no price ever being
    # relevant. With the verb slot narrowed to purchase verbs, 'have' no
    # longer satisfies ask/how-many-capacity, so the question falls
    # through to the ordinary factual ask (ask/how-many-entity, widened to
    # future_modal by an earlier candidate) and folds correctly.
    r = solve(
        "Farid has 90 marbles. Farid gives away 30 marbles. "
        "How many marbles will he have left?",
        full_registry,
    )
    assert r.answer.value == 60
    assert r.answer.kind == "number"


def test_future_modal_remainder_ask_auxiliary_form_matches_identically(full_registry):
    # the pre-existing 'does'-phrased sibling of the case just above —
    # included to show the fix makes the two forms resolve identically,
    # not merely that the 'will' form stopped erroring
    r = solve(
        "Farid has 90 marbles. Farid gives away 30 marbles. "
        "How many marbles does he have left?",
        full_registry,
    )
    assert r.answer.value == 60


def test_non_purchase_modal_question_with_no_available_consumer_still_declines(
    full_registry,
):
    # decline-safety: narrowing the verb slot must never manufacture a
    # wrong commit for a non-purchase-verb modal question that genuinely
    # has no consumer able to answer it — it must decline cleanly, exactly
    # as a question no ask recognises at all would
    r = solve(
        "Farid has 12 dollars. How many kites will Farid want?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_capacity_modal_can_still_excluded_from_non_purchase_verbs(full_registry):
    # decline-safety companion: a capacity/hypothetical modal ('can') over
    # a non-purchase, non-event verb ('have') must still decline rather
    # than being newly swept into any other ask machinery
    r = solve(
        "Farid has 5 marbles. How many marbles can Farid have?",
        full_registry,
    )
    assert r.answer.kind == "decline"
