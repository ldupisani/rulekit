"""Pack-local plural morphology closes a qualified-class reading gap."""

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


def test_plural_modifier_is_consumed_inside_the_qualified_class() -> None:
    facts = _facts("All students with studio logos are patient people.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("student with studio logo", "patient person", True),
    ]


@pytest.mark.parametrize(
    "surface",
    [
        "Some students with studio logos are patient people.",
        "Every student with a studio logo is a patient person.",
        "All students with studio logos are not patient people.",
        "All students with studio logos might be patient people.",
        "All students with studio logos are patient people or calm people.",
    ],
)
def test_adjacent_quantifier_signed_modal_and_union_surfaces_refuse(surface: str) -> None:
    assert _facts(surface) == []
