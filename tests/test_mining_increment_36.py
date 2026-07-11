"""Mining candidate copular-priced-items: 'ITEM(s) is/are $X each' — a price
stated with the state verb 'be' (a copular sentence) instead of increment
15's 'cost'/'costs'. learn.py emits a Price fact keyed on the SUBJECT noun
when 'be''s dobj is a currency-valued count noun followed by the existing
distributive-'each' structure, gated on the subject being a PLURAL common
noun — reusing increment 10's _is_rate/_rate_unit unwidened, exactly as
increment 15 does for 'cost'. No YAML change: 'be' is not added to
price_verb (that would widen every price_verb consumer); the gate is
structural (state category + verb_lemma == 'be' + plural subject + currency
dobj + the each-marker). Every other 'be'+currency-dobj shape (no 'each',
singular subject, a 'per NOUN' rate marker) is untouched — the existing
state-verb Quantity/Membership/Predication fold still owns it. The
increment-10 purchase-total consumer in answer.py matches these item-keyed
Price facts against purchase quantities by item noun with zero changes of
its own (increment 15 precedent). Synthetic only."""

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


def test_copular_priced_item_feeds_purchase_total(full_registry):
    r = solve(
        "Tickets are $5 each. Ben buys 4 tickets. How much does Ben spend?",
        full_registry,
    )
    assert r.answer.value == 20


def test_copular_priced_item_pay_verb(full_registry):
    r = solve(
        "Cookies are $2 each. Amy buys 6 cookies. How much did Amy pay?",
        full_registry,
    )
    assert r.answer.value == 12


def test_two_copular_priced_items_sum(full_registry):
    r = solve(
        "Tickets are $5 each. Cookies are $2 each. "
        "Ben buys 4 tickets. Ben buys 3 cookies. How much does Ben spend in total?",
        full_registry,
    )
    assert r.answer.value == 26


def test_singular_subject_is_not_a_copular_priced_item(full_registry):
    # a SINGULAR subject ("a ticket") is not this class' gate (plural common
    # noun only) — must not misfire and must not disturb the ordinary fold
    r = solve(
        "A ticket is $5. Ben buys 4 tickets. How much does Ben spend?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_lump_sum_be_without_each_declines(full_registry):
    # no distributive 'each' — a lump-sum/ambiguous statement, not a
    # per-unit price; must not be treated as $5/ticket
    r = solve(
        "Tickets are $5. Ben buys 4 tickets. How much does Ben spend?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_rate_marker_per_is_not_a_copular_each(full_registry):
    # 'per NOUN' is a different (unbuilt) rate reading, not the distributive
    # 'each' this class targets — must not misfire as $5/ticket
    r = solve(
        "Tickets are $5 per pack. Ben buys 4 tickets. How much does Ben spend?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_ordinary_copular_membership_still_folds(full_registry):
    # an ordinary 'be' + noun-dobj Membership sentence (no currency at all)
    # must be entirely unaffected by the new branch
    r = solve(
        "Roses are flowers. How many flowers does Ana have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_split_cost_still_declines_with_copular_priced_source(full_registry):
    # increment 10's invariant must hold regardless of which emission site
    # supplied the Price fact: a 'splits the cost' predicate on the buyer
    # is an unconsumed qualitative predicate that must still decline
    r = solve(
        "Mugs are $8 each. Sam buys 5 mugs and splits the cost with his brother. "
        "How much does Sam pay?",
        full_registry,
    )
    assert r.answer.kind == "decline"
