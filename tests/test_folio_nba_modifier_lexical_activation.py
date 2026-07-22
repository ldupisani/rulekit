"""A pack-local all-caps modifier activates existing copular readers."""

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


def test_all_caps_modifier_remains_inside_the_complete_class() -> None:
    facts = _facts("All NBA students are clever people.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("nba student", "clever person", True),
    ]


@pytest.mark.parametrize(
    "surface",
    [
        "Some NBA students are clever people.",
        "Every NBA student is a clever person.",
        "All NBA students are not clever people.",
        "All NBA students might be clever people.",
        "All NBA students are clever people or patient people.",
    ],
)
def test_adjacent_quantifier_signed_modal_and_union_surfaces_refuse(surface: str) -> None:
    assert _facts(surface) == []
