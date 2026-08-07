"""Phase B reader 11: ``No CLSs have P`` / ``No CLS has P``."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Atom, Quantified


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {"logic/universal-no-have", "logic/universal-no-has"}


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


def _source_facts(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return [
        fact
        for fact in result.store.by_kind(Quantified)
        if fact.provenance.source in SOURCES
    ]


def test_plural_agreement_emits_folded_class_and_canonical_have(logic_reg):
    facts = _source_facts("No reptiles have fur.", logic_reg)

    assert [
        (fact.cls, fact.pred, fact.polarity) for fact in facts
    ] == [("reptile", "have fur", False)]


def test_singular_agreement_emits_plain_class_and_canonical_have(logic_reg):
    facts = _source_facts("No reptile has fur.", logic_reg)

    assert [
        (fact.cls, fact.pred, fact.polarity) for fact in facts
    ] == [("reptile", "have fur", False)]


def test_negative_universal_chains_to_a_subclass(logic_reg):
    result = engine.solve(
        "No reptiles have fur. Snakes are reptiles.", logic_reg, tracing=False
    )

    assert any(
        fact.cls == "snake"
        and fact.pred == "have fur"
        and fact.polarity is False
        for fact in result.store.by_kind(Quantified)
    )


def test_negative_universal_instantiates_for_a_named_member(logic_reg):
    result = engine.solve(
        "No reptiles have fur. Rex is a reptile.", logic_reg, tracing=False
    )

    assert any(
        fact.entity == "rex"
        and fact.pred == "have fur"
        and fact.polarity is False
        for fact in result.store.by_kind(Atom)
    )


@pytest.mark.parametrize(
    "surface",
    [
        "All reptiles have fur.",
        "No reptile is furry.",
        "No reptiles do not have fur.",
        "No reptiles that Alice studies have fur.",
        "No reptiles and birds have fur.",
        "No reptiles have fur and scales.",
        "No reptiles have eaten fish.",
        "No reptiles can have fur.",
    ],
)
def test_larger_or_distinct_constructions_stay_unread(logic_reg, surface):
    assert _source_facts(surface, logic_reg) == []
