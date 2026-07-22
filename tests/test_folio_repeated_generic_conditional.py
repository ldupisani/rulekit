"""Phase B reader 61: repeated-generic copular conditionals."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Atom, Conditional


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/conditional-indefinite-is-repeated-definite-is"


def _facts(text: str) -> list[Conditional]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Conditional)
        if fact.provenance.source == SOURCE
    ]


def test_emits_only_after_exact_generic_phrase_repetition() -> None:
    facts = _facts("If a ranger is patient, the ranger is calm.")
    assert [(f.cls, f.pred, f.then_pred, f.polarity) for f in facts] == [
        ("ranger", "patient", "calm", True),
    ]


def test_existing_instantiation_requires_class_and_property() -> None:
    rule = "If a ranger is patient, the ranger is calm. "
    complete = solve(rule + "Ari is a ranger. Ari is patient.", REGISTRY)
    missing = solve(rule + "Ari is a ranger.", REGISTRY)
    complete_atoms = [
        (fact.entity, fact.pred, fact.polarity)
        for fact in complete.store.by_kind(Atom)
        if fact.entity == "ari" and fact.pred == "calm"
    ]
    missing_atoms = [
        fact
        for fact in missing.store.by_kind(Atom)
        if fact.entity == "ari" and fact.pred == "calm"
    ]
    assert complete_atoms == [("ari", "calm", True)]
    assert missing_atoms == []


@pytest.mark.parametrize(
    "surface",
    [
        "If a ranger is patient, the scout is calm.",
        "If the ranger is patient, the ranger is calm.",
        "If a ranger is patient, a ranger is calm.",
        "If a ranger is not patient, the ranger is calm.",
        "If a ranger is patient, the ranger is not calm.",
        "If a ranger is patient, then the ranger is calm.",
        "If a ranger is patient, they are calm.",
        "If a ranger works nearby, the ranger is calm.",
        "If a ranger is patient or quiet, the ranger is calm.",
        "If two rangers are patient, the rangers are calm.",
        "If a ranger is patient, the ranger is calm",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
