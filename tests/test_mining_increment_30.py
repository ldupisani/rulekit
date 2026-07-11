"""Mining candidate sales-revenue-asks: 'how much does WHO make/earn from
selling N ITEM at $P each' — the sell-side mirror of increment 10's
purchase-total. answer.py's _revenue_total sums qty x unit price over every
SELL-category Quantity an entity holds (a new narrow 'sell' category tag,
multi-membership alongside the existing broader 'lose' tag), gated to money
asks over the wage_verb category (make/earn) exactly like the spend_verb
branch gates _purchase_total. Any sold item missing its own Price fact
declines the whole total (increment-10 discipline), and a Rate fact on the
same entity (wage-earnings territory, increment 21's ask/earn-span) makes
the 'make'/'earn' verb ambiguous between two different money sources —
declined rather than guessed. Synthetic only."""

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


def test_simple_priced_sale_revenue(full_registry):
    r = solve(
        "Tom sells 5 cakes at 3 dollars each. How much money does Tom make?",
        full_registry,
    )
    assert r.answer.value == 15


def test_earn_wording_over_priced_sale(full_registry):
    r = solve(
        "Ella sells 4 bracelets at 6 dollars each. How much money does Ella earn?",
        full_registry,
    )
    assert r.answer.value == 24


def test_unpriced_sold_item_declines_whole_total(full_registry):
    # the second sold item has no price of its own -> the whole total declines
    r = solve(
        "Tom sells 5 cakes at 3 dollars each and 2 pies. How much money does Tom make?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_no_sale_event_declines(full_registry):
    # 'make' here is the PRODUCE sense (no sell event at all) — must not
    # be confused with a sales-revenue answer
    r = solve(
        "Tom builds 5 tables. How much money does Tom make?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_rate_and_sale_ambiguity_declines(full_registry):
    # a wage rate AND a priced sale both exist for the same entity — the
    # 'make' verb is genuinely ambiguous between the two money sources
    r = solve(
        "Rob earns 10 dollars an hour. He works 5 hours. He also sells "
        "3 cakes at 2 dollars each. How much money does Rob make?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_wage_rate_span_still_answers_unaffected(full_registry):
    # increment 21's ask/earn-span (rate x worked span) must still fire on
    # its own, unaffected by the new sales-revenue branch
    r = solve(
        "Rob earns 10 dollars an hour. He works 8 hours. How much does Rob make?",
        full_registry,
    )
    assert r.answer.value == 80
