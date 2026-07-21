"""Phase B reader 15: ``A/An CLS will not V P``."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Atom, Quantified


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/universal-indefinite-future-not-verbal"


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


def _verdict(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return result.answer.value if result.answer.kind == "verdict" else result.answer.kind


def test_emits_exact_negative_event_key(logic_reg):
    facts = _facts("A student will not visit museums.", logic_reg)

    assert [
        (fact.cls, fact.pred, fact.polarity) for fact in facts
    ] == [("student", "visit museum", False)]


def test_negative_universal_instantiates_and_refutes_positive_question(logic_reg):
    assert _verdict(
        "A student will not visit museums. Rex is a student. "
        "Is it true that Rex visits museums?",
        logic_reg,
    ) == "no"


def test_negative_universal_chains_before_instantiation(logic_reg):
    result = engine.solve(
        "A student will not visit museums. Every artist is a student. "
        "Rex is an artist.",
        logic_reg,
        tracing=False,
    )

    assert any(
        fact.entity == "rex"
        and fact.pred == "visit museum"
        and fact.polarity is False
        for fact in result.store.by_kind(Atom)
    )


def test_composition_requires_class_membership(logic_reg):
    assert _verdict(
        "A student will not visit museums. Rex is an artist. "
        "Is it true that Rex visits museums?",
        logic_reg,
    ) == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "Every student will not visit museums.",
        "Students will not visit museums.",
        "The student will not visit museums.",
        "A student does not visit museums.",
        "A student would not visit museums.",
        "A student will visit museums.",
        "A student will never visit museums.",
        "A student will not be happy.",
        "A student will not want to visit museums.",
        "A student will not get up.",
        "A student and teacher will not visit museums.",
        "A student will not visit museums and galleries.",
        "A student will not visit 3 museums.",
    ],
)
def test_larger_or_distinct_constructions_stay_unread(logic_reg, surface):
    assert _facts(surface, logic_reg) == []
