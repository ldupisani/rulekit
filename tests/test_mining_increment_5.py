"""Increment 5 (premise machinery): existential premises, the fraction
family, and rest-of-pool chains. Synthetic strings only."""

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


def test_located_existential(registry):
    r = solve("There are 15 flowers in the garden. How many flowers are in the garden?", registry)
    assert r.answer.value == 15


def test_bare_existential(registry):
    r = solve("There are 12 books. How many books are there?", registry)
    assert r.answer.value == 12


def test_aggregate_existential_is_a_total_not_a_holding(registry):
    # "There are 160 toys altogether" is a sum CONSTRAINT — never a holding
    r = solve(
        "Tom has 3 more marbles than Mary. There are 9 marbles altogether. "
        "How many marbles are there in the box?",
        registry,
    )
    assert r.answer.kind == "decline"


def test_fraction_of_pool(registry):
    r = solve(
        "Tom found 12 eggs. Tom ate half of the eggs. How many eggs are left?", registry
    )
    assert r.answer.value == 6


def test_fraction_chain_sequences(registry):
    r = solve(
        "Tom found 12 eggs. Tom ate half of the eggs. Tom gave 2 eggs to Mary. "
        "How many eggs are left?",
        registry,
    )
    assert r.answer.value == 4


def test_percent_of_money(full_registry):
    r = solve(
        "Tom has 20 dollars. Tom spent 40% of the money. How much does Tom have left?",
        full_registry,
    )
    assert r.answer.value == 12


def test_word_fraction_merges(registry):
    r = solve(
        "Tom found 12 eggs. Tom ate one half of the eggs. How many eggs are left?",
        registry,
    )
    assert r.answer.value == 6


def test_fraction_of_pronoun_unique_pool(registry):
    # rules re-run after discourse binding resolves the subject pronoun
    r = solve(
        "Mary found 28 coins. She lost one fourth of it. How many coins are left?",
        registry,
    )
    assert r.answer.value == 21


def test_fraction_pool_spans_entities(registry):
    # "THE eggs" is the definite pool — everyone's eggs (12 + 10)
    r = solve(
        "Tom found 12 eggs. Mary found 10 eggs. Tom ate half of the eggs. "
        "How many eggs did Tom eat?",
        registry,
    )
    assert r.answer.value == 11


def test_fraction_with_no_pool_declines(registry):
    # nothing to anchor "half of the eggs" against — unresolved, decline
    r = solve(
        "Tom ate half of the eggs. How many eggs did Tom eat?", registry
    )
    assert r.answer.kind == "decline"


def test_rest_of_pool(full_registry):
    r = solve(
        "Tom found 8 apples. Tom ate 3 apples. Tom sold the rest. "
        "How many apples did Tom sell?",
        full_registry,
    )
    assert r.answer.value == 5


def test_rest_after_fraction(full_registry):
    r = solve(
        "Tom found 12 eggs. Tom ate half of the eggs. Tom sold the rest. "
        "How many eggs did Tom sell?",
        full_registry,
    )
    assert r.answer.value == 6


def test_combined_ask_requires_plurality(registry):
    # the permissive scan's Σ-over-one artifact: "do they have altogether"
    # asserts plurality, so a single holder declines
    r = solve(
        "Tom has 7 coins. How many coins do they have altogether?", registry
    )
    assert r.answer.kind == "decline"
    assert "at least two holders" in r.answer.reason


def test_fraction_of_rest_chain(full_registry):
    # sequential remainder chain: 28 - 4 = 24, then half of the rest = 12
    r = solve(
        "Leah earned 28 dollars. She spent a seventh of it. She lost half "
        "of the rest. How much does she have left?",
        full_registry,
    )
    assert r.answer.value == 12


def test_fraction_of_remaining_noun(full_registry):
    r = solve(
        "Tom found 12 eggs. Tom ate half of the eggs. Tom ate a third of "
        "the remaining eggs. How many eggs are left?",
        full_registry,
    )
    assert r.answer.value == 4


def test_unknown_polarity_verb_declines(full_registry):
    # 'put half of the rest in the basket' — put has no polarity tag; the
    # fold must never default it to +1 (a deposit is not income)
    r = solve(
        "Tom found 12 eggs. Tom put half of the rest in the basket. "
        "How many eggs are left?",
        full_registry,
    )
    assert r.answer.kind == "decline"
