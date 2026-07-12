"""Mining candidate priced-quantity-cost-asks: "how much did WHO pay/spend
for/on N ITEM" — a question-supplied-quantity cost ask. The question states
its OWN count (never an existing Quantity fact); the new 'cost-of-quantity'
consumer (answer.py) commits N times the item's unique per-unit Price fact,
declining on any price ambiguity, a cost-splitting predicate on the buyer
(increment 10's invariant), or a pre-existing quantity of the same item for
the same buyer. Synthetic only."""

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


def test_pay_for_quantity(full_registry):
    r = solve(
        "Pencils cost 2 dollars each. How much did Rosa pay for 6 pencils?",
        full_registry,
    )
    assert r.answer.value == 12


def test_spend_on_quantity(full_registry):
    r = solve(
        "A mug costs 8 dollars. Mugs are 8 dollars each. "
        "How much did Wendell spend on 3 mugs?",
        full_registry,
    )
    assert r.answer.value == 24


def test_no_price_fact_declines(full_registry):
    # no price stated anywhere for 'candle' -> decline, never guess
    r = solve(
        "Rosa likes candles. How much did Rosa pay for 6 candles?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_cost_splitting_predicate_declines(full_registry):
    # increment 10's invariant: a buyer who splits the cost with someone
    # else means the raw qty * price isn't necessarily what they paid
    r = solve(
        "Pencils cost 2 dollars each. Rosa splits the bill with her friend. "
        "How much did Rosa pay for 6 pencils?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_conflicting_existing_quantity_declines(full_registry):
    # Rosa already has a stated quantity of pencils elsewhere in the text —
    # ambiguous against the question's own count, decline rather than guess
    r = solve(
        "Pencils cost 2 dollars each. Rosa buys 10 pencils. "
        "How much did Rosa pay for 6 pencils?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_bare_pay_ask_still_uses_real_events(full_registry):
    # the pre-existing bare "how much did WHO pay" ask (no trailing
    # "for/on N ITEM" clause) must keep winning via the real purchase
    # total when there is no question-supplied quantity to consume
    r = solve(
        "Hats cost 9 dollars each. Otis buys 3 hats. How much did Otis pay?",
        full_registry,
    )
    assert r.answer.value == 27


def test_span_question_not_hijacked(full_registry):
    # "in N months" must keep routing to the rate-span/earn-span family,
    # never the new cost-of-quantity ask (spend_target_prep excludes 'in')
    r = solve(
        "Otis earns 5 dollars an hour. How much did Otis earn in 3 hours?",
        full_registry,
    )
    assert r.answer.value == 15
