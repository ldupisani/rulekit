"""Mining increment 92: discounted purchase totals — a percent or flat discount
applied to a priced purchase before the pay/spend total. A new `Discount`
fact (model.py, USE-gated for value accounting like Rate/Price/Goal/
GroupTotal) is emitted by pattern rules covering "N% off", "a N%
discount", "a discount of N%", "a $N discount", "$N off", "a discount of
$N" and "a discount of $N EACH" (per-unit scope). The existing
purchase-total consumer (answer.py's `_purchase_total`) applies at most
ONE in-play Discount to its Σ price × qty total before committing; two or
more stated discounts, or an unmodeled scope/percent combination, decline
rather than guess. Synthetic only."""

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


def test_percent_discount_off_form(full_registry):
    r = solve(
        "Priya buys a desk for $400 and gets 25% off.  How much did she pay?",
        full_registry,
    )
    assert r.answer.value == 300


def test_percent_discount_noun_form(full_registry):
    r = solve(
        "Omar buys a bicycle for $500 and gets a 20% discount.  How much did he pay?",
        full_registry,
    )
    assert r.answer.value == 400


def test_discount_of_percent_form(full_registry):
    r = solve(
        "Wanda buys a table for $300. She is given a discount of 10%. "
        "How much did she pay?",
        full_registry,
    )
    assert r.answer.value == 270


def test_flat_discount_noun_form(full_registry):
    r = solve(
        "Felix buys a desk for $150 and gets a $30 discount.  How much did he pay?",
        full_registry,
    )
    assert r.answer.value == 120


def test_flat_discount_off_form(full_registry):
    r = solve(
        "Greta buys a heater for $220 and gets $20 off.  How much did she pay?",
        full_registry,
    )
    assert r.answer.value == 200


def test_discount_of_flat_total_form(full_registry):
    r = solve(
        "Hassan buys a printer for $180. He has a $40 discount. "
        "How much does he pay?",
        full_registry,
    )
    assert r.answer.value == 140


def test_discount_of_flat_per_unit_form(full_registry):
    # 8 candles at $4 each = 32, minus a $1-EACH discount (8 * 1 = 8) -> 24,
    # NOT 32 - 1 = 31 (the bare/total reading) — the trailing 'each' must
    # scope the flat amount per purchased unit.
    r = solve(
        "Nadia bought 8 candles at $4 each. She was given a discount of "
        "$1 each.  How much did Nadia pay in all?",
        full_registry,
    )
    assert r.answer.value == 24


def test_multi_item_purchase_with_percent_discount(full_registry):
    # Σ price × qty across TWO different priced items, then one 10%
    # discount applied to the combined total.
    r = solve(
        "Derek buys 2 chairs at $50 each and a table for $100. "
        "He gets a 10% discount on the total. How much did he pay?",
        full_registry,
    )
    assert r.answer.value == 180


def test_two_conflicting_discounts_decline(full_registry):
    # two DIFFERENT stated discounts is an unmodeled compounding scenario
    # — decline rather than silently pick one or apply neither.
    r = solve(
        "Ivy buys a couch for $1000 and gets a 20% discount. "
        "She also gets a 10% discount. How much did she pay?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_discount_without_purchase_still_declines(full_registry):
    # a bare discount clause with no priced purchase to apply it to: the
    # purchase-total consumer never fires, so this stays a plain decline,
    # not a wrong.
    r = solve("The store offers a 30% discount today. What is the discount?", full_registry)
    assert r.answer.kind == "decline"


def test_undiscounted_purchase_total_unaffected(full_registry):
    # decline-safety / regression check: no discount clause at all leaves
    # the pre-existing purchase-total consumer byte-identical.
    r = solve("Leo buys a table for $80. How much did he pay?", full_registry)
    assert r.answer.value == 80
