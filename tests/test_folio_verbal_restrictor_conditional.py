"""Phase B reader 5: verbal-restrictor ``If …, then it is …`` rules."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Conditional


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/conditional-verbal-then-it-is"


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
        for fact in result.store.by_kind(Conditional)
        if fact.provenance.source == SOURCE
    ]


def _verdict(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return result.answer.value if result.answer.kind == "verdict" else result.answer.kind


def test_verbal_restrictor_emits_exact_conditional(logic_reg):
    facts = _facts("If a dog eats mice, then it is happy.", logic_reg)

    assert [
        (fact.cls, fact.pred, fact.then_pred, fact.polarity) for fact in facts
    ] == [("dog", "eat mouse", "happy", True)]


def test_copular_antecedent_minimal_pair_uses_no_verbal_reader(logic_reg):
    assert _facts("If a dog is hungry, then it is happy.", logic_reg) == []


def test_verbal_restrictor_composes_with_named_witness(logic_reg):
    assert _verdict(
        "If a dog eats mice, then it is happy. Rex is a dog. Rex eats mice. "
        "Is it true that Rex is happy?",
        logic_reg,
    ) == "yes"


def test_negated_consequence_stays_unread(logic_reg):
    assert _facts("If a dog eats mice, then it is not happy.", logic_reg) == []


def test_coordinated_antecedent_refuses_partial_read(logic_reg):
    assert _facts(
        "If a dog eats mice and likes cheese, then it is happy.", logic_reg
    ) == []


def test_particle_antecedent_refuses_a_lossy_base_lemma_key(logic_reg):
    assert _facts("If a dog gives away mice, then it is happy.", logic_reg) == []


def test_modal_antecedent_stays_unread(logic_reg):
    assert _facts("If a dog can eat mice, then it is happy.", logic_reg) == []
