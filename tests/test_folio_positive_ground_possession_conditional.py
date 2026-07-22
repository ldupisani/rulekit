"""Reader 47: positive same-name ground possession conditionals."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import PositiveGroundConditional


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/positive-ground-possession-conditional"


def _facts(text: str) -> list[PositiveGroundConditional]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(
            PositiveGroundConditional
        )
        if fact.provenance.source == SOURCE
    ]


def test_emits_the_complete_positive_ground_implication() -> None:
    facts = _facts(
        "If Orion has high ambitions and future goals, then Orion is a "
        "patient artist."
    )
    assert [
        (f.entity, f.pred, f.then_pred, f.then_polarity) for f in facts
    ] == [
        (
            "orion",
            "have high ambitions and future goal",
            "patient artist",
            True,
        )
    ]


def test_composes_with_reader_46s_exact_ground_atom() -> None:
    result = solve(
        "If Orion has a velvet badge, then Orion is a patient artist. "
        "Orion has a velvet badge. Is it true that Orion is a patient artist?",
        REGISTRY,
    )
    assert result.value == "yes"


def test_undecided_antecedent_fires_nothing() -> None:
    result = solve(
        "If Orion has a velvet badge, then Orion is a patient artist. "
        "Is it true that Orion is a patient artist?",
        REGISTRY,
    )
    assert result.value == "undetermined"


def test_changed_property_does_not_fire() -> None:
    result = solve(
        "If Orion has a velvet badge, then Orion is a patient artist. "
        "Orion has a satin flower. Is it true that Orion is a patient artist?",
        REGISTRY,
    )
    assert result.value == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "If the Orion has a velvet badge, then Orion is a patient artist.",
        "If a teacher has a velvet badge, then Orion is a patient artist.",
        "If he has a velvet badge, then Orion is a patient artist.",
        "If Orion does not have a velvet badge, then Orion is a patient artist.",
        "If Orion will have a velvet badge, then Orion is a patient artist.",
        "If Orion can have a velvet badge, then Orion is a patient artist.",
        "If Orion has no velvet badge, then Orion is a patient artist.",
        "If Orion has either a badge or a flower, then Orion is a patient artist.",
        "If Orion has a velvet badge, then Lyra is a patient artist.",
        "If Orion has a velvet badge, then he is a patient artist.",
        "If Orion has a velvet badge, then Orion is not a patient artist.",
        "If Orion has a velvet badge, then Orion can paint murals.",
        "If Orion has a velvet badge, then Orion is either patient or calm.",
        "If Orion has a velvet badge, then Orion is patient and is calm.",
        "If Orion has a velvet badge, then Orion is a patient artist",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
