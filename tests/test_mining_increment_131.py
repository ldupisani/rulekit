"""Mining increment 131: unit-normalized task-completion duration gaps."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.consumers import CONSUMERS, ConsumerContext
from rulekit.kernel.engine import solve
from rulekit.kernel.evaluate import ArithmeticLog
from rulekit.kernel.facts import FactStore
from rulekit.kernel.model import TaskCompletionDuration
from rulekit.kernel.patterns import match_ask


@pytest.fixture(scope="module")
def registry():
    return load_project(Path("projects/gsm8k")).registry


STRICT_POSITIVE = (
    "Ari took 42 minutes to finish her task while "
    "Bina took 1.2 hours to finish it. "
    "How many minutes faster did Ari finish the task than Bina?"
)


def test_coordinated_completion_durations_normalize_units(registry):
    result = solve(STRICT_POSITIVE, registry)

    assert result.answer.kind == "number"
    assert result.answer.value == pytest.approx(30.0)
    assert [
        (fact.participant, fact.task, fact.elapsed, fact.unit, fact.verb)
        for fact in result.store.by_kind(TaskCompletionDuration)
    ] == [
        ("ari", "task", 42.0, "minute", "finish"),
        ("bina", "task", 1.2, "hour", "finish"),
    ]
    matched = match_ask(result.question, registry)
    assert matched is not None
    assert matched[0].id == "ask/how-many-unit-task-completion-comparative-than"
    assert matched[1]["direction"] == "faster"


def test_separate_took_finish_paraphrases_and_reordered_names(registry):
    result = solve(
        "Dax took 30 minutes to finish the task. "
        "Cora took 1.5 hours to finish the task. "
        "How many hours slower did Cora finish the task than Dax?",
        registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == pytest.approx(1.0)
    assert {
        (fact.participant, fact.elapsed, fact.unit)
        for fact in result.store.by_kind(TaskCompletionDuration)
    } == {("cora", 1.5, "hour"), ("dax", 30.0, "minute")}


def test_dedicated_vocabulary_is_bounded_and_not_quarantined(registry):
    for form in ("finish", "finished", "finishes"):
        assert registry.word_categories[form] == ("task_completion_verb",)
        assert form not in registry.quarantine
    assert registry.word_categories["faster"] == ("task_completion_faster",)
    assert registry.word_categories["slower"] == ("task_completion_slower",)
    assert "faster" not in registry.quarantine
    assert "slower" not in registry.quarantine


def test_defensive_consumer_guard_rejects_an_undeclared_direction(registry):
    answer = CONSUMERS["completion-duration-difference"](
        ConsumerContext(
            query={
                "a": "ari",
                "b": "bina",
                "task": "task",
                "unit": "minute",
                "direction": "quickly",
            },
            question=None,
            store=FactStore(),
            reg=registry,
            log=ArithmeticLog(),
            match=None,
            ask=None,
        )
    )

    assert not answer.committed
    assert "completion-speed direction" in answer.reason


def test_controlled_boundary_different_tasks_declines(registry):
    result = solve(
        "Ari took 42 minutes to finish the task while "
        "Bina took 1.2 hours to finish the project. "
        "How many minutes faster did Ari finish the task than Bina?",
        registry,
    )

    assert not result.answer.committed
    assert {
        (fact.participant, fact.task)
        for fact in result.store.by_kind(TaskCompletionDuration)
    } == {("ari", "task"), ("bina", "project")}
    assert "arithmetic/coordinated-task-completion-durations" not in {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


@pytest.mark.parametrize(
    "text",
    [
        # Competing durations for one participant/task are ambiguous.
        "Cora took 1 hour to finish the task. "
        "Cora took 2 hours to finish the task. "
        "Dax took 30 minutes to finish the task. "
        "How many minutes slower did Cora finish the task than Dax?",
        # One participant has no compatible duration.
        "Cora took 1 hour to finish the task. "
        "How many minutes slower did Cora finish the task than Dax?",
        # A declared duration unit with no conversion path cannot be guessed.
        "Cora took 1 year to finish the task. "
        "Dax took 30 minutes to finish the task. "
        "How many minutes slower did Cora finish the task than Dax?",
        # Individually valid facts for different tasks cannot be crossed.
        "Cora took 1 hour to finish the task. "
        "Dax took 30 minutes to finish the project. "
        "How many minutes slower did Cora finish the task than Dax?",
        # A self-comparison cannot be treated as a zero gap.
        "Cora took 1 hour to finish the task. "
        "How many minutes faster did Cora finish the task than Cora?",
        # The requested direction must agree with elapsed ordering.
        "Cora took 30 minutes to finish the task. "
        "Dax took 1 hour to finish the task. "
        "How many minutes slower did Cora finish the task than Dax?",
        # Zero elapsed time is not completion-duration evidence.
        "Cora took 0 minutes to finish the task. "
        "Dax took 1 hour to finish the task. "
        "How many minutes faster did Cora finish the task than Dax?",
        # Equal elapsed times license neither faster nor slower.
        "Cora took 30 minutes to finish the task. "
        "Dax took 0.5 hours to finish the task. "
        "How many minutes faster did Cora finish the task than Dax?",
    ],
)
def test_incomplete_ambiguous_or_contradictory_evidence_declines(registry, text):
    assert not solve(text, registry).answer.committed
