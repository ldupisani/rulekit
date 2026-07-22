"""Reader 42: implicit-restrictor negative possession universals."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Atom, Quantified


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/universal-nothing-restricted-has"


def _facts(text: str) -> list[Quantified]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Quantified)
        if fact.provenance.source == SOURCE
    ]


def test_emits_exact_negative_possession_universal() -> None:
    facts = _facts("Nothing near Harbor has a permit.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("near harbor", "have permit", False),
    ]


def test_composes_with_existing_universal_instantiation() -> None:
    result = solve(
        "Nothing near Harbor has a permit. Mia is near Harbor.",
        REGISTRY,
    )
    assert any(
        fact.entity == "mia" and fact.pred == "have permit" and fact.polarity is False
        for fact in result.store.by_kind(Atom)
    )


def test_composition_requires_the_restriction() -> None:
    result = solve(
        "Nothing near Harbor has a permit. Mia is near Station.",
        REGISTRY,
    )
    assert not any(
        fact.entity == "mia" and fact.pred == "have permit" and fact.polarity is False
        for fact in result.store.by_kind(Atom)
    )


@pytest.mark.parametrize(
    "surface",
    [
        "Anything near Harbor has a permit.",
        "No one near Harbor has a permit.",
        "Nothing has a permit.",
        "Nothing near Harbor have a permit.",
        "Nothing near Harbor had a permit.",
        "Nothing near Harbor is permitted.",
        "Nothing not near Harbor has a permit.",
        "Nothing near Harbor and Station has a permit.",
        "Nothing near Harbor has no permit.",
        "Nothing near Harbor has a permit and badge.",
        "Nothing near Harbor can have a permit.",
        "Nothing near Harbor has bought a permit.",
        "Nothing near Harbor has two permits.",
        "Nothing near Harbor has a permit",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
