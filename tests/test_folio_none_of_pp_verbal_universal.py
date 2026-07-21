"""Phase B reader 32: ``None of the CLSs PREP R V the P`` universals."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Quantified


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/universal-none-of-pp-verbal"


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


def test_emits_exact_negative_restricted_verbal_universal(logic_reg):
    facts = _facts("None of the dogs in London eat the mice.", logic_reg)

    assert [(fact.cls, fact.pred, fact.polarity) for fact in facts] == [
        ("dog in london", "eat mouse", False),
    ]


def test_exact_restricted_membership_instantiates_negative_event(logic_reg):
    assert _verdict(
        "None of the dogs in London eat the mice. Rex is a dog in London. "
        "Is it true that Rex eats the mice?",
        logic_reg,
    ) == "no"


def test_different_restriction_does_not_instantiate(logic_reg):
    assert _verdict(
        "None of the dogs in London eat the mice. Rex is a dog in Paris. "
        "Is it true that Rex eats the mice?",
        logic_reg,
    ) == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "Some of the dogs in London eat the mice.",
        "None the dogs in London eat the mice.",
        "None of dogs in London eat the mice.",
        "None of the dog in London eats the mice.",
        "None of the dogs eat the mice.",
        "None of the dogs in London and Paris eat the mice.",
        "None of the dogs in the parks in London eat the mice.",
        "None of the dogs who live in London eat the mice.",
        "None of the dogs in London do not eat the mice.",
        "None of the dogs in London can eat the mice.",
        "None of the dogs in London eat mice.",
        "None of the dogs in London eat a mouse.",
        "None of the dogs in London eat the 2 mice.",
        "None of the dogs in London eat the mice and rats.",
        "None of the dogs in London eat the mice in cages.",
        "None of the dogs in London have eaten the mice.",
    ],
)
def test_adjacent_constructions_stay_unread(surface, logic_reg):
    assert _facts(surface, logic_reg) == []
