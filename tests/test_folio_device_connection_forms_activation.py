"""Pack-local forms complete existing device universals."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantified


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/universal-copular-all-are"


def _facts(text: str) -> list[Quantified]:
    return [
        f
        for f in solve(text, REGISTRY, tracing=False).store.by_kind(Quantified)
        if f.provenance.source == SOURCE
    ]


def test_participial_class_and_connection_property_remain_complete() -> None:
    facts = _facts("All devices belonging to the studio are connected to HomeHub.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("device belong to studio", "connected to homehub", True),
    ]


@pytest.mark.parametrize(
    "surface",
    [
        "Some devices belonging to the studio are connected to HomeHub.",
        "Every device belonging to the studio is connected to HomeHub.",
        "All devices belonging to the studio are not connected to HomeHub.",
        "All devices belonging to the studio might be connected to HomeHub.",
        "All devices belonging to the studio are connected to HomeHub or LocalHub.",
    ],
)
def test_adjacent_quantifier_signed_modal_and_union_surfaces_refuse(surface: str) -> None:
    assert _facts(surface) == []
