"""Increment 18: flat-priced purchase items ('a hat for $10' / '1 hat for
$10') mixed with 'each'-priced items in the same purchase list. The
purchase-total consumer already sums qty × price over
every purchase-verb Quantity that has a matching Price; the gap was that a
SINGULAR purchased item (no explicit count, or an explicit count of
exactly 1) stated with a flat 'for $N'/'at $N' total and no distributive
'each' never got a Price fact at all — first because a shared
clause-boundary scan (`_is_rate`'s DISTRIBUTIVE quantifier lookahead) let
a LATER conjunct's 'each' leak backward and misclassify the flat item as
a rate, aborting its whole fact extraction; second because the item
picker in `_conjoined_purchase_items` preferred a currency noun over the
purchased item itself when the item carried no explicit digit.

The fix is `learn.py`-only, gated on the existing purchase category:
- `_is_rate` and `_price_each_value` gained an opt-in
  `stop_at_list_boundary` flag (only the purchase-verb call site sets it)
  so a sibling conjunct's 'each' can never leak across a comma/conjunction
  boundary into an earlier item's classification.
- A new `_flat_purchase_price` helper resolves a flat total via the
  'for'/'at' preposition's own ANCHOR obligation (never positional
  guessing) — a beneficiary/duration/exchange 'for' that anchors
  elsewhere, or whose object isn't a currency noun, simply returns None
  and the item declines exactly as before this fact existed.
- Only fires at quantity exactly 1 (explicit or implicit) — a flat total
  on a qty > 1 item is genuinely ambiguous (total vs. each) and stays
  unbuilt, matching the class named at ship time.

Synthetic only.
"""

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


def test_each_priced_then_flat_priced_bare_noun(full_registry):
    r = solve(
        "Tom buys 3 shirts at 5 dollars each and a hat for 10 dollars. "
        "How much did Tom spend?",
        full_registry,
    )
    assert r.answer.value == 25


def test_flat_priced_bare_noun_then_each_priced(full_registry):
    r = solve(
        "Tom buys a hat for 10 dollars and 3 shirts at 5 dollars each. "
        "How much did Tom pay?",
        full_registry,
    )
    assert r.answer.value == 25


def test_each_priced_then_flat_priced_explicit_one(full_registry):
    # "1 hat" (explicit digit) is the same singular-quantity class as the
    # bare-noun "a hat" above — GSM8K text uses both spellings.
    r = solve(
        "Tom buys 3 shirts at 5 dollars each and 1 hat for 10 dollars. "
        "How much did Tom spend?",
        full_registry,
    )
    assert r.answer.value == 25


def test_flat_priced_explicit_one_then_each_priced(full_registry):
    r = solve(
        "Tom buys 1 hat for 10 dollars and 3 shirts at 5 dollars each. "
        "How much did Tom pay?",
        full_registry,
    )
    assert r.answer.value == 25


def test_single_flat_priced_purchase(full_registry):
    r = solve(
        "Tom buys a hat for 10 dollars. How much did Tom spend?",
        full_registry,
    )
    assert r.answer.value == 10


def test_flat_price_on_quantity_above_one_declines(full_registry):
    # "3 shirts for 15 dollars" with NO 'each' is genuinely ambiguous
    # (total vs. per-shirt) at quantity > 1 — must stay declined, never
    # guessed.
    r = solve(
        "Tom buys 3 shirts for 15 dollars. How much did Tom spend?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_beneficiary_for_does_not_misprice(full_registry):
    # a 'for'-PP anchored to something other than the purchased item
    # (a beneficiary, not a price) must never manufacture a Price fact.
    r = solve(
        "Tom buys a shirt for his brother. How much did Tom spend?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_distributive_for_each_of_children_still_declines(full_registry):
    # the pre-existing DISTRIBUTIVE 'each' reading ("N ITEM for EACH of
    # his children") is a per-recipient rate, unrelated to the flat-price
    # class this fix adds — must still decline exactly as before.
    r = solve(
        "Tom buys 2 notebooks for each of his 3 children. How much did Tom spend?",
        full_registry,
    )
    assert r.answer.kind == "decline"
