"""Activity-scoped wage rates paired with converted elapsed durations."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate, list_rule_availability
from rulekit.kernel.engine import solve
from rulekit.kernel.model import ActivityDuration, Rate, RateScope


@pytest.fixture(scope="module")
def registry():
    return load_project(Path("projects/curated")).registry


TARGET = (
    "Natalia earns $12 an hour for gardening. "
    "Yesterday she did 50 minutes of gardening. "
    "How much did she earn?"
)


def test_activity_scoped_wage_converts_elapsed_minutes(registry):
    result = solve(TARGET, registry)

    assert result.answer.kind == "number"
    assert result.answer.value == pytest.approx(10.0)
    assert [
        (fact.entity, fact.measure, fact.value, fact.per, fact.verb)
        for fact in result.store.by_kind(Rate)
    ] == [("natalia", "dollar", 12.0, "hour", "earn")]
    assert [
        (fact.participant, fact.activity, fact.verb)
        for fact in result.store.by_kind(RateScope)
    ] == [("natalia", "gardening", "earn")]
    assert [
        (
            fact.participant,
            fact.activity,
            fact.elapsed,
            fact.unit,
            fact.time,
        )
        for fact in result.store.by_kind(ActivityDuration)
    ] == [("natalia", "gardening", 50.0, "minute", "yesterday")]


@pytest.mark.parametrize(
    "duration_clause",
    (
        "Yesterday she only did 50 minutes of gardening.",
        "Yesterday she did only 50 minutes of gardening.",
        "Yesterday she just did 50 minutes of gardening.",
        "Yesterday she did just 50 minutes of gardening.",
    ),
)
def test_restrictive_focus_preserves_the_stated_activity_duration(
    registry, duration_clause
):
    result = solve(
        "Natalia earns $12 an hour for gardening. "
        f"{duration_clause} How much did she earn?",
        registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == pytest.approx(10.0)


def test_unlicensed_or_repeated_focus_does_not_widen_the_duration_rule(registry):
    for duration_clause in (
        "Yesterday she individually did 50 minutes of gardening.",
        "Yesterday she only did only 50 minutes of gardening.",
    ):
        result = solve(
            "Natalia earns $12 an hour for gardening. "
            f"{duration_clause} How much did she earn?",
            registry,
        )
        assert not result.answer.committed


def test_duration_for_a_different_activity_is_not_borrowed(registry):
    result = solve(
        "Natalia earns $12 an hour for gardening. "
        "Yesterday she did 50 minutes of tutoring. "
        "How much did she earn?",
        registry,
    )

    assert not result.answer.committed
    assert "no unique duration" in result.answer.reason


def test_scoped_rate_does_not_fall_back_to_unqualified_time(registry):
    result = solve(
        "Natalia earns $12 an hour for gardening. "
        "Natalia has 1 hour. How much does Natalia earn?",
        registry,
    )

    assert not result.answer.committed
    assert "no unique duration" in result.answer.reason


def test_another_declared_activity_uses_the_same_construction(registry):
    result = solve(
        "Tariq earns 18 dollars an hour for tutoring. "
        "Yesterday he did 40 minutes of tutoring. "
        "How much did he earn?",
        registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == pytest.approx(12.0)


def test_existing_unscoped_wage_span_path_is_unchanged(registry):
    result = solve(
        "Rob earns 10 dollars an hour. Rob has 8 hours. "
        "How much does Rob earn?",
        registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == pytest.approx(80.0)


def test_both_activity_wage_premises_have_strict_generation_round_trips():
    project = load_project(Path("projects/curated"))
    availability = {
        item.id: item for item in list_rule_availability(project)
    }

    for index, rule_id in enumerate(
        (
            "arithmetic/activity-scoped-wage-rate",
            "arithmetic/performed-activity-duration",
        )
    ):
        assert availability[rule_id].supported
        candidate = generate_candidate(project, rule_id=rule_id, seed=4200 + index)
        assert candidate.target_status in {"matched", "shadowed"}
