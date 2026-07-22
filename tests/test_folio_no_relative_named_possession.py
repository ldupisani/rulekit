"""Phase B reader 58: relative-class negative possession universals."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Atom, Quantified


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/universal-no-relative-named-verbal-have"


def _facts(text: str) -> list[Quantified]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Quantified)
        if fact.provenance.source == SOURCE
    ]


def test_emits_complete_relative_class_and_negative_possession() -> None:
    facts = _facts("No facts that Mira knows have proven to be inaccurate.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("fact that mira know", "have proven to be inaccurate", False),
    ]


def test_reader_does_not_assert_a_negative_ground_fact() -> None:
    result = solve("No facts that Mira knows have proven to be inaccurate.", REGISTRY)
    assert [fact for fact in result.store.by_kind(Atom) if not fact.polarity] == []


@pytest.mark.parametrize(
    "surface",
    [
        "Facts that Mira knows have proven to be inaccurate.",
        "No fact that Mira knows has proven to be inaccurate.",
        "No facts which Mira knows have proven to be inaccurate.",
        "No facts that researchers know have proven to be inaccurate.",
        "No facts that she knows have proven to be inaccurate.",
        "No facts that Mira can know have proven to be inaccurate.",
        "No facts that Mira does not know have proven to be inaccurate.",
        "No facts that Mira knows do not prove to be inaccurate.",
        "No facts that Mira knows have proven to be inaccurate and misleading.",
        "No facts that Mira knows will have proven to be inaccurate.",
        "No facts that Mira knows have proven to be inaccurate",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
