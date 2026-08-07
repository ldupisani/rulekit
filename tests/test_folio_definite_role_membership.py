"""Phase B reader 35: ``The ROLE of OWNER is/was MEMBER``."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Atom


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "logic/ground-definite-role-of-owner-is-name",
    "logic/ground-definite-role-of-owner-was-name",
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
        for fact in result.store.by_kind(Atom)
        if fact.provenance.source in SOURCES
    ]


def _verdict(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return result.answer.value if result.answer.kind == "verdict" else result.answer.kind


@pytest.mark.parametrize("copula", ["is", "was"])
def test_emits_exact_owner_qualified_role(copula, logic_reg):
    facts = _facts(f"The captain of Atlantis {copula} Rex.", logic_reg)

    assert [(fact.entity, fact.pred, fact.polarity) for fact in facts] == [
        ("rex", "captain of atlantis", True),
    ]


def test_exact_role_membership_joins_existing_copular_ask(logic_reg):
    assert _verdict(
        "The captain of Atlantis was Rex. "
        "Is it true that Rex is the captain of Atlantis?",
        logic_reg,
    ) == "yes"


def test_changed_owner_does_not_join(logic_reg):
    assert _verdict(
        "The captain of Atlantis was Rex. "
        "Is it true that Rex is the captain of Lemuria?",
        logic_reg,
    ) == "undetermined"


@pytest.mark.parametrize(
    "sentence",
    [
        "A captain of Atlantis was Rex.",
        "Captain of Atlantis was Rex.",
        "The captain Atlantis was Rex.",
        "The captain of Atlantis are Rex.",
        "The captain of Atlantis was not Rex.",
        "The captain of Atlantis was a sailor.",
        "The captain of Atlantis was he.",
        "The captain and pilot of Atlantis was Rex.",
        "The captain of Atlantis and Lemuria was Rex.",
        "The captain of Atlantis was Rex and Ann.",
        "The captain of Atlantis was Rex in Rome.",
        "The captain who sailed of Atlantis was Rex.",
        "The two captains of Atlantis were Rex.",
        "The captain of Atlantis could be Rex.",
        "The captain near Rome of Atlantis was Rex.",
        "The captain of Atlantis, Rex, was famous.",
    ],
)
def test_adjacent_constructions_stay_unread(sentence, logic_reg):
    assert _facts(sentence, logic_reg) == []
