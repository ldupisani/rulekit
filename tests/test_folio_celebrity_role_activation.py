"""A pack-local person role completes an existing generic conditional."""

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


def test_person_role_is_preserved_inside_restricted_conditional() -> None:
    facts = _facts(
        "If a person at the studio is a celebrity, then they are well compensated."
    )
    assert [(f.cls, f.pred, f.then_pred, f.polarity) for f in facts] == [
        ("person at studio", "celebrity", "well compensated", True),
    ]


@pytest.mark.parametrize(
    "surface",
    [
        "If two people at the studio are celebrities, then they are well compensated.",
        "If a person at the studio is a celebrity, then she is well compensated.",
        "If a person at the studio is a celebrity, then they are not well compensated.",
        "If a person at the studio is a celebrity, then they might be well compensated.",
        "If a person at the studio is a celebrity, then they are.",
    ],
)
def test_adjacent_plural_pronominal_signed_modal_and_incomplete_surfaces_refuse(
    surface: str,
) -> None:
    assert _facts(surface) == []
