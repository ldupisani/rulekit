"""Phase B reader 12: plural ``No CLSs V P`` event universals."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Atom, Quantified


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/universal-no-verbal-plural"


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


def _source_facts(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return [
        fact
        for fact in result.store.by_kind(Quantified)
        if fact.provenance.source == SOURCE
    ]


def test_plural_event_universal_emits_folded_class_and_predicate(logic_reg):
    facts = _source_facts("No students visit museums.", logic_reg)

    assert [
        (fact.cls, fact.pred, fact.polarity) for fact in facts
    ] == [("student", "visit museum", False)]


def test_negative_event_universal_chains_to_a_subclass(logic_reg):
    result = engine.solve(
        "No students visit museums. Scholars are students.",
        logic_reg,
        tracing=False,
    )

    assert any(
        fact.cls == "scholar"
        and fact.pred == "visit museum"
        and fact.polarity is False
        for fact in result.store.by_kind(Quantified)
    )


def test_negative_event_universal_instantiates_for_a_named_member(logic_reg):
    result = engine.solve(
        "No students visit museums. Rex is a student.", logic_reg, tracing=False
    )

    assert any(
        fact.entity == "rex"
        and fact.pred == "visit museum"
        and fact.polarity is False
        for fact in result.store.by_kind(Atom)
    )


@pytest.mark.parametrize(
    "surface",
    [
        "All students visit museums.",
        "No student visits museums.",
        "No students can visit museums.",
        "No students who study art visit museums.",
        "No students that study art visit museums.",
        "No students which study art visit museums.",
        "No students do not visit museums.",
        "No students and teachers visit museums.",
        "No students visit museums and galleries.",
        "No students have visited museums.",
        "No students get up early.",
        "No students visit 3 museums.",
    ],
)
def test_larger_or_distinct_constructions_stay_unread(logic_reg, surface):
    assert _source_facts(surface, logic_reg) == []
