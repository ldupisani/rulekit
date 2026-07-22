"""Phase B reader 60: restricted indefinite negative-verbal conditionals."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Atom, Conditional


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/conditional-indefinite-pp-is-then-they-do-not-verbal"


def _facts(text: str) -> list[Conditional]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Conditional)
        if fact.provenance.source == SOURCE
    ]


def test_emits_qualified_class_property_and_negative_event() -> None:
    facts = _facts(
        "If a ranger in Lakeside is patient, then they do not eat berries."
    )
    assert [(f.cls, f.pred, f.then_pred, f.polarity) for f in facts] == [
        ("ranger in lakeside", "patient", "eat berry", False),
    ]


def test_existing_instantiation_requires_both_antecedents() -> None:
    rule = "If a ranger in Lakeside is patient, then they do not eat berries. "
    complete = solve(rule + "Ari is a ranger in Lakeside. Ari is patient.", REGISTRY)
    missing = solve(rule + "Ari is a ranger in Lakeside.", REGISTRY)
    complete_atoms = [
        (fact.entity, fact.pred, fact.polarity)
        for fact in complete.store.by_kind(Atom)
        if fact.entity == "ari" and fact.pred == "eat berry"
    ]
    missing_atoms = [
        fact
        for fact in missing.store.by_kind(Atom)
        if fact.entity == "ari" and fact.pred == "eat berry"
    ]
    assert complete_atoms == [("ari", "eat berry", False)]
    assert missing_atoms == []


@pytest.mark.parametrize(
    "surface",
    [
        "If a ranger is patient, then they do not eat berries.",
        "If rangers in Lakeside are patient, then they do not eat berries.",
        "If a ranger in Lakeside is not patient, then they do not eat berries.",
        "If a ranger in Lakeside is patient, then she does not eat berries.",
        "If a ranger in Lakeside is patient, then they eat berries.",
        "If a ranger in Lakeside is patient, then they cannot eat berries.",
        "If a ranger in Lakeside is patient, then they do not eat and collect berries.",
        "If a ranger in Lakeside is patient, then they have not eaten berries.",
        "If a ranger in Lakeside is patient, then they do not eat two berries.",
        "If a ranger in Lakeside is patient or calm, then they do not eat berries.",
        "If a ranger in Lakeside is patient, then they do not eat berries",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
