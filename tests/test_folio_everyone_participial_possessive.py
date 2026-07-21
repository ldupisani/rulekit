"""Phase B reader 25: ``Everyone V-ing P has Q`` universals."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Atom, Quantified


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/universal-everyone-participial-has"


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


def test_participial_restrictor_emits_exact_possessive_universal(logic_reg):
    facts = _facts("Everyone working for Acme has a blue badge.", logic_reg)

    assert [(fact.cls, fact.pred, fact.polarity) for fact in facts] == [
        ("work for acme", "have blue badge", True),
    ]


def test_named_event_instantiates_possessive_consequence(logic_reg):
    assert ("rex", "have blue badge", True) in _derived_atoms(
        "Everyone working for Acme has a blue badge. Rex works for Acme. "
        "Is it true that Rex is cheerful?",
        logic_reg,
    )


def test_missing_restrictor_does_not_instantiate(logic_reg):
    assert ("rex", "have blue badge", True) not in _derived_atoms(
        "Everyone working for Acme has a blue badge. Rex works for Zenith. "
        "Is it true that Rex is cheerful?",
        logic_reg,
    )


@pytest.mark.parametrize(
    "sentence",
    [
        "Someone working for Acme has a blue badge.",
        "Everyone who works for Acme has a blue badge.",
        "Everyone works for Acme has a blue badge.",
        "Everyone sing songs has a blue badge.",
        "Everyone not working for Acme has a blue badge.",
        "Everyone working for Acme and Zenith has a blue badge.",
        "Everyone working for Acme does not have a blue badge.",
        "Everyone working for Acme will have a blue badge.",
        "Everyone working for Acme likes blue badges.",
        "Everyone working for 2 companies has a blue badge.",
        "Everyone carried by robots has a blue badge.",
        "Everyone getting up early has a blue badge.",
    ],
)
def test_adjacent_constructions_stay_unread(sentence, logic_reg):
    assert _facts(sentence, logic_reg) == []
