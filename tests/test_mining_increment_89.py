"""Mining candidate passive-event-totality-asks: passive-voice, entity-less
event totality asks ("how many X were eaten/sold/given/bought in total?").

Adds `ask/how-many-passive-combined` (packs/arithmetic/rules/core.yaml) — the
passive-voice sibling of ask/how-many-there-combined: a copula ({cat: state}:
is/was/are/were) immediately followed by a bare past-participle verb form
(no subject, no auxiliary, no literal 'there') plus the SAME required
trailing totality marker (optionally preceded by a preposition: "in total",
"altogether", "combined"). Routes to the SAME unchanged 'combined' consumer
(answer.py) every other entity-less totality ask already uses — no new
consumer, no new fact kind, no new vocabulary (every past participle
exercised here already carries sense=verb with its own verb.lemma feature in
the shipped packs). Synthetic only."""

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


def test_passive_totality_three_holders_eat(full_registry):
    r = solve(
        "Priya ate 12 grapes. Owen ate 9 grapes. Maya ate 6 grapes. "
        "How many grapes were eaten in total?",
        full_registry,
    )
    assert r.answer.value == 27


def test_passive_totality_two_holders_sell_altogether(full_registry):
    r = solve(
        "Nadia sold 8 candles. Felix sold 6 candles. "
        "How many candles were sold altogether?",
        full_registry,
    )
    assert r.answer.value == 14


def test_passive_totality_bought_verb(full_registry):
    r = solve(
        "Renata bought 5 marbles. Dmitri bought 7 marbles. "
        "How many marbles were bought in total?",
        full_registry,
    )
    assert r.answer.value == 12


def test_active_twin_unaffected_regression(full_registry):
    # ask/how-many-there-combined (the already-shipped active twin) still
    # answers its own phrasing unchanged — the new passive ask never shadows
    # or competes with it (disjoint literal skeletons, never a tie).
    r = solve(
        "Priya ate 12 grapes. Owen ate 9 grapes. Maya ate 6 grapes. "
        "How many grapes did they eat in total?",
        full_registry,
    )
    assert r.answer.value == 27


def test_bare_passive_without_totality_marker_still_declines(full_registry):
    # No aggregate marker at all -> the new ask must NOT match (it requires
    # the trailing totality marker); this must stay a decline, never route
    # through 'unique-entity' with a signed event fold (which would answer
    # a wrong, sign-flipped number for an event verb like 'eat').
    r = solve(
        "Owen ate 5 grapes. How many grapes were eaten?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_excluded_world_entity_leaves_fewer_than_two_holders_declines(full_registry):
    # mirrors ask/how-many-there-combined's own `exclude_entity: world`
    # discipline: a bare existential scene restatement ("There are N X")
    # must never be summed alongside a real named holder as an independent
    # third holding. With 'world' excluded, only ONE real holder remains,
    # which is below the combined ask's own >=2-holders-or-decline floor.
    r = solve(
        "There are 4 grapes. Owen ate 5 grapes. "
        "How many grapes were eaten in total?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_single_holder_still_declines_without_totality_context(full_registry):
    # a lone holder is still below the combined ask's own plurality floor,
    # independent of the exclude_entity path above
    r = solve(
        "Owen ate 5 grapes. How many grapes were eaten in total?",
        full_registry,
    )
    assert r.answer.kind == "decline"
