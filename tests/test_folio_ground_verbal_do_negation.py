"""Phase B reader 13: named ``NAME does not V P`` event denials."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Atom


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/ground-verbal-does-not"


@pytest.fixture(scope="module")
def logic_reg():
    return compile_registry(
        load_packs([
            ROOT / "packs/core-english",
            ROOT / "packs/arithmetic",
            ROOT / "packs/difg-mined",
            ROOT / "packs/logic",
        ])
    )


def _source_facts(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return [
        fact
        for fact in result.store.by_kind(Atom)
        if fact.provenance.source == SOURCE
    ]


def test_named_do_support_denial_emits_exact_negative_event_atom(logic_reg):
    facts = _source_facts("Rex does not visit museums.", logic_reg)

    assert [
        (fact.entity, fact.pred, fact.polarity) for fact in facts
    ] == [("rex", "visit museum", False)]


def test_negative_event_atom_refutes_the_positive_verbal_question(logic_reg):
    result = engine.solve(
        "Rex does not visit museums. Is it true that Rex visits museums?",
        logic_reg,
        tracing=False,
    )

    assert result.answer.kind == "verdict"
    assert result.answer.value == "no"


def test_different_entity_does_not_refute_the_question(logic_reg):
    result = engine.solve(
        "Rex does not visit museums. Is it true that Tom visits museums?",
        logic_reg,
        tracing=False,
    )

    assert result.answer.value == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "Rex visits museums.",
        "Rex does visit museums.",
        "Rex does not own a car.",
        "Rex does not have a car.",
        "Rex and Tom do not visit museums.",
        "Rex does not visit museums and galleries.",
        "Rex does not want to visit museums.",
        "Rex does not get up early.",
        "Rex does not visit 3 museums.",
        "If Rex is tired, then Rex does not visit museums.",
    ],
)
def test_larger_or_distinct_constructions_stay_unread(logic_reg, surface):
    assert _source_facts(surface, logic_reg) == []
