"""Mining candidate particle-event-verbs: phrasal/particle event verbs
(VERB + away/out/off/up) as ordinary signed events.

A polarity-tagged event verb ('gives', 'gave', 'ate', ...) immediately
followed by a directional particle ('away'/'out'/'off'/'up') otherwise
reads as a verb plus a free adverb — the particle orphans the fraction or
count it modifies, tripping the value-accounting guard on an unaccounted
number. condense.py's merge-particle-verb pass fuses the pair into ONE
verb lexeme, keeping the base verb's own lemma (and hence its polarity
category), so the existing single-entity signed fold can consume the
fraction it would otherwise have declined.

Decline-safety is the whole point of the gate: the merge fires ONLY when
the base verb already carries a polarity tag (_has_event_polarity, the
increment-45 invariant). An UNTAGGED verb plus a particle — including the
"take up to N" capacity-modal shape, whose verb ('take') carries no
polarity category in this pack — must stay declined exactly as before.

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


def test_gives_away_fraction_of_pool(full_registry):
    r = solve(
        "Priya has 20 marbles. Priya gives away 1/4 of the marbles. "
        "How many marbles does Priya have left?",
        full_registry,
    )
    assert r.answer.value == 15


def test_gave_away_spelled_fraction(full_registry):
    r = solve(
        "Jamal has 30 stickers. Jamal gave away half of the stickers. "
        "How many stickers does Jamal have left?",
        full_registry,
    )
    assert r.answer.value == 15


def test_gives_away_third(full_registry):
    r = solve(
        "Noor has 12 pencils. Noor gives away 1/3 of the pencils. "
        "How many pencils does Noor have left?",
        full_registry,
    )
    assert r.answer.value == 8


def test_untagged_verb_plus_particle_still_declines(full_registry):
    # 'look' carries no polarity category -> no merge, no signed event ->
    # decline exactly as before this candidate.
    r = solve(
        "Owen looks up 4 words in the dictionary. "
        "How many words does Owen have left?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_take_up_to_capacity_trap_stays_declined(full_registry):
    # 'take' is untagged for polarity in this pack (category 'accompany',
    # not 'acquire'/'lose') -> the capacity-modal "take up to N" reading
    # must NOT be swept into a merged event verb.
    r = solve(
        "Diego can take up to 12 people on the boat. "
        "How many people can Diego take?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_dobj_crossing_particle_stays_unmerged(full_registry):
    # the particle is not IMMEDIATELY after the verb ("took two letters
    # off") -> out of scope for this increment's adjacent-only merge;
    # must stay decline-safe, not a false positive.
    r = solve(
        "Marco took two letters off the shelf. "
        "How many letters does Marco have left?",
        full_registry,
    )
    assert r.answer.kind == "decline"
