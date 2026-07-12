"""Mining candidate modal-spend-measure-price: future-modal spend/pay asks
PAIRED with 'a MEASURE of ITEM costs $X' price emission.

Two coordinated pieces:

1. Ask widening: `ask/how-much-bare-entity` and `ask/how-much-pay-for-quantity`
   have their `aux` slot widened from `type: auxiliary` to `type: future_modal`
   (mirrors increment 49's four-ask widening exactly) so "how much will/would
   WHO pay?" and "how much will/would WHO pay for N ITEM?" are recognized
   alongside the ordinary do/does/did form. No consumer changes.

2. Price emission: a price_verb ("cost(s)") whose subject binds (through the
   existing partitive 'of' preposition) to an ITEM noun, where the 'of'
   phrase's own anchor names a KNOWN physical measure unit (reg.conversions:
   pound, gallon, ounce, ...), now emits a Price fact keyed on that MEASURE
   noun rather than the item — lining up with the purchase premise's own
   Quantity.measure (unwidened since increment 10). Two sub-shapes: a bare
   (uncounted) measure anchor is itself the per-unit signal ("a pound of X
   costs $Y"); a counted measure anchor ("4 pounds of X") still needs the
   existing 'each'/distributive trigger.

A pre-existing rule collision is also fixed:
`arithmetic/partition-membership-of-noun`'s `verb` slot is narrowed from the
general `type: verb` to `cat: state` — a membership partition is always
copular ("ARE dogs"); the unrestricted verb slot let it swallow an unrelated
priced-measure sentence sharing the same token order ("4 pounds of X COST 10
dollars each"), stealing it from the price-verb emission before it could run.

Synthetic only — every scenario here is invented from scratch."""

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


def test_bare_measure_partitive_price_feeds_purchase_total(full_registry):
    # "a pound of X costs $Y" — the bare (uncounted) measure anchor IS the
    # per-unit signal; no 'each' anywhere in the text.
    r = solve(
        "Priya bought 3 pounds of flour and 2 quarts of milk. "
        "A pound of flour costs 4 dollars and a quart of milk costs 5 dollars. "
        "How much will Priya pay in all?",
        full_registry,
    )
    assert r.value == 3 * 4 + 2 * 5


def test_counted_measure_partitive_with_each_emits_measure_keyed_price(full_registry):
    # "N MEASURE of X cost $Y each" — the counted measure anchor needs the
    # ordinary distributive 'each' trigger (increment 15's existing path),
    # but the Price must still key on the MEASURE noun, not the item. Kept
    # as a standalone sentence (not chained to a purchase premise): a
    # SEPARATE, pre-existing value-accounting behavior already declines
    # whenever a price sentence restates the exact same stated count as an
    # earlier purchase sentence (confirmed on unmodified increment 15's own
    # "6 eggs cost $2 each" shape too) — out of scope for this candidate;
    # the Price fact itself is the coverage evidence here.
    r = solve("6 ounces of sugar cost 2 dollars each.", full_registry)
    prices = [f for f in r.facts() if type(f).__name__ == "Price"]
    assert len(prices) == 1
    assert prices[0].item == "ounce"
    assert prices[0].value == 2.0


def test_future_modal_pay_for_quantity_ask(full_registry):
    # ask/how-much-pay-for-quantity widened: "how much would WHO pay for N
    # ITEM" — an ordinary (non-partitive) priced item, isolating the ask-side
    # widening from the price-emission mechanism above.
    r = solve(
        "Kai's toys cost 5 dollars each. How much would Kai pay for 3 toys?",
        full_registry,
    )
    assert r.value == 15


def test_future_modal_bare_entity_ask_ordinary_purchase(full_registry):
    # ask/how-much-bare-entity widened, over an ordinary (non-partitive)
    # priced purchase — the increment-10/15 path, untouched.
    r = solve(
        "Marbles cost 2 dollars each. Wren buys 4 marbles. "
        "How much will Wren pay?",
        full_registry,
    )
    assert r.value == 8


def test_non_conversion_measure_word_declines(full_registry):
    # "a box of X costs $Y" — 'box' is not a known physical measure unit
    # (never a reg.conversions member), so this stays the increment-10/15
    # decline discipline: no per-unit Price is invented from a made-up
    # container noun, and the purchase can't be priced.
    r = solve(
        "Zara bought 3 boxes of pens. A box of pens costs 6 dollars. "
        "How much will Zara pay?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_capacity_modal_still_excluded_from_bare_entity_ask(full_registry):
    # the increment-14/19/49 invariant: capacity/hypothetical modals
    # (can/could/...) must NOT satisfy the future_modal-widened aux slot —
    # only will/would do.
    r = solve(
        "Marbles cost 2 dollars each. Wren buys 4 marbles. "
        "How much can Wren pay?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_membership_partition_of_noun_still_fires_on_state_verb(full_registry):
    # regression: the cat:state narrowing on
    # arithmetic/partition-membership-of-noun must not break its own real
    # class — a genuine copular membership partition over a named plural
    # collection.
    r = solve(
        "There are 20 animals. 8 of the animals are dogs. How many dogs are there?",
        full_registry,
    )
    assert r.value == 8


def test_price_verb_swallowed_partition_no_longer_fires(full_registry):
    # the exact collision this candidate fixes: a priced-measure sentence
    # sharing partition-membership-of-noun's token order (number, 'of',
    # plural noun, verb, noun) must be read as a Price statement, not
    # mis-parsed as a bogus membership partition over 'cost'.
    r = solve("4 pounds of rice cost 8 dollars each.", full_registry)
    prices = [f for f in r.facts() if type(f).__name__ == "Price"]
    partitions = [f for f in r.facts() if type(f).__name__ == "PartitionQuantity"]
    assert len(prices) == 1 and prices[0].item == "pound" and prices[0].value == 8.0
    assert not partitions
