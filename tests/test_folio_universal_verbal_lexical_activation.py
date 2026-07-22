"""Pack-local vocabulary activates the existing verbal-universal reader."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantified


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/universal-verbal-all"


def _facts(text: str) -> list[Quantified]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Quantified)
        if fact.provenance.source == SOURCE
    ]


def test_qualified_plural_class_preserves_the_complete_universal() -> None:
    facts = _facts("All devices with the studio logo belong to the studio.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("device with studio logo", "belong to studio", True),
    ]


@pytest.mark.parametrize(
    "surface",
    [
        "Some gadgets with the studio logo belong to the studio.",
        "All gadget with the studio logo belongs to the studio.",
        "All gadgets with the studio logo do not belong to the studio.",
        "Every gadget with the studio logo belongs to the studio.",
        "All gadgets with the studio logo belong to the studio or the gallery.",
    ],
)
def test_adjacent_non_universal_or_non_atomic_surfaces_refuse(surface: str) -> None:
    assert _facts(surface) == []
