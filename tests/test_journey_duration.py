"""Synthetic repeated journeys with explicit modes and return legs."""

import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def registry():
    return load_project("projects/curated").registry


def story():
    return ("It takes Mira one hour to walk to school and 30 minutes to ride her bike to school. "
            "Mira walks to and from school twice a week and rides her bike to and from school three times a week. "
            "How many hours in total does she take to get to and from school a week with walking and biking?")


def test_mixed_mode_return_journeys(registry):
    r = solve(story(), registry)
    assert r.value == 7, r.answer
    assert "both legs" in r.answer.reason


@pytest.mark.parametrize("old,new,expected", [
    ("one hour", "two hours", 11),
    ("30 minutes", "one hour", 10),
    ("twice a week", "four times a week", 11),
    ("three times a week", "twice a week", 6),
    ("school", "work", 7),
    ("How many hours", "How many minutes", 420),
    ("with walking and biking", "with biking and walking", 7),
    ("with walking and biking", "with walking and walking", None),
    ("one hour", "zero hours", None),
    ("30 minutes", "30 dollars", None),
    ("Mira walks", "Cato walks", None),
    ("bike to school", "bike to the office", None),
    ("a week with", "a month with", None),
    ("three times a week", "three times a day", None),
    ("to and from school twice", "to school twice", None),
    ("Mira walks", "Mira waits 5 minutes. Mira walks", None),
])
def test_journey_units_scope_and_completeness(registry, old, new, expected):
    r = solve(story().replace(old, new), registry)
    assert r.value == expected, r.answer


def test_independent_duration_and_schedule_clauses_compose(registry):
    text = story().replace("and 30 minutes", ". It takes Mira 30 minutes").replace(
        "and rides her bike", ". Mira rides her bike")
    assert solve(text, registry).value == 7


def test_competing_duration_does_not_pick_one(registry):
    text = "It takes Mira two hours to walk to school. " + story()
    assert not solve(text, registry).answer.committed


@pytest.mark.parametrize("rule", [
    "one-way-journey-duration", "one-way-vehicle-journey-duration",
    "conjoined-journey-durations", "conjoined-vehicle-journey-durations",
    "return-journey-schedule", "return-vehicle-journey-schedule",
    "conjoined-return-journey-schedules", "conjoined-return-vehicle-journey-schedules",
])
def test_journey_shapes_generate(rule):
    from rulekit.generation import generate_candidate
    c = generate_candidate(load_project("projects/curated"), rule_id="arithmetic/" + rule, seed=11)
    assert c.target_status == "matched"
    assert c.facts
