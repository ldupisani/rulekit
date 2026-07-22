"""Phase B reader 55: restrictive-only modal-passive class union."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import QuantifiedDisjunction


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/qdisj-only-modal-passive-union"


def _facts(text: str) -> list[QuantifiedDisjunction]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(QuantifiedDisjunction)
        if fact.provenance.source == SOURCE
    ]


def test_emits_complete_restricted_class_and_inclusive_union() -> None:
    facts = _facts(
        "The only animals that can be spotted near the garden are cats and dogs."
    )
    assert [(f.cls, f.left, f.right, f.exclusive) for f in facts] == [
        ("animal can be spot near garden", "cat", "dog", False),
    ]


def test_union_alone_asserts_neither_branch() -> None:
    result = solve(
        "The only animals that can be spotted near the garden are cats and dogs. "
        "Rex is an animal can be spot near garden. Is it true that Rex is a cat?",
        REGISTRY,
    )
    assert result.value == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "Animals that can be spotted near the garden are cats and dogs.",
        "The only animal that can be spotted near the garden is a cat and a dog.",
        "The only animals that are spotted near the garden are cats and dogs.",
        "The only animals that can spot the garden are cats and dogs.",
        "The only animals that can be spot near the garden are cats and dogs.",
        "The only animals that cannot be spotted near the garden are cats and dogs.",
        "The only animals that can be spotted near the garden are cats or dogs.",
        "The only animals that can be spotted near the garden are cats, dogs, and foxes.",
        "The only animals that can be spotted near the garden are a cat and a dog.",
        "The only animals that can be spotted near the garden are cats and not dogs.",
        "The only animals that can be spotted near the garden are cats and dogs",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
