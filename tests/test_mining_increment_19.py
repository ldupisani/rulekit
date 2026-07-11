"""Capacity asks (budget / unit price): "how many X can/could/... WHO
buy/purchase/afford (with $B)?" — a new ask shape keyed structurally on
the MODAL token (increment 14 split 'modal' from 'auxiliary' precisely so
factual asks exclude it and a capacity shape can claim it instead), plus a
'capacity' consumer in answer.py: floor(budget / Price(item)).

The consumer commits ONLY when: a Price fact for the asked item exists
(exactly one), a UNIQUE explicit budget is stated (the ask's own "with $B"
tail, or absent that, the entity's single stated money holding), and any
OTHER priced item entangled with the same entity is itself a resolvable
purchase (a later increment, remaining-budget-capacity, subtracts those
purchases from the budget instead of declining outright — anything less
resolvable than that still declines exactly as before).
Floor division uses round-then-floor to avoid float-precision false floors
(e.g. 1.0 // 0.1 == 9.0 in raw floating point, not 10). Synthetic only."""

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


def test_explicit_budget_with_clause(full_registry):
    r = solve(
        "Pens cost 2 dollars each. How many pens can Mary buy with 10 dollars?",
        full_registry,
    )
    assert r.answer.value == 5


def test_budget_from_entitys_single_money_holding(full_registry):
    r = solve(
        "Pens cost 2 dollars each. Mary has 10 dollars. How many pens can Mary buy?",
        full_registry,
    )
    assert r.answer.value == 5


def test_pronoun_subject_resolves_through_discourse(full_registry):
    r = solve(
        "Mary has 10 dollars. Pens cost 2 dollars each. How many pens can she buy?",
        full_registry,
    )
    assert r.answer.value == 5


def test_floor_semantics_leftover_money_not_a_partial_item(full_registry):
    # 10 / 3 = 3.33... -> floors to 3, never rounds up or errors on the
    # $1 left over
    r = solve(
        "Pens cost 3 dollars each. How many pens can Mary buy with 10 dollars?",
        full_registry,
    )
    assert r.answer.value == 3


def test_exact_division_float_precision_does_not_false_floor(full_registry):
    # 0.3 / 0.1 in raw IEEE float division is 2.9999999999999996, so a naive
    # `budget // price` floors it to 2 instead of the true exact quotient
    # 3 — the round-then-floor expression must land on 3, not undercount
    r = solve(
        "Pens cost 0.1 dollars each. How many pens can Mary buy with 0.3 dollars?",
        full_registry,
    )
    assert r.answer.value == 3


def test_missing_price_fact_declines(full_registry):
    # no priced 'pen' anywhere — the semantic gate (Price fact required)
    # must decline rather than treat the stated $10 as a bare number
    r = solve(
        "Mary has 10 dollars. How many pens can Mary buy?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_multiple_money_holdings_declines(full_registry):
    # two conflicting stated holdings for the same entity — genuinely
    # ambiguous, must not guess which is the budget
    r = solve(
        "Pens cost 2 dollars each. Mary has 10 dollars. Mary has 4 dollars. "
        "How many pens can Mary buy?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_entangled_but_fully_priced_purchase_computes_remaining_budget(full_registry):
    # Mary's budget is shared across pens AND erasers (she already bought
    # erasers) — a later increment (remaining-budget-capacity) taught this
    # mechanism to subtract the entity's OTHER fully-priced purchases
    # (3 erasers x $1 = $3) from the budget before dividing, rather than
    # declining outright: (10 - 3) / 2 = 3 (floor).
    r = solve(
        "Pens cost 2 dollars each. Erasers cost 1 dollar each. "
        "Mary buys 3 erasers. How many pens can Mary buy with 10 dollars?",
        full_registry,
    )
    assert r.answer.value == 3


def test_entangled_purchase_with_a_further_unpriced_purchase_still_declines(
    full_registry,
):
    # erasers ARE fully priced and resolvable, but Mary also bought 2
    # markers with no stated price at all — the remaining-budget total
    # can't drop that unpriced term silently (the increment-10
    # definitive-or-decline invariant, reused unscoped here), so this
    # must still decline exactly as before remaining-budget subtraction
    # existed.
    r = solve(
        "Pens cost 2 dollars each. Erasers cost 1 dollar each. "
        "Mary buys 3 erasers. Mary buys 2 markers. "
        "How many pens can Mary buy with 10 dollars?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_factual_auxiliary_ask_is_unaffected(full_registry):
    # the pre-existing 'did/does' auxiliary-gated factual ask shapes must
    # keep matching exactly as before — the modal slot type only claims
    # tokens those asks already could not (increment 14)
    r = solve(
        "Mary bought 5 pens. How many pens does Mary have?",
        full_registry,
    )
    assert r.answer.value == 5
