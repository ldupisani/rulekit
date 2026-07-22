"""Phase B reader 54: modal passive plus local positive coordination."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Atom


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/ground-modal-passive-local-it-positive"


def _facts(text: str) -> list[Atom]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Atom)
        if fact.provenance.source == SOURCE
    ]


def test_preserves_modal_property_and_local_positive_property() -> None:
    facts = _facts("Rex can be spotted near the garden, and it is calm.")
    assert [(f.entity, f.pred, f.polarity) for f in facts] == [
        ("rex", "can be spot near garden", True),
        ("rex", "calm", True),
    ]


def test_local_positive_property_composes() -> None:
    result = solve(
        "Rex can be spotted near the garden, and it is calm. "
        "Is it true that Rex is calm?",
        REGISTRY,
    )
    assert result.value == "yes"


def test_possibility_does_not_assert_actual_spotting() -> None:
    result = solve(
        "Rex can be spotted near the garden, and it is calm. "
        "Is it true that Rex is spotted near the garden?",
        REGISTRY,
    )
    assert result.value == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "An animal can be spotted near the garden, and it is calm.",
        "Rex is spotted near the garden, and it is calm.",
        "Rex will be spotted near the garden, and it is calm.",
        "Rex cannot be spotted near the garden, and it is calm.",
        "Rex can spot the garden, and it is calm.",
        "Rex can be spot near the garden, and it is calm.",
        "Rex can be spotted near the garden and pond, and it is calm.",
        "Rex can be spotted near the garden and it is calm.",
        "Rex can be spotted near the garden, and she is calm.",
        "Rex can be spotted near the garden, and it is not calm.",
        "Rex can be spotted near the garden, and it is calm",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
