"""Reader 37: ``There was a/an CLS PREPOSITION the DESCRIPTION``."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Existential


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/existential-there-was-indefinite-definite-pp"


def _facts(text: str) -> list[Existential]:
    return [
        fact for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Existential)
        if fact.provenance.source == SOURCE
    ]


def test_emits_the_exact_existential_without_a_witness() -> None:
    facts = _facts("There was a lantern festival near the oldest city park.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("lantern festival", "near oldest city park", True),
    ]


def test_composes_with_the_existing_existential_ask() -> None:
    result = solve(
        "There was a dog on the smallest race track. "
        "Is it true that Some dogs are on the smallest race track?",
        REGISTRY,
    )
    assert result.value == "yes"


def test_changed_description_remains_undetermined() -> None:
    result = solve(
        "There was a dog on the smallest race track. "
        "Is it true that Some dogs are on the largest race track?",
        REGISTRY,
    )
    assert result.value == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "There is a dog on the smallest track.",
        "There were dogs on the smallest track.",
        "There was a dog in London.",
        "There was a dog on a small track.",
        "There was the dog on the smallest track.",
        "There was no dog on the smallest track.",
        "There was a dog and cat on the smallest track.",
        "There was a dog on the smallest and oldest track.",
        "There was a dog on the 2 smallest tracks.",
        "There was a cat beside the 3 small watches.",
        "There was a dog on the smallest track in Rome.",
        "There was a dog on the smallest track that closed.",
        "There was a dog on the smallest track",
        "Here was a dog on the smallest track.",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
