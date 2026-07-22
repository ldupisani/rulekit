"""Pack-local forms activate an existing controlled ground-event reading."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Atom


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/ground-verbal"


def _facts(text: str) -> list[Atom]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Atom)
        if fact.provenance.source == SOURCE
    ]


def test_preserves_complete_controlled_event_key() -> None:
    facts = _facts("Arcadia plots to swallow up some nearby islands.")
    assert [(f.entity, f.pred, f.polarity) for f in facts] == [
        ("arcadia", "plot to swallow up some nearby island", True),
    ]


@pytest.mark.parametrize(
    "surface",
    [
        "Arcadia does not plot to swallow up some nearby islands.",
        "Arcadia will plot to swallow up some nearby islands.",
        "Some nations plot to swallow up some nearby islands.",
        "Arcadia plots to swallow up some nearby islands or peninsulas.",
    ],
)
def test_signed_modal_generic_and_disjunctive_siblings_do_not_use_ground_reader(
    surface: str,
) -> None:
    assert _facts(surface) == []
