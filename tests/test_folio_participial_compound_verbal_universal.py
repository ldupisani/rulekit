"""Phase B reader 29: active-participial compound verbal universals."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Quantified


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/universal-participial-bare-plural-verbal"


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


def test_emits_exact_participial_class_and_verbal_predicate(logic_reg):
    facts = _facts("Growing plants produce seeds.", logic_reg)

    assert [(fact.cls, fact.pred, fact.polarity) for fact in facts] == [
        ("grow plant", "produce seed", True),
    ]


def test_named_participial_membership_instantiates_consequence(logic_reg):
    assert _verdict(
        "Growing plants produce seeds. Rex is a growing plant. "
        "Is it true that Rex produces seeds?",
        logic_reg,
    ) == "yes"


def test_missing_participial_membership_does_not_instantiate(logic_reg):
    assert _verdict(
        "Growing plants produce seeds. Rex is a garden plant. "
        "Is it true that Rex produces seeds?",
        logic_reg,
    ) == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "Plants produce seeds.",
        "Grow plants produce seeds.",
        "Green plants produce seeds.",
        "Growing plant produces seeds.",
        "The growing plants produce seeds.",
        "Not growing plants produce seeds.",
        "Growing and flowering plants produce seeds.",
        "Growing plants are green.",
        "Growing plants can produce seeds.",
        "Growing plants do not produce seeds.",
        "Growing plants produce seeds and fruit.",
        "Growing plants produce or release seeds.",
        "Growing plants have roots.",
        "Growing plants have produced seeds.",
        "Growing plants grow up quickly.",
        "Growing plants produce 2 seeds.",
        "Growing plants that flower produce seeds.",
    ],
)
def test_adjacent_constructions_stay_unread(surface, logic_reg):
    assert _facts(surface, logic_reg) == []
