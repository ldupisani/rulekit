"""Phase B reader 22: ``Anything P is Q`` / ``No one P is Q`` universals."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Quantified


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "logic/universal-anything-copular",
    "logic/universal-no-one-copular",
}


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


def _facts(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return [
        fact
        for fact in result.store.by_kind(Quantified)
        if fact.provenance.source in SOURCES
    ]


def _verdict(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return result.answer.value if result.answer.kind == "verdict" else result.answer.kind


def test_positive_form_emits_property_universal(logic_reg):
    facts = _facts("Anything happy is friendly.", logic_reg)

    assert [(fact.cls, fact.pred, fact.polarity) for fact in facts] == [
        ("happy", "friendly", True),
    ]


def test_negative_form_drops_the_implicit_one(logic_reg):
    facts = _facts("No one friendly is sleepy.", logic_reg)

    assert [(fact.cls, fact.pred, fact.polarity) for fact in facts] == [
        ("friendly", "sleepy", False),
    ]


def test_named_property_instantiates_positive_consequence(logic_reg):
    assert _verdict(
        "Anything happy is friendly. Rex is happy. "
        "Is it true that Rex is friendly?",
        logic_reg,
    ) == "yes"


def test_positive_and_negative_forms_chain(logic_reg):
    assert _verdict(
        "Anything happy is friendly. No one friendly is sleepy. Rex is happy. "
        "Is it true that Rex is sleepy?",
        logic_reg,
    ) == "no"


def test_missing_property_does_not_instantiate(logic_reg):
    assert _verdict(
        "Anything happy is friendly. Rex is sleepy. "
        "Is it true that Rex is friendly?",
        logic_reg,
    ) == "undetermined"


@pytest.mark.parametrize(
    "sentence",
    [
        "Everything happy is friendly.",
        "Anything not happy is friendly.",
        "Anything happy is not friendly.",
        "Anything happy and sleepy is friendly.",
        "Anything happy is friendly and calm.",
        "Anything that is happy is friendly.",
        "Anything happy can be friendly.",
        "Anything happy is either friendly or calm.",
        "Anything happy eats cheese.",
        "Anything happy is 2 dogs.",
        "No friendly person is sleepy.",
        "No one not friendly is sleepy.",
        "No one friendly is not sleepy.",
        "No one friendly or calm is sleepy.",
    ],
)
def test_adjacent_and_larger_constructions_stay_unread(sentence, logic_reg):
    assert _facts(sentence, logic_reg) == []
