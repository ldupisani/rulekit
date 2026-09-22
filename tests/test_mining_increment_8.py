"""Re-landing steps 3+4: the rate-span committer, conversion spans, the
`entity` slot type (name | common noun | resolved pronoun for ask
subjects), and rate x population built on top of it — population is only
reachable once the ask can name its holder via a common noun
(docs/negative-results.md)."""

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


def test_exact_unit_rate_span(full_registry):
    r = solve("Tom finds 3 coins a day. How many coins does Tom find in 5 days?", full_registry)
    assert r.answer.value == 15


def test_money_rate_span(full_registry):
    r = solve("Tina makes $18 an hour. How much does Tina make in 40 hours?", full_registry)
    assert r.answer.value == 720


def test_conversion_span(full_registry):
    r = solve(
        "Lisa walks 10 meters a minute. How many meters does Lisa walk in 2 hours?",
        full_registry,
    )
    assert r.answer.value == 1200


def test_unconvertible_span_declines(full_registry):
    r = solve(
        "Tom finds 3 coins a day. How many coins does Tom find in 5 gallons?",
        full_registry,
    )
    assert r.answer.kind == "decline"
    assert "conversion" in r.answer.reason


def test_per_individual_rate_times_population(full_registry):
    # 7/day per bird x 5 birds x 4 days
    r = solve(
        "A bird eats 7 berries a day. Samuel has 5 birds. "
        "How many berries do the birds eat in 4 days?",
        full_registry,
    )
    assert r.answer.value == 140


def test_population_across_multiple_holders_sums(full_registry):
    # every holder of the rate's entity-kind contributes to the population
    r = solve(
        "A bird eats 7 berries a day. Samuel has 5 birds. Kevin has 3 birds. "
        "How many berries do the birds eat in 4 days?",
        full_registry,
    )
    assert r.answer.value == 224  # 7 * (5 + 3) * 4


def test_entity_slot_still_requires_name_or_noun(full_registry):
    # a pronoun that never resolves still cannot stand in for "who"
    r = solve(
        "A bird eats 7 berries a day. How many berries does it eat in 4 days?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_rate_without_span_declines(full_registry):
    r = solve("Tom finds 3 coins a day. How many coins does Tom have?", full_registry)
    assert r.answer.kind == "decline"


def test_subtype_qualified_ask_declines(full_registry):
    # value-slot-only ask consumption: the four in "four-minute songs" is
    # never silently absorbed by the item match
    r = solve(
        "Mary added 16 three-minute songs to the playlist. "
        "How many four-minute songs does Mary have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_unused_rate_never_unlocks_other_commits(full_registry):
    # a rate that merely EXISTS is not read: the fold must not commit the
    # bonus while ignoring the wage
    r = solve(
        "Tina makes $18 an hour. Tina got a $50 bonus. "
        "How much does Tina have?",
        full_registry,
    )
    assert r.answer.kind == "decline"
