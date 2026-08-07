"""Phase B reader 20: ``People V P are Q`` reduced-relative universals."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Quantified


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/universal-people-reduced-relative-copular"


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
        for fact in result.store.by_kind(Quantified)
        if fact.provenance.source == SOURCE
    ]


def _verdict(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return result.answer.value if result.answer.kind == "verdict" else result.answer.kind


def test_exact_form_emits_restrictor_to_predicate_universal(logic_reg):
    facts = _facts("People born in London are Americans.", logic_reg)

    assert [(fact.cls, fact.pred, fact.polarity) for fact in facts] == [
        ("born in london", "american", True),
    ]


def test_named_restrictor_fact_instantiates_consequence(logic_reg):
    assert _verdict(
        "People born in London are Americans. Rex was born in London. "
        "Is it true that Rex is American?",
        logic_reg,
    ) == "yes"


def test_missing_restrictor_does_not_instantiate(logic_reg):
    assert _verdict(
        "People born in London are Americans. Rex is sleepy. "
        "Is it true that Rex is American?",
        logic_reg,
    ) == "undetermined"


def test_multiword_name_predicate_stays_exact(logic_reg):
    facts = _facts("People born in London are New Yorkers.", logic_reg)

    assert [(fact.cls, fact.pred, fact.polarity) for fact in facts] == [
        ("born in london", "new yorkers", True),
    ]


@pytest.mark.parametrize(
    "sentence",
    [
        "People not born in London are Americans.",
        "People born in London are not Americans.",
        "People born in London are Americans and Britons.",
        "People born in 2 cities are Americans.",
        "People who are born in London are Americans.",
        "People born in London eat cheese.",
        "The people born in London are Americans.",
    ],
)
def test_adjacent_and_larger_constructions_stay_unread(sentence, logic_reg):
    assert _facts(sentence, logic_reg) == []
