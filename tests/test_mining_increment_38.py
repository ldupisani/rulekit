"""Mining candidate item-cost-asks: item-subject cost asks ("how much do/
does/did ITEM cost?"). A new ask (ask/how-much-item-cost, gated on the
EXISTING price_verb category — cost/costs, no category widening) paired with
a new answer.py consumer ("item-cost") that resolves the asked item's unique
Price fact times its unique purchased/held Quantity — or the bare unit price
when no such Quantity is in play. Exactly-one-Price-fact-or-decline and
exactly-one-Quantity-fact-or-decline mirror increment 19's capacity consumer
discipline. Synthetic only."""

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


def test_priced_purchase_totals_qty_times_price(full_registry):
    r = solve(
        "Priya buys 4 jackets at 6 dollars each. How much do the jackets cost?",
        full_registry,
    )
    assert r.answer.value == 24


def test_does_variant_singular_item(full_registry):
    r = solve(
        "Marcus buys 2 hats at 15 dollars each. How much does the hat cost?",
        full_registry,
    )
    assert r.answer.value == 30


def test_bare_unit_price_with_no_quantity_in_play(full_registry):
    # no purchase/holding quantity is ever stated for 'hat' — only the
    # per-unit price itself, so the bare price answers directly
    r = solve(
        "Each hat costs 12 dollars. How much does a hat cost?",
        full_registry,
    )
    assert r.answer.value == 12


def test_ambiguous_multiple_quantities_declines(full_registry):
    # two DIFFERENT entities each hold their own quantity of the same
    # priced item — which one the question means is a genuine ambiguity
    r = solve(
        "Priya buys 4 jackets at 6 dollars each. Marcus buys 3 jackets at "
        "6 dollars each. How much do the jackets cost?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_ambiguous_multiple_prices_declines(full_registry):
    # two competing price statements for the same item — never guess which
    r = solve(
        "A hat costs 12 dollars each. A hat costs 15 dollars each. "
        "How much does the hat cost?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_unpriced_item_declines(full_registry):
    # 'jacket' is never priced anywhere in the text — no ask shape gap,
    # the item-cost consumer itself must decline rather than guess
    r = solve(
        "Priya buys 4 jackets. How much do the jackets cost?",
        full_registry,
    )
    assert r.answer.kind == "decline"
