"""Phase B reader 33: ``One of the CLSs of OWNER was MEMBER``."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Atom


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/ground-one-of-owned-class-was-name"


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
        for fact in result.store.by_kind(Atom)
        if fact.provenance.source == SOURCE
    ]


def _verdict(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return result.answer.value if result.answer.kind == "verdict" else result.answer.kind


def test_emits_exact_named_membership_in_owned_class(logic_reg):
    facts = _facts("One of the students of Plato was Rex.", logic_reg)

    assert [(fact.entity, fact.pred, fact.polarity) for fact in facts] == [
        ("rex", "student of plato", True),
    ]


def test_exact_membership_echoes_through_existing_copular_ask(logic_reg):
    assert _verdict(
        "One of the students of Plato was Rex. "
        "Is it true that Rex is a student of Plato?",
        logic_reg,
    ) == "yes"


def test_different_owner_does_not_echo(logic_reg):
    assert _verdict(
        "One of the students of Plato was Rex. "
        "Is it true that Rex is a student of Socrates?",
        logic_reg,
    ) == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "Two of the students of Plato was Rex.",
        "One the students of Plato was Rex.",
        "One of students of Plato was Rex.",
        "One of the students was Rex.",
        "One of the students near Athens of Plato was Rex.",
        "One of the students of Plato is Rex.",
        "One of the students of Plato was not Rex.",
        "One of the students of Plato was a scholar.",
        "One of the students of Plato was he.",
        "One of the students of Plato and Socrates was Rex.",
        "One of the students of Plato was Rex and Ann.",
        "One of the students of Plato was Rex in Athens.",
        "One of the students of Plato, Rex, was famous.",
        "One of the 2 students of Plato was Rex.",
        "One of the students of Plato could be Rex.",
        "One of the students who knew Plato was Rex.",
    ],
)
def test_adjacent_constructions_stay_unread(surface, logic_reg):
    assert _facts(surface, logic_reg) == []
