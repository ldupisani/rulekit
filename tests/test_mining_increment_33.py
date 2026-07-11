"""Mining candidate money-left-asks: 'how much money does WHO have left' —
a new ask shape (packs/arithmetic/rules/core.yaml) gated on the literal
'money' + the trailing 'left' plus the `state` verb category (have/has/
had/...), routed to a new 'money-left' consumer in answer.py: the entity's
general money total (_entity_total — the SAME state-anchor + signed-event
fold the bare 'how much money does WHO have' ask already uses, so a
"spends $N on Y" / "receives $N" event already signed by category polarity
folds in exactly as it would for that ask) minus its priced purchases
(_purchase_total, UNCHANGED — the increment-10 invariant travels with it:
any unpriced purchase, or a 'splits/shares the cost' predicate on the same
entity, declines the WHOLE total rather than risk a silently dropped
term). The subtraction never double-counts: a priced purchase ("buys a
gadget for $8") never emits a currency-measured Quantity at all (learn.py
emits an ITEM-measured Quantity plus a separate Price fact), so it is
invisible to _entity_total's currency fold and only ever appears once, in
the purchase-total subtraction. A negative remainder (purchases exceeding
the money total) declines rather than committing an impossible answer.
Synthetic only."""

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
    r = solve(
        "Nadia has 30 dollars. She buys a notebook for 9 dollars. "
        "How much money does Nadia have left?",
        full_registry,
    )
    assert r.answer.value == 21


def test_multiple_each_priced_purchases(full_registry):
    r = solve(
        "Markers cost 3 dollars each. Grant has 25 dollars. Grant buys 4 markers. "
        "How much money does Grant have left?",
        full_registry,
    )
    assert r.answer.value == 13


def test_direct_spend_event_folds_via_entity_total(full_registry):
    # "spends $N on Y" is not a purchase-verb quantity at all (no Price
    # fact, no item-measured Quantity) — it is a plain currency-measured
    # EVENT the general entity-total fold already signs via the 'lose'
    # category polarity, exactly as the bare 'how much money does WHO
    # have' ask already folds it.
    r = solve(
        "Rosalind has 60 dollars. She spends 11 dollars on stickers. "
        "How much money does she have left?",
        full_registry,
    )
    assert r.answer.value == 49


def test_no_purchases_returns_the_bare_holding(full_registry):
    r = solve(
        "Desmond has 40 dollars. How much money does Desmond have left?",
        full_registry,
    )
    assert r.answer.value == 40


def test_unpriced_purchase_declines(full_registry):
    # a purchase with no matching Price fact anywhere must not silently
    # drop its term from the total (increment-10 discipline, reused here
    # unscoped through _purchase_total).
    r = solve(
        "Desmond has 40 dollars. He buys three kites. "
        "How much money does Desmond have left?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_cost_split_predicate_declines(full_registry):
    r = solve(
        "Desmond has 40 dollars. He buys a kite for 9 dollars. "
        "He splits the cost with his cousin. "
        "How much money does Desmond have left?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_purchases_exceeding_holding_declines(full_registry):
    # a negative remainder is an impossible answer, never committed
    r = solve(
        "Desmond has 6 dollars. He buys a kite for 9 dollars. "
        "How much money does Desmond have left?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_bare_have_ask_without_left_is_unaffected(full_registry):
    # the pre-existing 'how much money does WHO have' ask (no trailing
    # 'left') must keep answering the raw holding exactly as before this
    # candidate existed — this new ask only claims the strictly longer
    # 'left'-suffixed question via max-consumed specificity (patterns.
    # match_ask), never shadowing the shorter one.
    r = solve("Desmond has 40 dollars. How much money does Desmond have?", full_registry)
    assert r.answer.value == 40
