"""Mining candidate event-restate-anchor: event-then-restate state
disambiguation in the single-entity fold (`_entity_total`, answer.py).

When a STATE Quantity for an entity/measure is narrated in a LATER sentence
than a prior EVENT Quantity for that same entity/measure, the state sentence
is structurally ambiguous: it may be an independent additional holding (sum,
what the fold already did) OR a RESTATEMENT of the running post-event total
("Kendall finds 6 dimes. She now has 6 dimes." is 6, not 12 — the second
sentence isn't a second holding). Nothing in the fold distinguishes the two
readings, so this increment declines rather than risk a confident double-
count, converting a silent latent wrong into a safe decline. The anchor-
then-event narrative order (a state BEFORE any event for the same
entity/measure) is the ordinary case the fold was built for and is left
completely unaffected — the gate only fires when a state fact's sentence
index is greater than some event's.

All state verbs (have/own/be) are one equivalence class per the campaign
invariant; test cases exercise more than one member of it. Synthetic only —
no GSM8K text."""

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


def test_event_then_restate_declines(full_registry):
    # a single prior event, then a LATER state sentence restating the same
    # value — genuinely ambiguous (independent holding vs. restatement),
    # so this must decline rather than silently sum to 16.
    r = solve(
        "Priya finds 8 marbles. She now has 8 marbles. "
        "How many marbles does Priya have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_multiple_events_then_restate_declines(full_registry):
    # two prior events, then a later state sentence — still ambiguous.
    r = solve(
        "Priya finds 8 marbles. She finds 3 marbles. She now has 8 marbles. "
        "How many marbles does Priya have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_own_verb_equivalence_class_declines(full_registry):
    # 'own' is a member of the same state equivalence class as 'have'.
    r = solve(
        "Marcus buys 4 stickers. He now owns 4 stickers. "
        "How many stickers does Marcus have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_anchor_then_event_still_sums(full_registry):
    # decline-safety in the OTHER direction: a state that PRECEDES every
    # event is the ordinary anchor narrative order and must be unaffected.
    r = solve(
        "Priya has 5 marbles. She finds 8 marbles. "
        "How many marbles does Priya have?",
        full_registry,
    )
    assert r.answer.value == 13


def test_state_only_unaffected(full_registry):
    r = solve(
        "Priya has 8 marbles. How many marbles does Priya have?",
        full_registry,
    )
    assert r.answer.value == 8


def test_event_only_unaffected(full_registry):
    r = solve(
        "Priya finds 8 marbles. How many marbles does Priya have?",
        full_registry,
    )
    assert r.answer.value == 8
