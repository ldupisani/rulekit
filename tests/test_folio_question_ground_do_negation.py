"""Question-side twin for named do-support event denials."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.patterns import match_ask


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "ask/logic-ground-verbal-does-not"


def _matched(text: str):
    result = solve(text, REGISTRY, tracing=False)
    assert result.question is not None
    return result, match_ask(result.question, REGISTRY)


@pytest.mark.parametrize("surface", ["does not", "doesn't"])
def test_exact_negative_event_question_refutes_a_positive_fact(surface: str) -> None:
    result, matched = _matched(
        "Nadia visits the coastal archive. "
        f"Is it true that Nadia {surface} visit the coastal archive?"
    )
    assert matched is not None
    assert matched[0].id == SOURCE
    assert result.answer.kind == "verdict"
    assert result.answer.value == "no"


def test_exact_negative_event_echoes() -> None:
    result, matched = _matched(
        "Nadia does not visit the coastal archive. "
        "Is it true that Nadia doesn't visit the coastal archive?"
    )
    assert matched is not None
    assert matched[0].id == SOURCE
    assert result.answer.value == "yes"


def test_different_event_complement_remains_open_world() -> None:
    result, matched = _matched(
        "Nadia does not visit the coastal archive. "
        "Is it true that Nadia doesn't visit the regional archive?"
    )
    assert matched is not None
    assert matched[0].id == SOURCE
    assert result.answer.value == "undetermined"


@pytest.mark.parametrize(
    "question",
    [
        "Is it true that Nadia did not visit the coastal archive?",
        "Is it true that Nadia might not visit the coastal archive?",
        "Is it true that Nadia does not visit the archive or the gallery?",
        "Is it true that Nadia does not visit the archive and the gallery?",
        "Is it true that Nadia does not have visited the coastal archive?",
        "Is it true that Nadia does not visit 3 museums?",
    ],
)
def test_tense_modal_coordinated_perfect_and_counted_neighbors_refuse(
    question: str,
) -> None:
    _, matched = _matched(question)
    assert matched is None or matched[0].id != SOURCE


def test_existing_object_class_question_keeps_its_specific_consumer() -> None:
    _, matched = _matched(
        "Is it true that Nadia does not work for a regional museum?"
    )
    assert matched is not None
    assert matched[0].id == "ask/logic-verbal-obj-class-does-not"
