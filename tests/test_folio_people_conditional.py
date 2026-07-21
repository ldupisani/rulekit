"""Phase B reader 7: the someone-form's plural twin — ``If people are P,
then they are [not] Q`` reads as the degenerate universal ∀x P(x) → [¬]Q(x),
emitting the existing ``Quantified`` fact with `.singular`-folded keys (the
plural-agreeing discipline, Stage 8d/9a)."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Quantified


ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "logic/conditional-people-are-then-they-are",
    "logic/conditional-people-are-then-they-are-not",
)


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


def test_positive_form_emits_exact_quantified(logic_reg):
    facts = _facts("If people are happy, then they are dogs.", logic_reg)

    assert [
        (f.cls, f.pred, f.polarity) for f in facts
    ] == [("happy", "dog", True)]


def test_negative_form_emits_negative_quantified(logic_reg):
    facts = _facts("If people are happy, then they are not dogs.", logic_reg)

    assert [
        (f.cls, f.pred, f.polarity) for f in facts
    ] == [("happy", "dog", False)]


def test_passive_participial_antecedent_is_an_exact_key(logic_reg):
    facts = _facts(
        "If people are amazed by dogs, then they are happy.", logic_reg
    )

    assert [
        (f.cls, f.pred, f.polarity) for f in facts
    ] == [("amazed by dog", "happy", True)]


def test_named_witness_composition_instantiates(logic_reg):
    assert _verdict(
        "If people are happy, then they are dogs. Rex is happy. "
        "Is it true that Rex is a dog?",
        logic_reg,
    ) == "yes"


def test_named_witness_composition_requires_the_antecedent(logic_reg):
    assert _verdict(
        "If people are happy, then they are dogs. Rex is sad. "
        "Is it true that Rex is a dog?",
        logic_reg,
    ) == "undetermined"


def test_verbal_consequent_stays_unread(logic_reg):
    assert _facts(
        "If people are happy, then they eat mice.", logic_reg
    ) == []


def test_do_support_consequent_stays_unread(logic_reg):
    assert _facts(
        "If people are happy, then they do not eat mice.", logic_reg
    ) == []


def test_negated_antecedent_stays_unread(logic_reg):
    assert _facts(
        "If people are not happy, then they are dogs.", logic_reg
    ) == []


def test_singular_someone_form_is_not_this_reader(logic_reg):
    assert _facts("If someone is happy, then they are a dog.", logic_reg) == []
