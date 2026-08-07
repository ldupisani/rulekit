"""Phase B reader 27: free-relative verbal conditional consequences."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Quantified


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/conditional-indefinite-verbal-comma-they-verbal-free-relative"


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


def test_free_relative_consequence_preserves_its_embedded_words(logic_reg):
    facts = _facts(
        "If a person pays taxes, they eat what people call cheese.", logic_reg
    )

    assert [(fact.cls, fact.pred, fact.polarity) for fact in facts] == [
        ("pay tax", "eat what person call cheese", True),
    ]


def test_free_relative_consequence_composes_with_ground_event(logic_reg):
    assert _verdict(
        "If a person pays taxes, they eat what people call cheese. "
        "Rex pays taxes. Is it true that Rex eats what people call cheese?",
        logic_reg,
    ) == "yes"


def test_missing_antecedent_does_not_instantiate(logic_reg):
    assert _verdict(
        "If a person pays taxes, they eat what people call cheese. "
        "Rex earns money. Is it true that Rex eats what people call cheese?",
        logic_reg,
    ) == "undetermined"


@pytest.mark.parametrize(
    "sentence",
    [
        "If people pay taxes, they eat what people call cheese.",
        "If a person does not pay taxes, they eat what people call cheese.",
        "If a person can pay taxes, they eat what people call cheese.",
        "If a person pays taxes and votes, they eat what people call cheese.",
        "If a person gets up early, they eat what people call cheese.",
        "If a person pays 2 dollars, they eat what people call cheese.",
        "If a person pays taxes, then they eat what people call cheese.",
        "If a person pays taxes, they are what people call wealthy.",
        "If a person pays taxes, they do not eat what people call cheese.",
        "If a person pays taxes, they can eat what people call cheese.",
        "If a person pays taxes, they eat cheese.",
        "If a person pays taxes, they eat what people and chefs call cheese.",
        "If a person pays taxes, they eat what people do call cheese.",
        "If a person pays taxes, they eat what people call cheese and bread.",
        "If a person pays taxes, they eat what 2 people call cheese.",
        "If a person pays taxes, they eat what people call 2 dollars.",
    ],
)
def test_adjacent_constructions_stay_unread(sentence, logic_reg):
    assert _facts(sentence, logic_reg) == []
