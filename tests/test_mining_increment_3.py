"""Increment 3: possessive 's + the precision guards the wider ceiling
forced (number agreement, distributives, clause boundaries, time scoping).
Synthetic strings only."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import analyze, solve

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def full_registry():
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", mined])
    )


def test_possessive_condenses(registry):
    reading = analyze("Tom's garden has 12 flowers.", registry)
    garden = next(u for u in reading.units if "garden" in u.features.get("fold", ""))
    assert garden.sense() == "noun"
    assert "tom" in garden.features.get("attributes", [])
    assert not any(u.features.get("unknown") for u in reading.units)


def test_plural_pronoun_never_binds_a_lone_name(registry):
    # 'they' with a single-name discourse must stay unresolved (no group
    # referents yet), so the event ask declines instead of answering for Tom
    r = solve(
        "Tom bought 2 books. Mary bought 3 books. Tom bought 4 pencils. "
        "How many books did they buy?",
        registry,
    )
    assert r.answer.kind == "decline"


def test_distributive_declines(registry):
    # "2 books for each student" is per-recipient — a rate, not a total
    r = solve(
        "Tom bought 2 books for each student. How many books did Tom buy?", registry
    )
    assert r.answer.kind == "decline"


def test_clause_boundary_blocks_argument_binding(full_registry):
    # "found that ..." — the embedded clause's facts belong to ITS subject
    r = solve(
        "Tom found that Mary has 4 apples. How many apples does Mary have?",
        full_registry,
    )
    assert r.answer.value == 4
    r = solve(
        "Tom found that Mary has 4 apples. How many apples did Tom find?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_mixed_time_facts_decline(full_registry):
    r = solve(
        "Last year Tom made $100. This year Tom made $200. "
        "How much did Tom make?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_same_time_facts_still_fold(registry):
    r = solve("Tom bought 6 eggs. Tom ate 2 eggs. How many eggs does Tom have?", registry)
    assert r.answer.value == 4


def test_counted_noun_is_not_an_agent(full_registry):
    # "made $100 and got $10" must not bind 'got' to the $100 noun
    r = solve("Tom made $100 and got $10. How much did Tom get?", full_registry)
    assert r.answer.value == 10
