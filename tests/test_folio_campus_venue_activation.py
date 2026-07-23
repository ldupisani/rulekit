"""A pack-local venue completes an existing modal-passive existential."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Existential


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/existential-some-modal-passive"


def _facts(text: str) -> list[Existential]:
    return [
        f
        for f in solve(text, REGISTRY, tracing=False).store.by_kind(Existential)
        if f.provenance.source == SOURCE
    ]


def test_venue_remains_inside_modal_passive_property() -> None:
    facts = _facts("Some rabbits can be spotted near the campus.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("rabbit", "can be spot near campus", True),
    ]


@pytest.mark.parametrize(
    "surface",
    [
        "All turtles can be spotted near the campus.",
        "No turtles can be spotted near the campus.",
        "Some turtle can be spotted near the campus.",
        "Some turtles cannot be spotted near the campus.",
        "Some turtles can be spotted near the campus or the studio.",
    ],
)
def test_adjacent_universal_negative_agreement_and_union_surfaces_refuse(surface: str) -> None:
    assert _facts(surface) == []
