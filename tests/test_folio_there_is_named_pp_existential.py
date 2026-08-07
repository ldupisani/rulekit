"""Phase B reader 30: ``There is a/an CLS PREPOSITION NAME``."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Existential


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/existential-there-is-indefinite-named-pp"


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
        for fact in result.store.by_kind(Existential)
        if fact.provenance.source == SOURCE
    ]


def _verdict(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return result.answer.value if result.answer.kind == "verdict" else result.answer.kind


def test_emits_exact_existential_without_inventing_a_witness(logic_reg):
    facts = _facts("There is a dog in London.", logic_reg)

    assert [(fact.cls, fact.pred, fact.polarity) for fact in facts] == [
        ("dog", "in london", True),
    ]


def test_exact_some_query_echoes_named_pp_existential(logic_reg):
    assert _verdict(
        "There is a dog in London. Is it true that Some dogs are in London?",
        logic_reg,
    ) == "yes"


def test_different_named_object_does_not_echo(logic_reg):
    assert _verdict(
        "There is a dog in London. Is it true that Some dogs are in Paris?",
        logic_reg,
    ) == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "There is a dog.",
        "There are dogs in London.",
        "There was a dog in London.",
        "Here is a dog in London.",
        "There is the dog in London.",
        "There is some dog in London.",
        "There is no dog in London.",
        "There is Rex in London.",
        "There is a dog and cat in London.",
        "There is a dog in a city.",
        "There is a dog in 2 cities.",
        "There is a dog in London and Paris.",
        "There is a dog not in London.",
        "There is a dog in London that barks.",
        "There is a dog in London classified as a pet.",
        "There is a dog near the river.",
    ],
)
def test_adjacent_constructions_stay_unread(surface, logic_reg):
    assert _facts(surface, logic_reg) == []
