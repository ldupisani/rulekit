"""Mining candidate each-determiner-price: determiner-'each' subject prices
('Each ITEM costs $N'). Increment 15 already emits a Price fact keyed on the
subject noun for the TRAILING distributive shape ('Eggs cost $2 each'). This
extends the SAME price_verb emission path (learn.py) to the SUBJECT-SIDE
distributive determiner shape ('Each egg costs $2') by recognizing a
quantifier unit ('each'/'every'/...) whose own `collection` obligation
resolves to the price_verb's subject noun — a purely structural, reverse
obligation lookup (mirrors `_negated`'s pattern), gated on the SAME sense
('quantifier') the trailing form already keys on. No answer.py change: the
increment-10 purchase-total consumer matches Price facts by item noun
regardless of emission site. Synthetic only."""

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


def test_subject_each_determiner_feeds_purchase_total(full_registry):
    r = solve(
        "Tom buys 2 pens. Each pen costs 3 dollars. How much does Tom pay?",
        full_registry,
    )
    assert r.answer.value == 6


def test_subject_each_determiner_spend_verb(full_registry):
    r = solve(
        "Sam buys 4 apples. Each apple costs $2. How much does Sam spend?",
        full_registry,
    )
    assert r.answer.value == 8


def test_subject_every_determiner_same_structure(full_registry):
    # 'every' is the same 'quantifier' sense as 'each' — same structural
    # gate, no separate lexicon branch
    r = solve(
        "Mia buys 6 pencils. Every pencil costs $1. How much does Mia spend?",
        full_registry,
    )
    assert r.answer.value == 6


def test_two_subject_each_determiner_items_sum(full_registry):
    r = solve(
        "Tom buys 2 pens and 3 books. Each pen costs 3 dollars and "
        "each book costs 5 dollars. How much does Tom pay?",
        full_registry,
    )
    assert r.answer.value == 21


def test_trailing_each_form_still_works(full_registry):
    # increment 15's own shape must be unaffected by the new OR-branch
    r = solve(
        "Eggs cost $2 each. Tom buys 5 eggs. How much does Tom spend?",
        full_registry,
    )
    assert r.answer.value == 10


def test_plain_subject_without_distributive_determiner_declines(full_registry):
    # decline-safety: no 'each'/'every' on the subject and no trailing
    # distributive marker — a lump-sum statement, must not be treated as
    # a per-unit price
    r = solve(
        "Tom buys 5 eggs. Eggs cost $2. How much does Tom spend?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_split_cost_still_declines_with_subject_each_source(full_registry):
    # increment 10's invariant must hold no matter which emission site
    # supplied the Price fact
    r = solve(
        "Tom buys 5 eggs and splits the cost with his brother. "
        "Each egg costs $2. How much did Tom pay?",
        full_registry,
    )
    assert r.answer.kind == "decline"
