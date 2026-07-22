"""A pack-local adjective completes a negative restricted conditional."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Conditional


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/conditional-someone-restricted-is-then-they-are-not"


def _facts(text: str) -> list[Conditional]:
    return [
        f
        for f in solve(text, REGISTRY, tracing=False).store.by_kind(Conditional)
        if f.provenance.source == SOURCE
    ]


def test_negative_adjectival_consequence_is_preserved_exactly() -> None:
    facts = _facts("If someone in Riverton is patient, then they are not scared of birds.")
    assert [(f.cls, f.pred, f.then_pred, f.polarity) for f in facts] == [
        ("in riverton", "patient", "scared of bird", False),
    ]


@pytest.mark.parametrize(
    "surface",
    [
        "If someone is patient, then they are not scared of birds.",
        "If someone in Riverton is patient, then she is not scared of birds.",
        "If someone in Riverton is not patient, then they are not scared of birds.",
        "If someone in Riverton is patient, then they might not be scared of birds.",
        "If someone in Riverton is patient, then they are not scared of birds or cats.",
    ],
)
def test_adjacent_unrestricted_pronominal_signed_modal_and_union_surfaces_refuse(surface: str) -> None:
    assert _facts(surface) == []
