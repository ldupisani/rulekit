"""A pack-local adjective completes existing conditional readings."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Conditional


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/conditional-is-then-they-are"


def _facts(text: str) -> list[Conditional]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Conditional)
        if fact.provenance.source == SOURCE
    ]


def test_adjectival_consequence_is_preserved_exactly() -> None:
    facts = _facts("If a person at the studio is patient, then they are famous.")
    assert [(f.cls, f.pred, f.then_pred, f.polarity) for f in facts] == [
        ("person at studio", "patient", "famous", True),
    ]


@pytest.mark.parametrize(
    "surface",
    [
        "If two people at the studio are patient, then they are famous.",
        "If a person at the studio is patient, then he is famous.",
        "If a person at the studio is patient, then they are not famous.",
        "If a person at the studio is patient, then they might be famous.",
        "If a person at the studio is patient, then they are.",
    ],
)
def test_adjacent_counted_pronominal_signed_modal_and_incomplete_surfaces_refuse(surface: str) -> None:
    assert _facts(surface) == []
