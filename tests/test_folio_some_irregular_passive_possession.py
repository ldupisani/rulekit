"""Reader 45: reduced-passive possessive existentials."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Existential


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/existential-some-irregular-passive-have"


def _facts(text: str) -> list[Existential]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Existential)
        if fact.provenance.source == SOURCE
    ]


def test_emits_the_complete_restricted_existential() -> None:
    facts = _facts("Some teachers made by Orion have a velvet badge.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("teacher make by orion", "have velvet badge", True),
    ]


def test_composes_with_the_exact_existential_ask() -> None:
    result = solve(
        "Some teachers made by Orion have a velvet badge. "
        "Is it true that some teachers made by Orion have a velvet badge?",
        REGISTRY,
    )
    assert result.value == "yes"


def test_composition_preserves_the_agent_restriction() -> None:
    result = solve(
        "Some teachers made by Orion have a velvet badge. "
        "Is it true that some teachers made by Lyra have a velvet badge?",
        REGISTRY,
    )
    assert result.value == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "All teachers made by Orion have a velvet badge.",
        "Some teacher made by Orion has a velvet badge.",
        "Some teachers make by Orion have a velvet badge.",
        "Some teachers painted by Orion have a velvet badge.",
        "Some teachers making badges by Orion have a velvet badge.",
        "Some teachers made for Orion have a velvet badge.",
        "Some teachers made by Orion do not have a velvet badge.",
        "Some teachers made by Orion will have a velvet badge.",
        "Some teachers made by Orion has a velvet badge.",
        "Some teachers made by Orion have velvet badges.",
        "Some teachers made by Orion have a velvet badge and pin.",
        "Some teachers made by Orion have a velvet badge or a satin flower.",
        "Some teachers made by Orion have two velvet badges.",
        "Some teachers made by Orion and Lyra have a velvet badge.",
        "Some teachers made by Orion have a velvet badge",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
