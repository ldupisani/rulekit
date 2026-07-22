"""Pack-local object morphology completes an existing ground event."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Atom


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/ground-verbal"


def _facts(text: str) -> list[Atom]:
    return [
        f
        for f in solve(text, REGISTRY, tracing=False).store.by_kind(Atom)
        if f.provenance.source == SOURCE
    ]


def test_plural_object_folds_inside_ground_event_key() -> None:
    facts = _facts("Ada made wooden bodies.")
    assert [(f.entity, f.pred, f.polarity) for f in facts] == [
        ("ada", "make wooden body", True),
    ]


@pytest.mark.parametrize(
    "surface",
    [
        "Ada did not make wooden bodies.",
        "Ada might make wooden bodies.",
        "Ada made wooden bodies or frames.",
        "The artist made wooden bodies.",
        "Ada and Bea made wooden bodies.",
    ],
)
def test_adjacent_signed_modal_union_description_and_coordination_surfaces_refuse(surface: str) -> None:
    assert _facts(surface) == []
