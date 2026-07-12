"""Mining candidate elided-measure-entity-asks: a NEW ask shape for
questions with no item/measure noun at all — "How many does WHO have?" /
"How many did WHO VERB?" (ask/how-many-entity-elided-measure in
packs/arithmetic/rules/core.yaml). The measure is supplied as the UNIQUE
measure for which the asked entity holds any fact (answer.py's
`single-entity-elided-measure` consumer) — the same unique-pool-in-play
discipline the existing `unique-entity` consumer uses for the mirror case
(entity elided, measure given). More than one measure in play for the
entity must decline, never guess. Synthetic only."""

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


def test_state_verb_elided_measure(full_registry):
    r = solve("Priya has 12 stickers. How many does Priya have?", full_registry)
    assert r.answer.value == 12


def test_event_verb_elided_measure(full_registry):
    r = solve("Oscar made 8 kites. How many did Oscar make?", full_registry)
    assert r.answer.value == 8


def test_two_measures_in_play_declines(full_registry):
    # Priya holds TWO distinct measures (stickers, ribbons) — the
    # elided-measure ask has no way to pick one, so it must decline
    # rather than guess.
    r = solve(
        "Priya has 12 stickers and 4 ribbons. How many does Priya have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_itemed_ask_still_wins_when_item_present(full_registry):
    # a real item noun present in the question must still route to the
    # existing itemed ask (ask/how-many-entity) unchanged — the new
    # elided-measure ask must never shadow it.
    r = solve(
        "Priya has 12 stickers and 4 ribbons. How many stickers does Priya have?",
        full_registry,
    )
    assert r.answer.value == 12


def test_no_facts_for_entity_declines(full_registry):
    # a name with no quantity facts at all: nothing to resolve, decline.
    r = solve("Priya has 12 stickers. How many does Oscar have?", full_registry)
    assert r.answer.kind == "decline"
