"""Phase B reader 51: fronted predicative adjunct plus a ground event."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Atom


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/ground-verbal-after-being-adjective"


def _facts(text: str) -> list[Atom]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Atom)
        if fact.provenance.source == SOURCE
    ]


def test_emits_only_the_complete_main_event() -> None:
    facts = _facts("After being injured, Ada retired in 2018.")
    assert [(f.entity, f.pred, f.polarity) for f in facts] == [
        ("ada", "retire in 2018", True),
    ]


def test_does_not_mint_an_independent_adjunct_property() -> None:
    result = solve(
        "After being injured, Ada retired in 2018. Is it true that Ada is injured?",
        REGISTRY,
    )
    assert result.value == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "Before being injured, Ada retired in 2018.",
        "After getting injured, Ada retired in 2018.",
        "After being injured Ada retired in 2018.",
        "After being injured, she retired in 2018.",
        "After being injured, Ada did not retire in 2018.",
        "After being injured, Ada retired and moved in 2018.",
        "After being injured, Ada retired.",
        "After being injured, Ada retired in 2018",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
