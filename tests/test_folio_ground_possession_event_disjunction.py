"""Phase B reader 16: ``NAME has P or V Q``."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Atom, Disjunction


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/disj-ground-has-or-verbal"


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
        for fact in result.store.by_kind(Disjunction)
        if fact.provenance.source == SOURCE
    ]


def _verdict(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return result.answer.value if result.answer.kind == "verdict" else result.answer.kind


def test_emits_exact_inclusive_mixed_branch_keys(logic_reg):
    facts = _facts("Rex has a car or works at Acme.", logic_reg)

    assert [
        (fact.entity, fact.left, fact.right, fact.exclusive) for fact in facts
    ] == [("rex", "have car", "work at acme", False)]


def test_negative_event_branch_derives_possession_branch(logic_reg):
    result = engine.solve(
        "Rex has a car or works at Acme. Rex does not work at Acme.",
        logic_reg,
        tracing=False,
    )

    assert any(
        fact.entity == "rex"
        and fact.pred == "have car"
        and fact.polarity is True
        for fact in result.store.by_kind(Atom)
    )


def test_negative_possession_branch_derives_event_branch(logic_reg):
    assert _verdict(
        "Rex has a car or works at Acme. No students have cars. "
        "Rex is a student. Is it true that Rex works at Acme?",
        logic_reg,
    ) == "yes"


def test_disjunction_alone_asserts_neither_branch(logic_reg):
    assert _verdict(
        "Rex has a car or works at Acme. Is it true that Rex works at Acme?",
        logic_reg,
    ) == "undetermined"


def test_inclusive_disjunction_does_not_eliminate_from_positive_branch(logic_reg):
    result = engine.solve(
        "Rex has a car or works at Acme. Rex works at Acme.",
        logic_reg,
        tracing=False,
    )

    assert not any(
        fact.entity == "rex"
        and fact.pred == "have car"
        and fact.polarity is False
        for fact in result.store.by_kind(Atom)
    )


@pytest.mark.parametrize(
    "surface",
    [
        "Rex is a driver or works at Acme.",
        "Rex has a car and works at Acme.",
        "Rex either has a car or works at Acme.",
        "Rex has either a car or works at Acme.",
        "Rex has no car or works at Acme.",
        "Rex has a car or does not work at Acme.",
        "Rex has a car or can work at Acme.",
        "Rex has a car or wants to work at Acme.",
        "Rex has a car or gets up.",
        "Rex has a car and a bike or works at Acme.",
        "Rex has 3 cars or works at Acme.",
        "Rex has a car or works at Acme and Beta.",
        "Rex has a car or works at Acme or studies at Beta.",
        "A student has a car or works at Acme.",
    ],
)
def test_larger_or_distinct_constructions_stay_unread(logic_reg, surface):
    assert _facts(surface, logic_reg) == []
