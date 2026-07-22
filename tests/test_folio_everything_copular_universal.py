"""Reader 43: implicit-restrictor ``Everything P is Q`` universals."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantified


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/universal-everything-copular"


def _facts(text: str) -> list[Quantified]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Quantified)
        if fact.provenance.source == SOURCE
    ]


def test_emits_exact_implicit_restriction_and_property() -> None:
    facts = _facts("Everything near Harbor is quiet.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("near harbor", "quiet", True),
    ]


def test_composes_with_existing_universal_instantiation() -> None:
    result = solve(
        "Everything near Harbor is quiet. Mia is near Harbor. "
        "Is it true that Mia is quiet?",
        REGISTRY,
    )
    assert result.value == "yes"


def test_composition_requires_the_restriction() -> None:
    result = solve(
        "Everything near Harbor is quiet. Mia is near Station. "
        "Is it true that Mia is quiet?",
        REGISTRY,
    )
    assert result.value == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "Anything near Harbor is quiet.",
        "Everyone near Harbor is quiet.",
        "Everything is quiet.",
        "Everything near Harbor was quiet.",
        "Everything near Harbor is not quiet.",
        "Everything near Harbor and Station is quiet.",
        "Everything near Harbor is quiet and calm.",
        "Everything near Harbor is quiet or calm.",
        "Everything near Harbor is either quiet or calm.",
        "Everything near Harbor has a permit.",
        "Everything near Harbor is buying permits.",
        "Everything near Harbor can be quiet.",
        "Everything near Harbor is two objects.",
        "Everything near Harbor is quiet",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
