"""Mining increment 91: per-unit price premises
whose subject frame the price_verb branch (learn.py) did not previously
read at all — an indefinite-singular generic subject ("A book costs $5")
and a floating distributive 'each' immediately before a price_verb in a
'which'-headed relative clause ("5 toys which each cost $3"). Both are
purely additive readings of the SAME existing `Price` fact increments
15/29/36 already emit and the purchase-total/cost-of-quantity consumers
already read by item lemma.

Mechanism:
  1. `_has_indefinite_singular_determiner` (learn.py): an indefinite
     article ('a'/'an', the new `indefinite_article` category — packs/
     core-english/categories/core.yaml, rooted via the new 'article'
     ROOT_SENSES entry in registry.py) immediately left of an uncounted
     singular price_verb subject is itself per-unit evidence, joining the
     existing distributive-determiner/trailing-each/bare-measure gates
     (never replacing any of them). A definite article ('the') and a
     bare plural subject stay deliberately OUT of scope — the existing
     bare-plural decline (increment 29's own invariant) is unaffected.
  2. `_relative_clause_each_price` (learn.py): a dedicated forward token
     scan from a purchase verb's dobj recognizing 'which' (optional),
     then a bare 'each'/'every' quantifier, then a registered price_verb,
     then a currency noun — the MIRROR ORDER of the already-working
     trailing form ("...which cost $3 each"), read only when the
     ordinary `_price_each_value` scan already declined. A 'that'-headed
     version of this same floating-each shape is a KNOWN, deliberately
     deferred gap (see the function's own docstring): 'that' is a
     clause-boundary sense that also feeds sense disambiguation, tipping
     the price_verb into a NOUN reading before this fold ever runs — a
     disambiguation-stage fix, out of scope for this narrow token scan.
  3. answer.py's 'cost-of-quantity' consumer now treats multiple Price
     facts for the same item that all AGREE on value as one restated
     fact (not an ambiguity) — reading MORE price frames means the same
     price can legitimately be stated twice via two different surface
     forms in one document; only a genuine value DISAGREEMENT still
     declines (the increment-19 invariant this guard exists for).

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


# --- indefinite-singular generic subject ------------------------------


def test_indefinite_article_a_feeds_purchase_total(full_registry):
    r = solve(
        "In a shop, a mug costs $5. Priya bought 6 mugs. "
        "How much did Priya pay in all?",
        full_registry,
    )
    assert r.answer.value == 30


def test_indefinite_article_an_feeds_purchase_total(full_registry):
    r = solve(
        "An eraser costs $2. Elias buys 4 erasers. How much does Elias spend?",
        full_registry,
    )
    assert r.answer.value == 8


def test_two_indefinite_generic_items_sum(full_registry):
    r = solve(
        "A pen costs $2. A notebook costs $3. "
        "Marcus buys 3 pens and 2 notebooks. How much does Marcus pay?",
        full_registry,
    )
    assert r.answer.value == 12


def test_indefinite_generic_mixes_with_determiner_each(full_registry):
    r = solve(
        "A pen costs $2. Each notebook costs $3. "
        "Marcus buys 5 pens and 2 notebooks. How much does Marcus pay?",
        full_registry,
    )
    assert r.answer.value == 16


def test_definite_article_the_still_declines(full_registry):
    # 'the' is deliberately NOT in the indefinite_article category — a
    # definite singular price statement is a separate, more ambiguous
    # class and must stay out of scope.
    r = solve(
        "The mug costs $5. Priya bought 6 mugs. How much did Priya pay in all?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_bare_plural_without_each_still_declines(full_registry):
    # increment 29's own invariant, unaffected by the new determiner
    # signal: a bare plural subject with no article and no distributive
    # marker is a lump-sum/ambiguous statement.
    r = solve(
        "Tom buys 5 mugs. Mugs cost $2. How much does Tom spend?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_indefinite_plural_subject_not_singular_gate(full_registry):
    # 'a'/'an' only ever precede a SINGULAR noun grammatically, but guard
    # the plurality check explicitly: a plural-tagged subject must never
    # qualify even if a determiner sits in front of it.
    r = solve(
        "Mugs cost $2 in bulk. Tom buys 5 mugs. How much does Tom spend?",
        full_registry,
    )
    assert r.answer.kind == "decline"


# --- floating-each relative clause ("which each cost") -----------------


def test_which_each_floating_quantifier_feeds_purchase_total(full_registry):
    r = solve(
        "Nora buys 4 candles which each cost $3. How much does Nora pay?",
        full_registry,
    )
    assert r.answer.value == 12


def test_which_each_floating_quantifier_spend_verb(full_registry):
    r = solve(
        "Owen buys 5 shirts which each cost $2. How much does Owen spend?",
        full_registry,
    )
    assert r.answer.value == 10


def test_trailing_each_form_after_which_still_works(full_registry):
    # the already-working sibling (increment 10's dobj rate scan) must be
    # completely unaffected by the new mirror-order scan.
    r = solve(
        "Nora buys 4 candles which cost $3 each. How much does Nora pay?",
        full_registry,
    )
    assert r.answer.value == 12


def test_that_headed_floating_each_declines_known_gap(full_registry):
    # 'that' (a complementizer, unlike 'which') is a DELIBERATELY
    # deferred gap (see _relative_clause_each_price's docstring) — must
    # decline rather than silently misread.
    r = solve(
        "Nora buys 4 candles that each cost $3. How much does Nora pay?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_which_bare_no_each_still_declines(full_registry):
    # no distributive quantifier anywhere — an ordinary relative clause
    # stating a lump sum, not a per-unit price.
    r = solve(
        "Nora buys 4 candles which cost $12 in total. How much does Nora pay?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_distributive_event_recipient_unaffected(full_registry):
    # the PRE-EXISTING 'N ITEM each to M RECIPIENT' event-total reading
    # (distributive-each-totals, increment 86) must still fire exactly as
    # before: the new price-shaped fallback only tries once that reading's
    # own price scan (_price_each_value) has already declined, and must
    # never itself misfire on a non-price_verb clause. The fold's own
    # value must still be the composed N*M (12), matching increment 86's
    # own decline-safety discipline (this document's raw numbers are not
    # otherwise individually accounted, so the overall answer still
    # safely declines — only the fact-level value is asserted here).
    from rulekit.kernel.model import Quantity

    r = solve(
        "Priya gave 4 stickers each to 3 friends. How many stickers did Priya give?",
        full_registry,
    )
    assert r.answer.kind != "number"
    event_quantities = [
        q for q in r.store.by_kind(Quantity)
        if q.measure == "sticker" and q.verb == "give"
    ]
    assert len(event_quantities) == 1
    assert event_quantities[0].value == 12


# --- restated-price agreement (cost-of-quantity consumer) --------------


def test_restated_agreeing_price_still_commits(full_registry):
    # two Price facts for the SAME item, from two different verb forms,
    # that fully AGREE on value are one fact restated, not an ambiguity.
    r = solve(
        "A mug costs $8. Mugs are $8 each. How much did Wendell spend on 3 mugs?",
        full_registry,
    )
    assert r.answer.value == 24


def test_restated_disagreeing_price_still_declines(full_registry):
    # a genuine VALUE disagreement between two Price facts for the same
    # item must still decline — the increment-19 ambiguity guard.
    r = solve(
        "A mug costs $8. Mugs are $9 each. How much did Wendell spend on 3 mugs?",
        full_registry,
    )
    assert r.answer.kind == "decline"
