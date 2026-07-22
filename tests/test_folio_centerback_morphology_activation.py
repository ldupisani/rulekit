"""Closed-compound role morphology activates existing copular universals."""

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


def test_closed_compound_plural_folds_to_singular_role() -> None:
    facts = _facts("All centerbacks are patient people.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("centerback", "patient person", True),
    ]


@pytest.mark.parametrize(
    "surface",
    [
        "Some centerbacks are patient people.",
        "Every centerback is a patient person.",
        "All centerbacks are not patient people.",
        "All centerbacks might be patient people.",
        "All centerbacks are patient people or calm people.",
    ],
)
def test_adjacent_quantifier_signed_modal_and_union_surfaces_refuse(surface: str) -> None:
    assert _facts(surface) == []
