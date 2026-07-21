"""Phase B reader 28: ``A/An CLS is a/an L or a/an R``."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import QuantifiedDisjunction


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/qdisj-indefinite-copular-bare"


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


def test_emits_exact_inclusive_fact_with_plain_singular_keys(logic_reg):
    facts = _facts("A trout is a swimmer or a flyer.", logic_reg)

    assert [
        (fact.cls, fact.left, fact.right, fact.exclusive) for fact in facts
    ] == [("trout", "swimmer", "flyer", False)]


def test_instantiation_and_case_analysis_compose(logic_reg):
    assert _verdict(
        "A pet is a dog or a cat. Rex is a pet. "
        "Every dog is an animal. Every cat is an animal. "
        "Is it true that Rex is an animal?",
        logic_reg,
    ) == "yes"


def test_inclusive_surface_does_not_eliminate_a_known_other_branch(logic_reg):
    assert _verdict(
        "A pet is a dog or a cat. Rex is a pet. Rex is a dog. "
        "Is it true that Rex is not a cat?",
        logic_reg,
    ) == "undetermined"


def test_composition_requires_class_membership(logic_reg):
    assert _verdict(
        "A pet is a dog or a cat. Rex is a friend. "
        "Every dog is an animal. Every cat is an animal. "
        "Is it true that Rex is an animal?",
        logic_reg,
    ) == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "A trout is either a swimmer or a flyer.",
        "A trout is swimmer or a flyer.",
        "A trout is a swimmer or flyer.",
        "Every trout is a swimmer or a flyer.",
        "The trout is a swimmer or a flyer.",
        "Trout are swimmers or flyers.",
        "A trout and a salmon is a swimmer or a flyer.",
        "A trout is not a swimmer or a flyer.",
        "A trout is a swimmer or not a flyer.",
        "A trout is a swimmer and a pet or a flyer.",
        "A trout is a swimmer or a flyer and a pet.",
        "A trout is from a river or a flyer.",
        "A trout is a swimmer or from a lake.",
        "A trout is a swimmer or flies quickly.",
        "A trout is a swimmer or a flyer or a pet.",
        "A trout was a swimmer or a flyer.",
    ],
)
def test_larger_or_distinct_constructions_stay_unread(logic_reg, surface):
    assert _facts(surface, logic_reg) == []
