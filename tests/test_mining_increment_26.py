"""Increment (interchangeable-measure): category-sibling measure resolution
is now opt-in per category. `_resolve_measure` let an ask noun with no facts
of its own resolve to the UNIQUE in-store member of its semantic category —
right for currency (money → the one currency in play), a confident-wrong for
sibling count nouns ("20 pets. 8 of them are dogs. How many cats?" answered
8 via 'animal'). Categories now declare `interchangeable: true` (currency
only) to permit it; all other category siblings decline. Synthetic only."""

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


def test_sibling_noun_never_stands_in(full_registry):
    # the reported confident-wrong: a cats ask must not answer from dog facts
    r = solve(
        "Tom has 20 pets. 8 of them are dogs. How many cats are there?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_sibling_noun_declines_even_without_partition(full_registry):
    # same class, no partition machinery involved — the bug predates it
    r = solve(
        "Mia has 8 dogs. How many cats are there?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_currency_still_interchangeable(full_registry):
    r = solve(
        "Sara has 5 dollars. Ben gives her 3 dollars. "
        "How much money does Sara have?",
        full_registry,
    )
    assert r.answer.value == 8


def test_own_facts_still_resolve(full_registry):
    r = solve(
        "Tom has 20 pets. 8 of them are dogs. How many dogs are there?",
        full_registry,
    )
    assert r.answer.value == 8


def test_asked_measure_with_own_facts_never_collapses(full_registry):
    # both siblings have facts: each ask answers from ITS OWN measure
    r = solve(
        "Ann has 3 cats. Ann has 8 dogs. How many cats does Ann have?",
        full_registry,
    )
    assert r.answer.value == 3
