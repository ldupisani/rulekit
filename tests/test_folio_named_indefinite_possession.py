"""Reader 46: named indefinite possession atoms."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Atom


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/ground-named-has-indefinite"


def _facts(text: str) -> list[Atom]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Atom)
        if fact.provenance.source == SOURCE
    ]


def test_emits_the_complete_possession_property() -> None:
    facts = _facts("Orion has a velvet badge.")
    assert [(f.entity, f.pred, f.polarity) for f in facts] == [
        ("orion", "have velvet badge", True),
    ]


def test_composes_with_the_exact_possession_ask() -> None:
    result = solve(
        "Orion has a velvet badge. Is it true that Orion has a velvet badge?",
        REGISTRY,
    )
    assert result.value == "yes"


def test_composition_preserves_the_complete_property() -> None:
    result = solve(
        "Orion has a velvet badge. Is it true that Orion has a satin flower?",
        REGISTRY,
    )
    assert result.value == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "The Orion has a velvet badge.",
        "A teacher has a velvet badge.",
        "He has a velvet badge.",
        "Orion does not have a velvet badge.",
        "Orion will have a velvet badge.",
        "Orion can have a velvet badge.",
        "Orion had a velvet badge.",
        "Orion has velvet badges.",
        "Orion has no velvet badge.",
        "Orion has two velvet badges.",
        "Orion has a velvet badge and pin.",
        "Orion has a velvet badge or a satin flower.",
        "Orion has a badge made by Lyra.",
        "Orion has a velvet badge, Lyra.",
        "Orion has a velvet badge",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
