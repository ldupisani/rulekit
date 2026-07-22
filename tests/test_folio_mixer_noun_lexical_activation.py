"""A pack-local venue noun completes existing PP-qualified universals."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantified


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/universal-copular-every-is"


def _facts(text: str) -> list[Quantified]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Quantified)
        if fact.provenance.source == SOURCE
    ]


def test_venue_remains_inside_the_complete_qualified_class() -> None:
    facts = _facts("Every champion at the mixer is a patient person.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("champion at mixer", "patient person", True),
    ]


@pytest.mark.parametrize(
    "surface",
    [
        "Some champions at the mixer are patient people.",
        "All champions at the mixer are patient people.",
        "Every champion at the mixer is not a patient person.",
        "Every champion near the mixer might be a patient person.",
        "Every champion at the mixer is a patient person or a calm person.",
    ],
)
def test_adjacent_quantifier_signed_modal_and_union_surfaces_refuse(surface: str) -> None:
    assert _facts(surface) == []
