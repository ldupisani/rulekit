"""Phase B reader 19: ``If a/an CLS V P, [then] they V2 Q``."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Quantified


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "logic/conditional-indefinite-verbal-then-they-verbal-then",
    "logic/conditional-indefinite-verbal-comma-they-verbal",
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
        for fact in result.store.by_kind(Quantified)
        if fact.provenance.source in SOURCES
    ]


def _verdict(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return result.answer.value if result.answer.kind == "verdict" else result.answer.kind


def test_explicit_then_form_emits_two_event_keys(logic_reg):
    facts = _facts(
        "If a person pays taxes, then they contribute to the country.",
        logic_reg,
    )

    assert [(fact.cls, fact.pred, fact.polarity) for fact in facts] == [
        ("pay tax", "contribute to country", True),
    ]


def test_comma_only_form_emits_the_same_key_shape(logic_reg):
    facts = _facts(
        "If a person pays taxes, they contribute to the country.", logic_reg
    )

    assert [(fact.cls, fact.pred, fact.polarity) for fact in facts] == [
        ("pay tax", "contribute to country", True),
    ]


def test_named_ground_event_instantiates_consequent(logic_reg):
    assert _verdict(
        "If a person pays taxes, then they eat cheese. "
        "Rex pays taxes. Is it true that Rex eats cheese?",
        logic_reg,
    ) == "yes"


def test_missing_antecedent_does_not_instantiate(logic_reg):
    assert _verdict(
        "If a person pays taxes, then they eat cheese. "
        "Rex earns money. Is it true that Rex eats cheese?",
        logic_reg,
    ) == "undetermined"


@pytest.mark.parametrize(
    "sentence",
    [
        "If people pay taxes, then they contribute to the country.",
        "If someone pays taxes, then they contribute to the country.",
        "If a person does not pay taxes, then they contribute to the country.",
        "If a person can pay taxes, then they contribute to the country.",
        "If a person pays taxes, then they are wealthy.",
        "If a person pays taxes, then they do not contribute to the country.",
        "If a person pays taxes, then they will contribute to the country.",
        "If a person pays taxes, then they always contribute to the country.",
        "If a person pays taxes and votes, then they contribute to the country.",
        "If a person gets up early, then they contribute to the country.",
        "If a person pays 2 dollars, then they contribute to the country.",
    ],
)
def test_adjacent_constructions_stay_unread(sentence, logic_reg):
    assert _facts(sentence, logic_reg) == []
