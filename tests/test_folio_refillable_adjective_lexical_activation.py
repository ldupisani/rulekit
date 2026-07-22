"""A pack-local adjective completes an existing qualified universal."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantified


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/universal-copular-all-are"


def _facts(text: str) -> list[Quantified]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Quantified)
        if fact.provenance.source == SOURCE
    ]


def test_adjective_is_preserved_after_a_qualified_class() -> None:
    facts = _facts("All velvet-finish lipsticks in the studio set are refillable.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("velvet finish lipstick in studio set", "refillable", True),
    ]


@pytest.mark.parametrize(
    "surface",
    [
        "Some velvet-finish lipsticks in the studio set are refillable.",
        "Every velvet-finish lipstick in the studio set is refillable.",
        "All velvet-finish lipsticks in the studio set are not refillable.",
        "All velvet-finish lipsticks in the studio set might be refillable.",
        "All velvet-finish lipsticks in the studio set are refillable or rare.",
    ],
)
def test_adjacent_quantifier_signed_modal_and_union_surfaces_refuse(surface: str) -> None:
    assert _facts(surface) == []
