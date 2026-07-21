"""Phase B reader 4: single-antecedent verbal ``Everyone who`` rules."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Quantified


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/universal-everyone-who-verbal"


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


def test_everyone_relative_verbal_emits_exact_universal(logic_reg):
    facts = _facts("Everyone who eats mice likes cheese.", logic_reg)

    assert [(fact.cls, fact.pred, fact.polarity) for fact in facts] == [
        ("eat mouse", "like cheese", True),
    ]


def test_someone_minimal_pair_emits_nothing(logic_reg):
    assert _facts("Someone who eats mice likes cheese.", logic_reg) == []


def test_everyone_relative_verbal_composes_with_named_witness(logic_reg):
    assert _verdict(
        "Everyone who eats mice likes cheese. Rex eats mice. "
        "Is it true that Rex likes cheese?",
        logic_reg,
    ) == "yes"


def test_negated_consequent_stays_unread(logic_reg):
    assert _facts("Everyone who eats mice does not like cheese.", logic_reg) == []


def test_modal_consequent_stays_unread(logic_reg):
    assert _facts("Everyone who eats mice will like cheese.", logic_reg) == []


def test_particle_verb_refuses_a_lossy_base_lemma_key(logic_reg):
    assert _facts("Everyone who gets up early catches sunrise.", logic_reg) == []


def test_coordinated_antecedent_refuses_partial_read(logic_reg):
    assert _facts(
        "Everyone who eats mice and hunts rats likes cheese.", logic_reg
    ) == []
