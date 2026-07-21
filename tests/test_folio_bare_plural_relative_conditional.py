"""Phase B reader 8: ``CLSs who are P are [not] Q`` conditionals."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Conditional


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "logic/conditional-bare-plural-who-are",
    "logic/conditional-bare-plural-who-are-not",
}


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
        for fact in result.store.by_kind(Conditional)
        if fact.provenance.source in SOURCES
    ]


def _verdict(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return result.answer.value if result.answer.kind == "verdict" else result.answer.kind


def test_positive_form_emits_exact_conditional(logic_reg):
    facts = _facts("Dogs who are happy are friendly.", logic_reg)

    assert [
        (f.cls, f.pred, f.then_pred, f.polarity) for f in facts
    ] == [("dog", "happy", "friendly", True)]


def test_negative_form_emits_exact_conditional(logic_reg):
    facts = _facts("Dogs who are happy are not friendly.", logic_reg)

    assert [
        (f.cls, f.pred, f.then_pred, f.polarity) for f in facts
    ] == [("dog", "happy", "friendly", False)]


def test_composition_requires_class_and_relative_property(logic_reg):
    assert _verdict(
        "Dogs who are happy are friendly. Rex is a dog. Rex is happy. "
        "Is it true that Rex is friendly?",
        logic_reg,
    ) == "yes"


def test_composition_refuses_missing_class_membership(logic_reg):
    assert _verdict(
        "Dogs who are happy are friendly. Rex is happy. "
        "Is it true that Rex is friendly?",
        logic_reg,
    ) == "undetermined"


def test_composition_refuses_missing_relative_property(logic_reg):
    assert _verdict(
        "Dogs who are happy are friendly. Rex is a dog. "
        "Is it true that Rex is friendly?",
        logic_reg,
    ) == "undetermined"


def test_negative_relative_stays_unread(logic_reg):
    assert _facts("Dogs who are not happy are friendly.", logic_reg) == []


def test_verbal_relative_stays_unread(logic_reg):
    assert _facts("Dogs who chase cats are friendly.", logic_reg) == []


def test_verbal_consequence_stays_unread(logic_reg):
    assert _facts("Dogs who are happy chase cats.", logic_reg) == []


def test_definite_and_counted_subjects_stay_unread(logic_reg):
    assert _facts("The dogs who are happy are friendly.", logic_reg) == []
    assert _facts("Three dogs who are happy are friendly.", logic_reg) == []


def test_singular_subject_stays_unread(logic_reg):
    assert _facts("A dog who is happy is friendly.", logic_reg) == []
