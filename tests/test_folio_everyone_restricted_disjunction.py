"""Phase B reader 9: ``Everyone RESTRICTION is [either] L or R``."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import QuantifiedDisjunction


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "logic/qdisj-everyone-restricted-is-bare",
    "logic/qdisj-everyone-restricted-is-either",
}


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
        for fact in result.store.by_kind(QuantifiedDisjunction)
        if fact.provenance.source in SOURCES
    ]


def _verdict(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return result.answer.value if result.answer.kind == "verdict" else result.answer.kind


def test_bare_or_emits_exact_inclusive_fact(logic_reg):
    facts = _facts("Everyone at the party is happy or sad.", logic_reg)

    assert [
        (f.cls, f.left, f.right, f.exclusive) for f in facts
    ] == [("at party", "happy", "sad", False)]


def test_either_or_emits_exact_exclusive_fact(logic_reg):
    facts = _facts("Everyone at the party is either happy or sad.", logic_reg)

    assert [
        (f.cls, f.left, f.right, f.exclusive) for f in facts
    ] == [("at party", "happy", "sad", True)]


def test_instantiation_and_case_analysis_compose(logic_reg):
    assert _verdict(
        "Everyone at the party is a dog or a cat. Rex is at the party. "
        "Every dog is an animal. Every cat is an animal. "
        "Is it true that Rex is an animal?",
        logic_reg,
    ) == "yes"


def test_composition_requires_the_restriction(logic_reg):
    assert _verdict(
        "Everyone at the party is a dog or a cat. Rex is at the park. "
        "Every dog is an animal. Every cat is an animal. "
        "Is it true that Rex is an animal?",
        logic_reg,
    ) == "undetermined"


def test_disjunction_does_not_assert_either_branch(logic_reg):
    assert _verdict(
        "Everyone at the party is a dog or a cat. Rex is at the party. "
        "Is it true that Rex is a dog?",
        logic_reg,
    ) == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "Everyone is happy or sad.",
        "Everyone who is invited is happy or sad.",
        "Everyone at the party is not happy or sad.",
        "Everyone at the party is happy or not sad.",
        "Everyone at the party is happy or sad or calm.",
        "Everyone at the party sings or dances.",
    ],
)
def test_larger_or_distinct_constructions_stay_unread(logic_reg, surface):
    assert _facts(surface, logic_reg) == []
