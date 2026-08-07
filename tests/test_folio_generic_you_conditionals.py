"""Phase B reader 23: generic ``If you are P, then you are Q``."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Quantified


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/conditional-generic-you-are-then-you-are"


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
        if fact.provenance.source == SOURCE
    ]


def _verdict(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return result.answer.value if result.answer.kind == "verdict" else result.answer.kind


def test_emits_generic_property_implication(logic_reg):
    facts = _facts("If you are a cat, then you are an animal.", logic_reg)

    assert [(fact.cls, fact.pred, fact.polarity) for fact in facts] == [
        ("cat", "animal", True),
    ]


def test_named_member_instantiates_consequence(logic_reg):
    assert _verdict(
        "If you are a cat, then you are an animal. Rex is a cat. "
        "Is it true that Rex is an animal?",
        logic_reg,
    ) == "yes"


def test_generic_condition_composes_with_universal_chain(logic_reg):
    assert _verdict(
        "All pets are cats. If you are a cat, then you are an animal. "
        "Rex is a pet. Is it true that Rex is an animal?",
        logic_reg,
    ) == "yes"


def test_missing_antecedent_does_not_instantiate(logic_reg):
    assert _verdict(
        "If you are a cat, then you are an animal. Rex is a pet. "
        "Is it true that Rex is an animal?",
        logic_reg,
    ) == "undetermined"


@pytest.mark.parametrize(
    "sentence",
    [
        "If he is a cat, then he is an animal.",
        "If you are a cat, then they are animals.",
        "If you are a cat then you are an animal.",
        "If you are not a cat, then you are an animal.",
        "If you are a cat, then you are not an animal.",
        "If you are a cat or dog, then you are an animal.",
        "If you are a cat, then you are an animal and a pet.",
        "If you can be a cat, then you are an animal.",
        "If you are a cat, then you can be an animal.",
        "If you are a cat, then you protect animals.",
        "If you are two cats, then you are an animal.",
        "If you are a cat, then you are two animals.",
        "If you are friendly, then you are calm.",
    ],
)
def test_adjacent_and_larger_constructions_stay_unread(sentence, logic_reg):
    assert _facts(sentence, logic_reg) == []
