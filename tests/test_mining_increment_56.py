"""Mining candidate change-asks: 'how much change does/did/will WHO get/
receive/take (back)' — a new ask shape (packs/arithmetic/rules/core.yaml)
gated on the literal 'change' (given a new noun sense alongside its
existing verb sense), routed to a new 'change' consumer in answer.py: the
buyer's stated TENDER minus the SAME priced-purchase total the money-left
consumer already uses (_purchase_total, UNCHANGED — the increment-10
invariant travels with it unscoped: any unpriced purchase, or a 'splits/
shares the cost' predicate on the buyer, declines the whole total).

The tender is the general SVO fold's own plain currency Quantity EVENT for
a verb in the new `tender_verb` category (pay/give — packs/difg-mined/
categories/semantic.yaml): no new fact kind and no learn.py change were
needed, since "pays $50" / "pays with a $50 bill" / "gave $250 [to X]"
already produce this Quantity fact today; the category only lets the
change consumer name it specifically. Existence of a tender-shaped
Quantity alone is never enough — more than one, or none, is a genuine
ambiguity and declines.

Unlike money-left, a change ask presupposes a purchase actually happened:
when _purchase_total has nothing to offer (no priced purchase found at
all, for ANY reason) this consumer declines rather than defaulting spend
to 0. A discount/tip predicate on the buyer (the `discount` category,
generalizing increment 10's single 'splits the cost' verb check to a dobj
category) also declines, since the raw purchase total is then not
necessarily the final amount owed. Synthetic only."""

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


def test_paid_with_a_bill(full_registry):
    r = solve(
        "Priya buys 3 candles at $4 each and 2 vases at $6 each. "
        "She paid with a $50 bill. How much change will she get back?",
        full_registry,
    )
    assert r.answer.value == 26


def test_direct_dobj_currency_tender(full_registry):
    # "SUBJECT paid $N" — no 'with a ... bill' wrapper at all, the plainest
    # tender shape.
    r = solve(
        "Owen buys 4 kites at $5 each. He paid $30. How much change did Owen get?",
        full_registry,
    )
    assert r.answer.value == 10


def test_gave_currency_to_recipient(full_registry):
    # "SUBJECT gave $N to X" — the 'give' sibling of 'pay', with a trailing
    # prepositional recipient the tender extraction is indifferent to.
    r = solve(
        "Beatrix buys 2 mugs at $12 each. She gave $30 to the clerk. "
        "How much change did she take?",
        full_registry,
    )
    assert r.answer.value == 6


def test_future_modal_ask_variant(full_registry):
    # 'will' phrasing (future_modal), not just do/does/did.
    r = solve(
        "Declan buys 5 pens at $2 each. He paid with a $20 bill. "
        "How much change will Declan receive back?",
        full_registry,
    )
    assert r.answer.value == 10


def test_no_tender_declines(full_registry):
    # a plain holding ("has $N") is not a tender-verb event — no ask shape
    # here should manufacture a payment amount out of a state quantity.
    r = solve(
        "Farrah buys 3 mugs at $4 each. She has $50. "
        "How much change will Farrah receive?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_no_priced_purchase_declines(full_registry):
    # a change ask presupposes a purchase — no priced purchase at all must
    # NOT be silently treated as zero spend (unlike money-left's own
    # legitimate zero-purchase case).
    r = solve(
        "Marcus paid with a $20 bill. How much change will he get back?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_unpriced_purchase_declines_whole_total(full_registry):
    r = solve(
        "Ines buys 3 baskets at $2 each and 4 ribbons. "
        "She paid with a $20 bill. How much change did she get?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_cost_split_predicate_declines(full_registry):
    r = solve(
        "Wesley buys a kite for $18. He splits the cost with his roommate. "
        "He paid with a $20 bill. How much change did Wesley get back?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_tip_predicate_declines(full_registry):
    # a stated tip is an unconsumed price ADJUSTMENT the raw purchase
    # total never accounts for — decline rather than risk the pre-tip
    # number.
    r = solve(
        "Harriet buys 2 baskets at $9 each. She gave a tip to the driver. "
        "She paid with a $50 bill. How much change did Harriet receive?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_purchases_exceeding_tender_declines(full_registry):
    r = solve(
        "Callum buys 3 mugs at $10 each. He paid with a $20 bill. "
        "How much change did Callum get?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_bare_change_verb_sense_is_unaffected(full_registry):
    # 'change' still parses as an ordinary VERB outside this ask shape —
    # the new noun sense must not hijack unrelated sentences.
    r = solve(
        "Nora has $5. She will change the coin. How many dollars does Nora have?",
        full_registry,
    )
    assert r.answer.value == 5
