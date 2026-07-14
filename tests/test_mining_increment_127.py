"""Mining increment 127: unit-price-from-total (re-cut of the batch-47 review
kill): a per-unit price recovered from a stated purchase GRAND TOTAL, minus
every OTHER already-priced line item, divided by the asked item's own
purchased count -- ``_unit_price_from_total`` (answer.py), the increment-10
definitive-or-decline discipline reused verbatim via ``_purchase_total``'s
``exclude_item``. Two new ask shapes route here: a bare "how much does each
ITEM cost?" (unit price only) and "what is the cost of N ITEM?" (the
question's own stated quantity multiplies the recovered unit price). Both
route to the NEW ``unit-price-from-total`` consumer, never the existing
Price-fact lookups (item-cost / cost-of-quantity), because this class's
premise never states the asked item's price at all -- only a grand total
for the whole purchase does. Synthetic only."""

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


def test_stated_quantity_cost_of_residual_item(full_registry):
    # 3 hats at $12 (priced) + 5 kites (unpriced); grand total $96 ->
    # kites total = 96 - 36 = 60, unit price = 12, asked qty (2) x 12 = 24.
    r = solve(
        "Priya buys 3 hats and 5 kites. Each hat costs $12. "
        "The total cost of Priya's items is $96. "
        "What is the cost of 2 kites?",
        full_registry,
    )
    assert r.answer.value == 24


def test_bare_each_item_cost(full_registry):
    # 2 hats at $12 (priced) + 4 kites (unpriced); grand total $68 ->
    # kites total = 68 - 24 = 44, unit price = 11.
    r = solve(
        "Priya buys 2 hats and 4 kites. Each hat costs $12. "
        "The total cost of Priya's items is $68. "
        "How much does each kite cost?",
        full_registry,
    )
    assert r.answer.value == 11


def test_no_other_line_items_still_resolves(full_registry):
    # the asked item is the ONLY purchase -> nothing to subtract, the whole
    # grand total divides across the count.
    r = solve(
        "Omar buys 4 kites. The total cost of Omar's items is $40. "
        "How much does each kite cost?",
        full_registry,
    )
    assert r.answer.value == 10


def test_unpriced_other_item_declines(full_registry):
    # a THIRD purchased item with no price anywhere makes the residual
    # ambiguous -- _purchase_total's definitive-or-decline invariant
    # (increment 10) must veto the whole computation.
    r = solve(
        "Priya buys 3 hats, 5 kites, and 2 belts. Each hat costs $12. "
        "The total cost of Priya's items is $96. "
        "How much does each kite cost?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_equal_share_division_stays_declined(full_registry):
    # the DEAD CLASS: dividing a total EARNED between PEOPLE is not this
    # mechanism (the divisor is a count of people, never of the asked
    # item) -- must stay declined, not silently answered via the count of
    # some unrelated purchased item.
    r = solve(
        "Mona and Ravi sold 6 belts that cost $3 each and 4 toys that cost $2. "
        "How much will each of them earn if they divided their total earning?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_negative_residual_declines(full_registry):
    # the other priced items already exceed the stated grand total -> the
    # residual would be negative, so this must decline rather than commit
    # a negative unit price.
    r = solve(
        "Priya buys 3 hats and 5 kites. Each hat costs $40. "
        "The total cost of Priya's items is $96. "
        "How much does each kite cost?",
        full_registry,
    )
    assert r.answer.kind == "decline"
