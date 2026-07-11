"""Remaining-budget capacity asks: "how many X can WHO buy" when the
entity's stated budget is ALSO entangled with one or more OTHER purchases
this same entity already made ("Pens cost $2 each. Nora has $20. She buys
a notebook for $8. How many pens can Nora buy?"). Increment 19's capacity
consumer declined this outright (any other priced item entangled with the
entity made the budget "ambiguous"). This increment extends it: when every
entangled other-priced item is itself a fully-priced, unambiguous PURCHASE
(qty and price both known, no cost-splitting predicate on the entity), the
remaining budget is exactly computable — remaining = budget - Σ(qty x
price over those other purchases) — and the existing floor-division
mechanism runs on the remainder instead of declining.

Reuses `_purchase_total`'s own decline discipline (an unpriced purchase or
a 'splits/shares the cost' predicate on the entity declines the WHOLE
total, increment 10's invariant) via a new opt-in `exclude_item` parameter,
so that invariant automatically extends to this subtraction path. Any
other-priced item held through a NON-purchase verb ("has"/"owns") is not
spending at all and stays a genuine ambiguity — the original increment-19
decline, unchanged. A negative remainder (other purchases exceed the
stated budget) also declines. Synthetic only."""

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


def test_single_entangled_purchase_computes_remaining_budget(full_registry):
    # $20 budget minus the $8 notebook already bought leaves $12; floor(12
    # / 2) = 6 pens, not a decline.
    r = solve(
        "Pens cost 2 dollars each. Nora has 20 dollars. "
        "Nora buys a notebook for 8 dollars. How many pens can Nora buy?",
        full_registry,
    )
    assert r.answer.value == 6


def test_multiple_entangled_purchases_sum_before_dividing(full_registry):
    # two OTHER priced purchases both get subtracted: 30 - 8 - 5 = 17,
    # floor(17 / 2) = 8.
    r = solve(
        "Pens cost 2 dollars each. Nora has 30 dollars. "
        "Nora buys a notebook for 8 dollars. Nora buys a pencil for 5 dollars. "
        "How many pens can Nora buy?",
        full_registry,
    )
    assert r.answer.value == 8


def test_negative_remaining_budget_declines(full_registry):
    # the notebook alone ($8) already exceeds the stated $5 budget — the
    # remainder is negative, so this must decline rather than floor a
    # negative number or silently clamp it.
    r = solve(
        "Pens cost 2 dollars each. Nora has 5 dollars. "
        "Nora buys a notebook for 8 dollars. How many pens can Nora buy?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_split_cost_invariant_extends_to_subtraction_path(full_registry):
    # increment 10's "splits/shares the cost" invariant must extend here:
    # Nora's split notebook purchase makes what she actually paid unbuilt,
    # so the whole remaining-budget total must decline, not just silently
    # use the pre-split price.
    r = solve(
        "Pens cost 2 dollars each. Nora has 20 dollars. "
        "Nora buys 2 notebooks for 8 dollars each and splits the cost "
        "with her brother. How many pens can Nora buy?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_non_purchase_entangled_item_still_declines(full_registry):
    # Nora HAS 2 notebooks (a state holding, never a purchase) alongside
    # her own priced notebooks — that is not spending, so the remaining
    # budget cannot be resolved through it; this stays the original
    # increment-19 decline.
    r = solve(
        "Pens cost 2 dollars each. Nora has 20 dollars. "
        "Notebooks cost 8 dollars each. Nora has 2 notebooks. "
        "How many pens can Nora buy?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_unentangled_capacity_ask_is_unaffected(full_registry):
    # no other priced item at all — the plain increment-19 path is
    # untouched by this extension.
    r = solve(
        "Pens cost 2 dollars each. Nora has 20 dollars. How many pens can Nora buy?",
        full_registry,
    )
    assert r.answer.value == 10
