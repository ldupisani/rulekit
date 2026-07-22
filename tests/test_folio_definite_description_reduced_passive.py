"""Reader 39: definite membership with a reduced passive relative."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Atom


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/ground-copular-definite-description-reduced-passive"


def _facts(text: str) -> list[Atom]:
    return [
        fact for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Atom)
        if fact.provenance.source == SOURCE
    ]


def test_emits_the_complete_reduced_relative_property() -> None:
    facts = _facts("The Winter Hall is a building added near Rome.")
    assert [(f.entity, f.pred, f.polarity) for f in facts] == [
        ("winter hall", "building", True),
        ("winter hall", "building add near rome", True),
    ]


def test_composes_with_existing_exact_membership_ask() -> None:
    result = solve(
        "The Winter Hall is a building added near Rome. "
        "Is it true that Winter Hall is a building added near Rome?",
        REGISTRY,
    )
    assert result.value == "yes"


def test_changed_description_remains_undetermined() -> None:
    result = solve(
        "The Winter Hall is a building added near Rome. "
        "Is it true that Summer Hall is a building added near Rome?",
        REGISTRY,
    )
    assert result.value == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "A Winter Hall is a building added near Rome.",
        "Winter Hall is a building added near Rome.",
        "The Winter Hall was a building added near Rome.",
        "The Winter Hall is the building added near Rome.",
        "The Winter Hall is a building near Rome.",
        "The Winter Hall is not a building added near Rome.",
        "The Winter Hall and Summer Hall is a building added near Rome.",
        "The Winter Hall is a building and theater added near Rome.",
        "The Winter Hall is a building adds near Rome.",
        "The Winter Hall is a building add near Rome.",
        "The Winter Hall is a building was added near Rome.",
        "The Winter Hall is a building built near Rome.",
        "The Winter Hall is a building added.",
        "The Winter Hall is a building added near Rome that reopened.",
        "The Winter Hall is a building added near Rome",
        "At noon the Winter Hall is a building added near Rome.",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
