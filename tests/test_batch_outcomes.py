"""Invented disjoint-batch fractions, with complete-population complements."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import BatchEvidence


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/curated")).registry


def story(opening="Mira starts with 150 tennis balls.",
          first="Out of the first 90 balls, she manages to hit 1/3 of them.",
          following="Of the next 60 tennis balls, she manages to hit half of them.",
          ask="Out of all the tennis balls, how many did Mira not hit?"):
    return " ".join((opening, first, following, ask))


@pytest.mark.parametrize("opening", [
    "Mira starts with 150 tennis balls.",
    "Mira started with 150 tennis balls.",
    "Mira has 150 tennis balls.",
    "Mira loads the machine with 150 tennis balls.",
    "Mira loads up the machine with 150 tennis balls to start with.",
    "Mira loaded a basket with 150 tennis balls.",
    "Mira is going to practice playing tennis with a tennis ball machine that shoots out tennis balls for Mira to hit. "
    "She loads up the machine with 150 tennis balls to start with.",
])
@pytest.mark.parametrize("ask,value", [
    ("Out of all the tennis balls, how many did Mira not hit?", 90),
    ("Of all the balls, how many did Mira not hit?", 90),
    ("How many tennis balls did Mira not hit?", 90),
    ("How many balls did Mira not hit in all?", 90),
    ("Out of all the tennis balls, how many did Mira hit?", 60),
    ("How many tennis balls did Mira hit?", 60),
])
def test_opening_and_question_paraphrases(reg, opening, ask, value):
    result = solve(story(opening=opening, ask=ask), reg)
    assert result.answer.value == value, result.answer
    assert result.answer.proof


@pytest.mark.parametrize("first,following", [
    ("Of the first 90 balls, Mira hit one third of them.",
     "Out of the next 60 balls, Mira hit 50% of them."),
    ("Out of the first 90 balls, Mira hits 1/3 of them.",
     "Of the next 60 balls, Mira hits 1/2 of them."),
    ("Of the first 90 tennis balls, she managed to hit one third of them.",
     "Of the next 60 balls, she managed to hit half of them."),
])
def test_event_fraction_and_partitive_paraphrases(reg, first, following):
    result = solve(story(first=first, following=following), reg)
    assert result.answer.value == 90, result.answer


@pytest.mark.parametrize("noun,finite,bare", [
    ("boxes", "inspected", "inspect"),
    ("pages", "read", "read"),
    ("apples", "ate", "eat"),
])
def test_same_structure_supports_other_events_and_objects(reg, noun, finite, bare):
    result = solve(
        f"Tova starts with 120 {noun}. Of the first 80 {noun}, she {finite} 5/8 of them. "
        f"Out of the next 40 {noun}, she {finite} one fourth of them. "
        f"How many {noun} did Tova not {bare}?", reg)
    assert result.answer.value == 60, result.answer


def test_three_disjoint_batches_and_repeated_equal_values(reg):
    result = solve(story(
        first="Of the first 60 balls, Mira hit half of them.",
        following="Of the next 30 balls, Mira hit one third of them. "
                  "Of the next 60 balls, Mira hit one third of them.",
    ), reg)
    assert result.answer.value == 90, result.answer
    assert len(result.store.by_kind(BatchEvidence)) == 3


@pytest.mark.parametrize("fraction,value", [("0/5", 120), ("1/1", 30)])
def test_zero_and_complete_outcomes(reg, fraction, value):
    result = solve(story(first=f"Of the first 90 balls, Mira hit {fraction} of them."), reg)
    assert result.answer.value == value, result.answer


@pytest.mark.parametrize("changes", [
    {"opening": ""},
    {"opening": "Mira starts with 160 tennis balls."},
    {"opening": "Mira starts with 140 tennis balls."},
    {"opening": "Mira starts with 150 tennis balls. Tova starts with 20 tennis balls."},
    {"opening": "If Mira starts with 150 tennis balls."},
    {"opening": "Mira has 3 boxes. Mira starts with 150 tennis balls."},
    {"opening": "Mira starts with 150 red tennis balls."},
    {"opening": "Mira starts with Tova's 150 tennis balls."},
    {"opening": "Mira starts with 150 balls."},  # narrower ask is not the whole population
    {"first": "Of the next 90 balls, Mira hit one third of them."},
    {"first": "Of the first 90 red balls, Mira hit one third of them."},
    {"first": "Of Tova's first 90 balls, Mira hit one third of them."},
    {"first": "Of the first 90 balls, Mira hit 4/3 of them."},
    {"first": "Of the first 90 balls, Mira hit 1/7 of them."},
    {"first": "Of the first 90 balls, Mira did not hit one third of them."},
    {"first": "Of the first 90 balls, Mira will hit one third of them."},
    {"first": "Of the first 90 balls, Mira tries to hit one third of them."},
    {"first": "Of the first 90 balls, Mira manages to hits one third of them."},
    {"following": "Of the first 60 tennis balls, Mira hit half of them."},
    {"following": "Of the next 60 apples, Mira hit half of them."},
    {"following": "Of the next 60 balls, Tova hit half of them."},
    {"following": "Of the next 60 balls, Mira inspected half of them."},
    {"following": "Of the next 60 balls, Mira hit half of them. Mira lost 5 balls."},
    {"ask": "How many red balls did Mira not hit?"},
    {"ask": "How many balls did Tova not hit?"},
    {"ask": "How many balls did Mira not inspect?"},
    {"ask": "How many balls did Mira not hit yesterday?"},
    {"ask": "How many balls did Mira hit yesterday?"},
    {"ask": "How many balls did Mira hit on Tuesday?"},
])
def test_ambiguous_partial_or_changed_batch_evidence_declines(reg, changes):
    result = solve(story(**changes), reg)
    assert not result.answer.committed, result.answer


def test_unrelated_answer_cannot_drop_batch_evidence(reg):
    result = solve(story(ask="Tova has 8 apples. How many apples does Tova have?"), reg)
    assert not result.answer.committed


def test_initial_population_reuses_existing_fraction_and_transfer_reasoning():
    # Preserve the existing project's event polarity; core does not globally
    # equate beginning an activity with acquiring its objects.
    reg = load_project(Path("projects/gsm8k")).registry
    result = solve("Mira started with 160 marbles. She gave away 30 marbles. "
                   "She gave away 20 marbles. She sold half of the remaining marbles. "
                   "How many marbles does Mira have left?", reg)
    assert result.answer.value == 55, result.answer
    assert not result.store.by_kind(BatchEvidence)


def test_next_counted_noun_and_narrative_adverb_keep_different_readings(reg):
    result = solve("Of the next 60 balls, Mira hit half of them.", reg)
    assert any(u.features.get("qualifier") == "next" for u in result.premises[0].units)
    result = solve("Next, Mira added 3 grams of sugar.", reg)
    assert result.premises[0].units[0].sense() == "adverb"


@pytest.mark.parametrize("rule", [
    "arithmetic/ordered-batch-event-share", "arithmetic/ordered-batch-accomplished-share",
    "arithmetic/loaded-collection-population", "arithmetic/initial-collection-population",
])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_new_premises_generate_and_round_trip(rule, seed):
    from rulekit.generation import generate_candidate
    result = generate_candidate(load_project(Path("projects/curated")), rule_id=rule, seed=seed)
    assert result.target_status == "matched", result
