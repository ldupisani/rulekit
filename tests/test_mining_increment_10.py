"""Increment 10: priced purchases — 'N ITEM at/for $PRICE each' emits a
Price fact alongside the ordinary purchase Quantity; a purchase-total
fallback answers 'how much did X pay/spend' by multiplying qty x price
over every purchase-verb quantity the entity holds. Declines whenever any
purchase-verb quantity lacks a matching price (definitive-or-decline) —
never undercounts. Synthetic only."""

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


def test_single_priced_purchase(full_registry):
    r = solve("Nina buys three toys at $10 each. How much does Nina spend?", full_registry)
    assert r.answer.value == 30


def test_priced_purchase_pay_verb(full_registry):
    r = solve(
        "Tim buys 3 dozen eggs for $0.50 each. How much did Tim pay?", full_registry
    )
    assert r.answer.value == 18


def test_multi_sentence_purchases_sum(full_registry):
    r = solve(
        "Nina buys three toys at $10 each. Nina buys five shirts at $6 each. "
        "How much does Nina spend in total?",
        full_registry,
    )
    assert r.answer.value == 60


def test_one_unpriced_purchase_declines_the_whole_total(full_registry):
    # a second purchase with no known price must not silently drop its term
    r = solve(
        "Nina buys three toys at $10 each. Nina buys five shirts. "
        "How much does Nina spend?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_no_price_at_all_still_declines(full_registry):
    r = solve("Nina buys three toys. How much does Nina spend?", full_registry)
    assert r.answer.kind == "decline"


def test_distributive_each_unaffected(full_registry):
    # 'for EACH of his children' stays the plain silent-skip, not a price
    r = solve(
        "Kelly gives 2 notebooks for each of her 3 children. "
        "How many notebooks does Kelly have left?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_unrelated_ask_verb_does_not_borrow_purchase_total(full_registry):
    # 'earn' is not in spend_verb — a priced purchase must not answer it
    r = solve("Nina sells three toys at $10 each. How much does Nina earn?", full_registry)
    assert r.answer.kind == "decline"


def test_split_cost_declines_rather_than_the_presplit_total(full_registry):
    # "splits the cost with his brother" halves what he actually paid —
    # the split factor is unbuilt, so the raw purchase total must decline
    r = solve(
        "John buys 3 cakes for $12 each and splits the cost with his brother. "
        "How much did he pay?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_unused_price_never_unlocks_other_commits(full_registry):
    # a price that merely EXISTS is not read — mirrors the Rate lesson
    r = solve(
        "Nina buys three toys at $10 each. Nina got a $50 bonus. "
        "How much money does Nina have?",
        full_registry,
    )
    assert r.answer.kind == "decline"
