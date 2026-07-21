"""Phase B reader 17: ``Every CLS has P``."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Atom, Quantified


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/universal-every-has"


@pytest.fixture(scope="module")
def logic_reg():
    return compile_registry(
        load_packs([
            ROOT / "packs/core-english",
            ROOT / "packs/arithmetic",
            ROOT / "packs/difg-mined",
            ROOT / "projects/scratch/packs/logic",
        ])
    )


def _facts(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return [
        fact
        for fact in result.store.by_kind(Quantified)
        if fact.provenance.source == SOURCE
    ]


def test_emits_exact_positive_possession_key(logic_reg):
    facts = _facts("Every teacher has students.", logic_reg)

    assert [
        (fact.cls, fact.pred, fact.polarity) for fact in facts
    ] == [("teacher", "have student", True)]


def test_positive_possessive_universal_instantiates(logic_reg):
    result = engine.solve(
        "Every teacher has students. Rex is a teacher.",
        logic_reg,
        tracing=False,
    )

    assert any(
        fact.entity == "rex"
        and fact.pred == "have student"
        and fact.polarity is True
        for fact in result.store.by_kind(Atom)
    )


def test_positive_possessive_universal_chains_before_instantiation(logic_reg):
    result = engine.solve(
        "Every teacher has students. Every professor is a teacher. "
        "Rex is a professor.",
        logic_reg,
        tracing=False,
    )

    assert any(
        fact.entity == "rex"
        and fact.pred == "have student"
        and fact.polarity is True
        for fact in result.store.by_kind(Atom)
    )


def test_instantiation_requires_class_membership(logic_reg):
    result = engine.solve(
        "Every teacher has students. Rex is a professor.",
        logic_reg,
        tracing=False,
    )

    assert not any(
        fact.entity == "rex" and fact.pred == "have student"
        for fact in result.store.by_kind(Atom)
    )


@pytest.mark.parametrize(
    "surface",
    [
        "All teachers have students.",
        "Every teacher have students.",
        "Every teacher is kind.",
        "Every teacher has no students.",
        "Every teacher has either students or pets.",
        "Every teacher has students and assistants.",
        "Every teacher does not have students.",
        "Every teacher can have students.",
        "Every teacher has taught students.",
        "Every teacher has 3 students.",
        "Every teacher who works has students.",
        "Every teacher and professor has students.",
        "The teacher has students.",
    ],
)
def test_larger_or_distinct_constructions_stay_unread(logic_reg, surface):
    assert _facts(surface, logic_reg) == []
