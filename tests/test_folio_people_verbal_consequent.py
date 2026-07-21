"""Phase B reader 18: ``If people are P, then they V Q``."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Quantified


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/conditional-people-are-then-they-verbal"


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


def test_exact_form_emits_verbal_consequent(logic_reg):
    facts = _facts("If people are hungry, then they eat cheese.", logic_reg)

    assert [(fact.cls, fact.pred, fact.polarity) for fact in facts] == [
        ("hungry", "eat cheese", True),
    ]


def test_named_copular_fact_instantiates_verbal_consequent(logic_reg):
    assert _verdict(
        "If people are hungry, then they eat cheese. Rex is hungry. "
        "Is it true that Rex eats cheese?",
        logic_reg,
    ) == "yes"


def test_missing_antecedent_does_not_instantiate(logic_reg):
    assert _verdict(
        "If people are hungry, then they eat cheese. Rex is sleepy. "
        "Is it true that Rex eats cheese?",
        logic_reg,
    ) == "undetermined"


def test_coordinated_antecedent_remains_an_exact_key(logic_reg):
    facts = _facts(
        "If people are hungry and sleepy, then they eat cheese.", logic_reg
    )

    assert [(fact.cls, fact.pred, fact.polarity) for fact in facts] == [
        ("hungry and sleepy", "eat cheese", True),
    ]


@pytest.mark.parametrize(
    "sentence",
    [
        "If someone is hungry, then they eat cheese.",
        "If people in caves are hungry, then they eat cheese.",
        "If people are not hungry, then they eat cheese.",
        "If people are hungry, then they are sleepy.",
        "If people are hungry, then they do not eat cheese.",
        "If people are hungry, then they can eat cheese.",
        "If people are hungry, then they will eat cheese.",
        "If people are hungry, then they always eat cheese.",
        "If people are hungry, then they eat cheese and drink milk.",
        "If people are hungry, then they get up early.",
        "If people are hungry, then they eat 2 kg cheese.",
    ],
)
def test_adjacent_constructions_stay_unread(sentence, logic_reg):
    assert _facts(sentence, logic_reg) == []
