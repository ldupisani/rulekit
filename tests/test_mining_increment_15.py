"""Increment 15: subject-priced items — 'ITEM cost(s) $X each' — a price
stated with the ITEM as grammatical SUBJECT, not the object of buy. 'cost'
gains a verb sense (packs/difg-mined lexicon), gated by a new price_verb
category; learn.py emits a Price fact keyed on the SUBJECT noun when a
price_verb's dobj is a currency-valued count noun followed by the existing
distributive-'each' structure (reused, unwidened, from increment 10's
_is_rate/_rate_unit). The increment-10 purchase-total consumer in answer.py
matches these item-keyed Price facts against purchase quantities by item
noun with zero changes of its own. Synthetic only."""

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


def test_subject_priced_item_feeds_purchase_total(full_registry):
    r = solve(
        "Eggs cost $2 each. Tom buys 5 eggs. How much does Tom spend?",
        full_registry,
    )
    assert r.answer.value == 10


def test_subject_priced_item_pay_verb(full_registry):
    r = solve(
        "Apples cost $3 each. Sam buys 4 apples. How much did Sam pay?",
        full_registry,
    )
    assert r.answer.value == 12


def test_subject_priced_item_plural_verb_form(full_registry):
    # 'costs' (third-person singular subject) must resolve to the same
    # 'cost' lemma and gate through the same price_verb category
    r = solve(
        "A pencil costs $1 each. Mia buys 6 pencils. How much does Mia spend?",
        full_registry,
    )
    assert r.answer.value == 6


def test_two_subject_priced_items_sum(full_registry):
    r = solve(
        "Eggs cost $2 each. Apples cost $3 each. "
        "Tom buys 5 eggs. Tom buys 4 apples. How much does Tom spend in total?",
        full_registry,
    )
    assert r.answer.value == 22


def test_lump_sum_cost_without_each_declines(full_registry):
    # no distributive 'each' — a lump-sum statement, not a per-unit price;
    # must not be treated as $2/egg
    r = solve(
        "Eggs cost $2. Tom buys 5 eggs. How much does Tom spend?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_noun_sense_of_cost_still_wins_with_article(full_registry):
    # 'the cost' stays a noun (coverage arbitration, not a special case) —
    # 'cost' gaining a verb sense must not break this ordinary reading
    r = solve(
        "The cost of the trip was $50. How much did Nina and Sam spend on "
        "the trip together?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_rate_marker_per_is_not_a_subject_priced_each(full_registry):
    # 'per NOUN' is a different (unbuilt) rate reading, not the distributive
    # 'each' this class targets — must not misfire as $2/egg
    r = solve(
        "Eggs cost $2 per dozen. Tom buys 5 eggs. How much does Tom spend?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_split_cost_still_declines_with_subject_priced_source(full_registry):
    # increment 10's invariant must hold no matter which emission site
    # supplied the Price fact: a 'splits the cost' predicate on the buyer
    # means the raw total isn't what they actually paid
    r = solve(
        "Eggs cost $2 each. Tom buys 5 eggs and splits the cost with his "
        "brother. How much did Tom pay?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_unrelated_ask_verb_does_not_borrow_subject_priced_total(full_registry):
    r = solve(
        "Eggs cost $2 each. Tom finds 5 eggs. How much does Tom earn?",
        full_registry,
    )
    assert r.answer.kind == "decline"
