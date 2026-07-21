"""Phase B reader 26: plural-agreeing ``All CLSs have P`` universals."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Atom, Quantified


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/universal-all-have"


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


def _derived_atoms(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return {
        (fact.entity, fact.pred, fact.polarity)
        for fact in result.store.by_kind(Atom)
        if fact.provenance.source == "synth/universal-instantiation"
    }


def test_all_have_emits_exact_plural_agreeing_universal(logic_reg):
    facts = _facts("All blickets have amber crests.", logic_reg)

    assert [(fact.cls, fact.pred, fact.polarity) for fact in facts] == [
        ("blicket", "have amber crests", True),
    ]


def test_named_member_instantiates_possessive_consequence(logic_reg):
    assert ("rex", "have amber crests", True) in _derived_atoms(
        "All blickets have amber crests. Rex is a blicket. "
        "Is it true that Rex is cheerful?",
        logic_reg,
    )


def test_missing_membership_does_not_instantiate(logic_reg):
    assert ("rex", "have amber crests", True) not in _derived_atoms(
        "All blickets have amber crests. Rex is a dax. "
        "Is it true that Rex is cheerful?",
        logic_reg,
    )


@pytest.mark.parametrize(
    "sentence",
    [
        "Every blicket has amber crests.",
        "Some blickets have amber crests.",
        "All blickets do not have amber crests.",
        "All blickets will have amber crests.",
        "All blickets have amber crests and blue horns.",
        "All blickets have either amber crests or blue horns.",
        "All blickets have several amber crests.",
        "All blickets have 2 apples.",
        "All blickets that sing have amber crests.",
        "All blickets who sing have amber crests.",
        "All blickets have eaten seeds.",
        "All blickets and daxes have amber crests.",
    ],
)
def test_adjacent_constructions_stay_unread(sentence, logic_reg):
    assert _facts(sentence, logic_reg) == []
