"""Reader 41: reduced-passive ``Everything`` disjunctions."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import QuantifiedDisjunction


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/qdisj-everything-reduced-passive-is-either"


def _facts(text: str) -> list[QuantifiedDisjunction]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(QuantifiedDisjunction)
        if fact.provenance.source == SOURCE
    ]


def test_emits_exact_reduced_restriction_and_exclusive_branches() -> None:
    facts = _facts("Everything painted in Studio is either a dog or a cat.")
    assert [(f.cls, f.left, f.right, f.exclusive) for f in facts] == [
        ("paint in studio", "dog", "cat", True),
    ]


def test_composes_with_existing_instantiation_and_elimination() -> None:
    result = solve(
        "Everything painted in Studio is either a dog or a cat. "
        "Ruby is painted in Studio. Ruby is not a dog. "
        "Is it true that Ruby is a cat?",
        REGISTRY,
    )
    assert result.value == "yes"


def test_composition_requires_the_reduced_restriction() -> None:
    result = solve(
        "Everything painted in Studio is either a dog or a cat. "
        "Ruby is painted in Harbor. Ruby is not a dog. "
        "Is it true that Ruby is a cat?",
        REGISTRY,
    )
    assert result.value == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "Anything painted in Studio is either a dog or a cat.",
        "Everyone painted in Studio is either a dog or a cat.",
        "Everything paint in Studio is either a dog or a cat.",
        "Everything paints in Studio is either a dog or a cat.",
        "Everything painting in Studio is either a dog or a cat.",
        "Everything built in Studio is either a dog or a cat.",
        "Everything painted is either a dog or a cat.",
        "Everything painted in Studio was either a dog or a cat.",
        "Everything painted in Studio is a dog or a cat.",
        "Everything painted in Studio is either dog or cat.",
        "Everything painted in Studio is either not a dog or a cat.",
        "Everything painted in Studio is either a dog or not a cat.",
        "Everything painted in Studio is either a dog and horse or a cat.",
        "Everything painted in Studio is either a dog or a cat or a horse.",
        "Everything painted in Studio is either two dogs or a cat.",
        "Everything painted in Studio is either a dog or a cat",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
