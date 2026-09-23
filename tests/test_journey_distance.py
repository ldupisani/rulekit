"""Invented weekly route schedules, separate rides, and assumed speeds."""

import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def registry():
    return load_project("projects/curated").registry


def story():
    return ("Mira rides her bike back and forth to work for each of her 4 workdays. "
            "Her work is 12 miles away. She also goes for a weekend bike ride of 24 miles. "
            "If she can bike at 12 mph how much time does she spend biking a week?")


def test_distance_schedules_then_speed(registry):
    r = solve(story(), registry)
    assert r.value == 10, r.answer
    assert "120 mile" in r.answer.reason
    assert "4" in r.answer.reason


@pytest.mark.parametrize("old,new,expected", [
    ("4 workdays", "3 workdays", 8),
    ("12 miles away", "6 miles away", 6),
    ("24 miles", "48 miles", 12),
    ("12 mph", "24 mph", 5),
    ("mph how", "mph, how", 10),
    ("mph how", "mph How", 10),
    ("12 miles away", "19.312128 kilometers away", 10),
    ("also goes", "goes", 10),
    ("4 workdays", "8 workdays", None),
    ("4 workdays", "2.5 workdays", None),
    ("12 mph", "0 mph", None),
    ("12 mph", "12 dollars", None),
    ("12 miles away", "12 hours away", None),
    ("Her work", "Her school", None),
    ("she can bike", "Cato can bike", None),
    ("biking a week", "walking a week", None),
    ("biking a week", "biking a month", None),
    ("back and forth", "back", None),
    ("24 miles.", "24 miles. She also walks 5 miles.", None),
    ("If she can", "She can", None),
])
def test_journey_distance_units_and_guards(registry, old, new, expected):
    r = solve(story().replace(old, new), registry)
    assert r.value == pytest.approx(expected) if expected is not None else r.value is None, r.answer


def test_commutes_without_an_extra_ride(registry):
    text = story().replace("She also goes for a weekend bike ride of 24 miles. ", "")
    assert solve(text, registry).value == 8


def test_extra_rides_are_separate_events(registry):
    text = story().replace("If she can", "She goes for a weekend bike ride of 12 miles. If she can")
    assert solve(text, registry).value == 11


def test_lowercase_boundary_requires_an_exact_declared_assumption(registry):
    text = story().replace("she can bike at 12 mph", "she bought 12 bikes")
    r = solve(text, registry)
    assert r.question.text.startswith("If ")
    assert not r.answer.committed


def test_competing_destination_ownership_is_not_discarded(registry):
    text = story().replace("Her work", "Her Cato's work")
    assert not solve(text, registry).answer.committed


def test_unknown_generation_predicate_reports_a_blocker():
    from types import SimpleNamespace
    from rulekit.data.schemas import WherePredicate
    from rulekit.generation.sample import _where_blocker
    # owner_matches now has a realizer. Whole-span same_phrase remains an
    # intentionally unsupported premise-generation predicate.
    rule = SimpleNamespace(where=[WherePredicate(same_phrase=["a", "b"])],
                           generation_where=[])
    assert _where_blocker(rule) == ["where predicate 'same_phrase' has no current realizer"]


def test_capability_cannot_be_used_as_an_actual_activity_rate(registry):
    from rulekit.kernel.model import JourneyPace, Rate
    r = solve("Mira can bike at 12 mph. How many miles does Mira bike in 2 hours?", registry)
    assert not r.answer.committed
    assert len(r.store.by_kind(JourneyPace)) == 1
    assert not r.store.by_kind(Rate)


@pytest.mark.parametrize("rule", ["owned-workday-return-schedule", "owned-destination-distance", "additional-cycling-journey-distance", "assumed-travel-speed-mph"])
def test_distance_journey_shapes_generate(rule):
    from rulekit.generation import generate_candidate
    c = generate_candidate(load_project("projects/curated"), rule_id="arithmetic/" + rule, seed=11)
    assert c.target_status == "matched"
    assert c.facts
