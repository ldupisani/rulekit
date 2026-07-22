"""Reader 48: plural-agreeing intransitive verbal existentials."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Existential


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/existential-some-intransitive"


def _facts(text: str) -> list[Existential]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Existential)
        if fact.provenance.source == SOURCE
    ]


def test_emits_exact_intransitive_existential() -> None:
    facts = _facts("Some dogs swim.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("dog", "swim", True),
    ]


def test_exact_question_twin_composes() -> None:
    result = solve(
        "Some dogs swim. Is it true that some dogs swim?",
        REGISTRY,
    )
    assert result.value == "yes"


def test_changed_event_remains_undetermined() -> None:
    result = solve(
        "Some dogs swim. Is it true that some dogs run?",
        REGISTRY,
    )
    assert result.value == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "A dog swims.",
        "Some dog swims.",
        "Some dogs are swimmers.",
        "Some dogs have collars.",
        "Some dogs can swim.",
        "Some dogs do not swim.",
        "Some dogs swim quickly.",
        "Some dogs swim and run.",
        "Some trained dogs swim.",
        "Some two dogs swim.",
        "Some dogs swam.",
        "Some dogs swim",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
