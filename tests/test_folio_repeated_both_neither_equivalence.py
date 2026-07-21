"""Phase B reader 21: fully repeated both-or-neither equivalence."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Equivalence


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/equivalence-ground-both-or-neither-repeated"


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
        for fact in result.store.by_kind(Equivalence)
        if fact.provenance.source == SOURCE
    ]


def _verdict(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return result.answer.value if result.answer.kind == "verdict" else result.answer.kind


def test_exact_repeated_form_emits_equivalence(logic_reg):
    facts = _facts(
        "Mira is either both a singer and a dancer or neither a singer nor a dancer.",
        logic_reg,
    )

    assert [(fact.entity, fact.left, fact.right) for fact in facts] == [
        ("mira", "singer", "dancer"),
    ]


def test_positive_evidence_propagates_across_equivalence(logic_reg):
    assert _verdict(
        "Mira is either both a singer and a dancer or neither a singer nor a dancer. "
        "Mira is a singer. Is it true that Mira is a dancer?",
        logic_reg,
    ) == "yes"


def test_negative_evidence_propagates_across_equivalence(logic_reg):
    assert _verdict(
        "Mira is either both a singer and a dancer or neither a singer nor a dancer. "
        "Mira is not a singer. Is it true that Mira is not a dancer?",
        logic_reg,
    ) == "yes"


def test_equivalence_composes_with_reductio(logic_reg):
    assert _verdict(
        "No artists are doctors. All singers are artists. All dancers are doctors. "
        "Mira is either both a singer and a dancer or neither a singer nor a dancer. "
        "Is it true that Mira is not a singer?",
        logic_reg,
    ) == "yes"


@pytest.mark.parametrize(
    "sentence",
    [
        "Mira is either a singer or a dancer.",
        "Mira is both a singer and a dancer.",
        "Mira is either both a singer and a dancer or neither a painter nor a dancer.",
        "Mira is either both a singer and a dancer or neither a dancer nor a singer.",
        "Mira is either both not a singer and a dancer or neither a singer nor a dancer.",
        "Mira is either both a singer and a dancer or neither a singer nor a dancer or an artist.",
        "A person is either both a singer and a dancer or neither a singer nor a dancer.",
    ],
)
def test_adjacent_and_larger_constructions_stay_unread(sentence, logic_reg):
    assert _facts(sentence, logic_reg) == []
