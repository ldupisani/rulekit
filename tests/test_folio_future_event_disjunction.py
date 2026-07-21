"""Phase B reader 14: ``CLSs will either V P or V2 Q``."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import QuantifiedDisjunction


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/qdisj-bare-plural-future-events-either"


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


def test_emits_exact_exclusive_event_keys(logic_reg):
    facts = _facts(
        "Students will either visit museums or read books.", logic_reg
    )

    assert [
        (fact.cls, fact.left, fact.right, fact.exclusive) for fact in facts
    ] == [("student", "visit museum", "read book", True)]


def test_negative_branch_composes_by_disjunctive_syllogism(logic_reg):
    assert _verdict(
        "Students will either visit museums or read books. Rex is a student. "
        "Rex does not visit museums. Is it true that Rex reads books?",
        logic_reg,
    ) == "yes"


def test_positive_branch_composes_by_exclusive_elimination(logic_reg):
    assert _verdict(
        "Students will either visit museums or read books. Rex is a student. "
        "Rex visits museums. Is it true that Rex reads books?",
        logic_reg,
    ) == "no"


def test_composition_requires_class_membership(logic_reg):
    assert _verdict(
        "Students will either visit museums or read books. Rex is a friend. "
        "Rex does not visit museums. Is it true that Rex reads books?",
        logic_reg,
    ) == "undetermined"


def test_disjunction_alone_asserts_neither_branch(logic_reg):
    assert _verdict(
        "Students will either visit museums or read books. Rex is a student. "
        "Is it true that Rex visits museums?",
        logic_reg,
    ) == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "Students can either visit museums or read books.",
        "Students do either visit museums or read books.",
        "Students will visit museums or read books.",
        "A student will either visit museums or read books.",
        "The students will either visit museums or read books.",
        "Rex will either visit museums or read books.",
        "Students will either not visit museums or read books.",
        "Students will either visit museums and galleries or read books.",
        "Students will either want to visit museums or read books.",
        "Students will either get up or read books.",
        "Students will either visit 3 museums or read books.",
        "Students will either visit museums or read books or play games.",
        "Students will either be happy or read books.",
    ],
)
def test_larger_or_distinct_constructions_stay_unread(logic_reg, surface):
    assert _facts(surface, logic_reg) == []
