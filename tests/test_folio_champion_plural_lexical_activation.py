"""Pack-local title-role morphology activates existing logic readers."""

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


def test_plural_title_role_folds_inside_compound_class() -> None:
    facts = _facts("All regional champions are patient people.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("regional champion", "patient person", True),
    ]


@pytest.mark.parametrize(
    "surface",
    [
        "Some regional champions are patient people.",
        "Every regional champion is a patient person.",
        "All regional champions are not patient people.",
        "All regional champions might be patient people.",
        "All regional champions are patient people or calm people.",
    ],
)
def test_adjacent_quantifier_signed_modal_and_union_surfaces_refuse(surface: str) -> None:
    assert _facts(surface) == []
