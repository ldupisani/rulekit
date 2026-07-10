"""Re-landing step 2: the NARROW rate-span committer — exact units, lone
rates, populations decline. Conversion and population lift later behind
their own TEST looks (docs/negative-results.md)."""

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


def test_conversion_span_declines_for_now(full_registry):
    r = solve(
        "Lisa walks 10 meters a minute. How many meters does Lisa walk in 2 hours?",
        full_registry,
    )
    assert r.answer.kind == "decline"
    assert "conversion" in r.answer.reason


def test_population_declines_for_now(full_registry):
    r = solve(
        "A bird eats 7 berries a day. Samuel has 5 birds. "
        "How many berries does the bird eat in 4 days?",
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
