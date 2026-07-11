"""Increment 11: conjoined purchases — the verb's dobj obligation only
binds the FIRST item in 'A at $X each, B, and C at $Z each'; this recovers
the rest by segmenting the tail on top-level commas/conjunctions,
restricted to purchase-verb dobjs only (a scoped fix, not the general
conjunction-handling gap, which remains open for every other verb).
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


def test_three_conjoined_priced_items(full_registry):
    r = solve(
        "Nina buys three toys at $10 each, two packs of basketball cards at $5 each, "
        "and five shirts at $6 each. How much does Nina spend in all?",
        full_registry,
    )
    assert r.answer.value == 70


def test_conjoined_items_all_same_price(full_registry):
    r = solve(
        "Bruce buys 5 packs of cards at $5 each, 10 books at $5 each, "
        "and 3 toys at $5 each. How much did Bruce spend?",
        full_registry,
    )
    assert r.answer.value == 90


def test_two_conjoined_items(full_registry):
    r = solve(
        "Tim buys 3 toys at $10 each and 2 books at $5 each. How much did Tim pay?",
        full_registry,
    )
    assert r.answer.value == 40


def test_unpriced_conjunct_declines_whole_total(full_registry):
    # the second item has no price of its own -> the whole total declines
    r = solve(
        "Nina buys three toys at $10 each and two shirts. How much does Nina spend?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_unpriced_first_item_does_not_borrow_a_later_price(full_registry):
    # 'toys' has no price of its own; it must NOT silently inherit $5 from
    # 'packs' just because the scan for its own price crosses a comma
    r = solve(
        "Nina buys three toys, two packs at $5 each. How much does Nina spend?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_plain_multi_dobj_conjunction_still_declines(full_registry):
    # EVENT verbs (neither purchase nor state) are UNCHANGED — the general
    # conjunction gap remains open outside this scoped fix. (State verbs
    # gained conjunct recovery in the state-verb-conjunction candidate; this
    # test now exercises an event verb instead, to keep documenting the
    # still-open gap accurately.)
    r = solve(
        "Priya ate 5 apples and 3 eggs. How many apples did Priya eat?",
        full_registry,
    )
    assert r.answer.kind == "decline"
