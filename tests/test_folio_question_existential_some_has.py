"""Question reader for singular existential possession."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.patterns import match_ask


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "ask/logic-existential-some-has"


def _matched(text: str):
    result = solve(text, REGISTRY, tracing=False)
    assert result.question is not None
    return result, match_ask(result.question, REGISTRY)


def test_negative_universal_refutes_positive_existential() -> None:
    result, matched = _matched(
        "No otter has a badge. Is it true that Some otter has a badge?"
    )
    assert matched is not None
    assert matched[0].id == SOURCE
    assert result.answer.kind == "verdict"
    assert result.answer.value == "no"


def test_named_witness_answers_yes() -> None:
    result, matched = _matched(
        "Nadia is an otter. Nadia has a badge. "
        "Is it true that Some otter has a badge?"
    )
    assert matched is not None
    assert matched[0].id == SOURCE
    assert result.answer.value == "yes"


def test_missing_possession_remains_open_world() -> None:
    result, matched = _matched(
        "Nadia is an otter. Is it true that Some otter has a badge?"
    )
    assert matched is not None
    assert matched[0].id == SOURCE
    assert result.answer.value == "undetermined"


@pytest.mark.parametrize(
    "question",
    [
        "Is it true that Some otter had a badge?",
        "Is it true that Some otter may have a badge?",
        "Is it true that No otter has a badge?",
        "Is it true that Some otter does not have a badge?",
        "Is it true that Some otter has a badge or a ribbon?",
        "Is it true that Some otter has a badge and a ribbon?",
        "Is it true that Some otter has 3 badges?",
    ],
)
def test_past_modal_quantified_signed_coordinated_and_counted_neighbors_refuse(
    question: str,
) -> None:
    _, matched = _matched(question)
    assert matched is None or matched[0].id != SOURCE
