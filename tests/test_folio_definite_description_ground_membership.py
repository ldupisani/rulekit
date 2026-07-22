"""Reader 38: ``The DESCRIPTION is a/an PREDICATE``."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Atom


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/ground-copular-definite-description-is-indefinite"


def _facts(text: str) -> list[Atom]:
    return [
        fact for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Atom)
        if fact.provenance.source == SOURCE
    ]


def test_emits_exact_ground_membership_for_the_described_referent() -> None:
    facts = _facts("The winter city games is a sporting festival.")
    assert [(f.entity, f.pred, f.polarity) for f in facts] == [
        ("winter city game", "sporting festival", True),
    ]


def test_composes_with_existing_universal_instantiation() -> None:
    result = solve(
        "The Winter Gala is a sporting festival. "
        "Every sporting festival is popular. "
        "Is it true that Winter Gala is popular?",
        REGISTRY,
    )
    assert result.value == "yes"


def test_changed_description_remains_undetermined() -> None:
    result = solve(
        "The Winter Gala is a sporting festival. "
        "Every sporting festival is popular. "
        "Is it true that Summer Gala is popular?",
        REGISTRY,
    )
    assert result.value == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "A winter gala is a sporting festival.",
        "Winter Gala is a sporting festival.",
        "The Winter Gala was a sporting festival.",
        "The winter galas are sporting festivals.",
        "The Winter Gala is the sporting festival.",
        "The Winter Gala is sporting.",
        "The Winter Gala is not a sporting festival.",
        "The Winter Gala and Summer Gala is a sporting festival.",
        "The Winter Gala is a sporting festival and concert.",
        "The Winter Gala is a 2 day festival.",
        "The Winter Gala is a sporting festival that tours.",
        "The Winter Gala is a sporting festival",
        "At noon the Winter Gala is a sporting festival.",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
