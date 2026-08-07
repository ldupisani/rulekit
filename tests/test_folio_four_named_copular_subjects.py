"""Phase B reader 36: four asyndetic named copular subjects."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Atom


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/ground-copular-four-asyndetic-subjects"


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


def test_four_names_emit_one_singularized_atom_each(logic_reg):
    facts = _facts("Rex, Ann, Bob, Kim are teachers in Rome.", logic_reg)

    assert [(fact.entity, fact.pred, fact.polarity) for fact in facts] == [
        ("rex", "teacher in rome", True),
        ("ann", "teacher in rome", True),
        ("bob", "teacher in rome", True),
        ("kim", "teacher in rome", True),
    ]


def test_each_named_atom_joins_the_existing_copular_ask(logic_reg):
    assert _verdict(
        "Rex, Ann, Bob, Kim are teachers in Rome. "
        "Is it true that Kim is a teacher in Rome?",
        logic_reg,
    ) == "yes"


def test_unlisted_name_does_not_join(logic_reg):
    assert _verdict(
        "Rex, Ann, Bob, Kim are teachers in Rome. "
        "Is it true that Tim is a teacher in Rome?",
        logic_reg,
    ) == "undetermined"


@pytest.mark.parametrize(
    "sentence",
    [
        "Rex, Ann, Bob are teachers.",
        "Rex, Ann, Bob, Kim, Tim are teachers.",
        "Rex, Ann, Bob and Kim are teachers.",
        "Rex, Ann, Bob, and Kim are teachers.",
        "Rex Ann, Bob, Kim are teachers.",
        "Rex, Ann Bob, Kim are teachers.",
        "Rex, Ann, Bob Kim are teachers.",
        "Rex, Ann, Bob, Kim is a teacher.",
        "Rex, Ann, Bob, Kim are a team.",
        "Rex, Ann, Bob, Kim are not teachers.",
        "Rex, Ann, Bob, Kim are either teachers or doctors.",
        "Three, Ann, Bob, Kim are teachers.",
        "Rex, three, Bob, Kim are teachers.",
        "Rex; Ann, Bob, Kim are teachers.",
        "Yesterday Rex, Ann, Bob, Kim are teachers.",
        "Rex, Ann, Bob, Kim, musicians, are teachers.",
    ],
)
def test_adjacent_constructions_stay_unread(sentence, logic_reg):
    assert _facts(sentence, logic_reg) == []
