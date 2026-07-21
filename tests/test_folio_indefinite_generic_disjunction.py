"""Phase B reader 10: ``A/An CLS is either a/an L or a/an R``."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import QuantifiedDisjunction


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/qdisj-indefinite-copular-either"


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
        for fact in result.store.by_kind(QuantifiedDisjunction)
        if fact.provenance.source == SOURCE
    ]


def _verdict(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return result.answer.value if result.answer.kind == "verdict" else result.answer.kind


def test_emits_exact_exclusive_fact_with_plain_singular_keys(logic_reg):
    facts = _facts("A trout is either a swimmer or a flyer.", logic_reg)

    assert [
        (fact.cls, fact.left, fact.right, fact.exclusive) for fact in facts
    ] == [("trout", "swimmer", "flyer", True)]


def test_instantiation_and_case_analysis_compose(logic_reg):
    assert _verdict(
        "A pet is either a dog or a cat. Rex is a pet. "
        "Every dog is an animal. Every cat is an animal. "
        "Is it true that Rex is an animal?",
        logic_reg,
    ) == "yes"


def test_exclusivity_composes_with_a_known_branch(logic_reg):
    assert _verdict(
        "A pet is either a dog or a cat. Rex is a pet. Rex is a dog. "
        "Is it true that Rex is not a cat?",
        logic_reg,
    ) == "yes"


def test_composition_requires_class_membership(logic_reg):
    assert _verdict(
        "A pet is either a dog or a cat. Rex is a friend. Rex is a dog. "
        "Is it true that Rex is not a cat?",
        logic_reg,
    ) == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "A trout is a swimmer or a flyer.",
        "A trout is either swimmer or flyer.",
        "Every trout is either a swimmer or a flyer.",
        "The trout is either a swimmer or a flyer.",
        "A trout and a salmon is either a swimmer or a flyer.",
        "A trout is either not a swimmer or a flyer.",
        "A trout is either a swimmer or not a flyer.",
        "A trout is either from a river or from a lake.",
        "A trout is either a swimmer or flies quickly.",
        "A trout is either a swimmer or a flyer or a pet.",
    ],
)
def test_larger_or_distinct_constructions_stay_unread(logic_reg, surface):
    assert _facts(surface, logic_reg) == []
