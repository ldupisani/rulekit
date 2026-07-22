"""Phase B reader 59: PP-restricted singular negative verbal universals."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Atom, Quantified


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/universal-no-singular-pp-verbal"


def _facts(text: str) -> list[Quantified]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Quantified)
        if fact.provenance.source == SOURCE
    ]


def test_emits_complete_pp_restricted_class_and_negative_event() -> None:
    facts = _facts("No dancer in Lakeside struggles with ribbons.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("dancer in lakeside", "struggle with ribbon", False),
    ]


def test_existing_instantiation_requires_the_qualified_class() -> None:
    text = "No dancer in Lakeside struggles with ribbons. "
    qualified = solve(text + "Nia is a dancer in Lakeside.", REGISTRY)
    unqualified = solve(text + "Nia is a dancer.", REGISTRY)
    qualified_atoms = [
        (fact.entity, fact.pred, fact.polarity)
        for fact in qualified.store.by_kind(Atom)
        if fact.entity == "nia" and fact.pred == "struggle with ribbon"
    ]
    unqualified_atoms = [
        fact
        for fact in unqualified.store.by_kind(Atom)
        if fact.entity == "nia" and fact.pred == "struggle with ribbon"
    ]
    assert qualified_atoms == [("nia", "struggle with ribbon", False)]
    assert unqualified_atoms == []


@pytest.mark.parametrize(
    "surface",
    [
        "Dancers in Lakeside struggle with ribbons.",
        "No dancers in Lakeside struggle with ribbons.",
        "None of the dancers in Lakeside struggle with ribbons.",
        "No dancer struggles with ribbons.",
        "No dancer in Lakeside does not struggle with ribbons.",
        "No dancer in Lakeside can struggle with ribbons.",
        "No dancer in Lakeside struggles and competes with ribbons.",
        "No dancer in Lakeside has struggled with ribbons.",
        "No dancer in Lakeside struggles with two ribbons.",
        "No dancer in Lakeside struggles with ribbons or hoops.",
        "No dancer in Lakeside struggles with ribbons",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
