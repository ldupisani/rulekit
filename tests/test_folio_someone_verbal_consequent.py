"""Phase B reader 56: someone-generic verbal consequences."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantified


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/conditional-someone-is-then-they-verbal"


def _facts(text: str) -> list[Quantified]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Quantified)
        if fact.provenance.source == SOURCE
    ]


def test_emits_complete_antecedent_and_verbal_consequence() -> None:
    facts = _facts("If someone is a ranger, then they work at a clinic.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("ranger", "work at clinic", True),
    ]


def test_existing_instantiation_path_applies_the_consequence() -> None:
    result = solve(
        "If someone is a ranger, then they work at a clinic. "
        "Rae is a ranger. Is it true that Rae works at a clinic?",
        REGISTRY,
    )
    assert result.value == "yes"


@pytest.mark.parametrize(
    "surface",
    [
        "If somebody is a lifeguard, then they work at a pool.",
        "If someone is not a lifeguard, then they work at a pool.",
        "If someone is a lifeguard or a teacher, then they work at a pool.",
        "If someone is a lifeguard, then she works at a pool.",
        "If someone is a lifeguard, then they are at a pool.",
        "If someone is a lifeguard, then they do not work at a pool.",
        "If someone is a lifeguard, then they can work at a pool.",
        "If someone is a lifeguard, then they work and live at a pool.",
        "If someone is a lifeguard, then they have worked at a pool.",
        "If someone is a lifeguard, then they work at two pools.",
        "If someone is a lifeguard, then they work at a pool",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
