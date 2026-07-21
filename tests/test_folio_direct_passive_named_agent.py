"""Phase B reader 31: ``The PATIENT is V-ed by NAME`` premises."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import VerbalRelation


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "logic/passive-dobj-definite-patient-named-agent"


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
        for fact in result.store.by_kind(VerbalRelation)
        if fact.provenance.source == SOURCE
    ]


def _verdict(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return result.answer.value if result.answer.kind == "verdict" else result.answer.kind


def test_emits_exact_active_relation_with_reversed_surface_roles(logic_reg):
    facts = _facts("The Garden Shed is produced by Rex.", logic_reg)

    assert [
        (fact.entity, fact.verb, fact.obj, fact.prep, fact.polarity)
        for fact in facts
    ] == [("rex", "produce", "garden shed", "", True)]


def test_relation_composes_with_existing_passive_agent_bridge(logic_reg):
    assert _verdict(
        "The Garden Shed is produced by Rex. Rex is a British architect. "
        "Is it true that Garden Shed is produced by a British architect?",
        logic_reg,
    ) == "yes"


def test_different_patient_does_not_compose(logic_reg):
    assert _verdict(
        "The Garden Shed is produced by Rex. Rex is a British architect. "
        "Is it true that Market Hall is produced by a British architect?",
        logic_reg,
    ) == "undetermined"


def test_missing_agent_membership_does_not_compose(logic_reg):
    assert _verdict(
        "The Garden Shed is produced by Rex. "
        "Is it true that Garden Shed is produced by a British architect?",
        logic_reg,
    ) == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "Garden Shed is produced by Rex.",
        "A Garden Shed is produced by Rex.",
        "The Garden Shed was produced by Rex.",
        "The Garden Shed are produced by Rex.",
        "The Garden Shed is design by Rex.",
        "The Garden Shed is designs by Rex.",
        "The Garden Shed is not produced by Rex.",
        "The Garden Shed is being produced by Rex.",
        "The Garden Shed is either produced by Rex.",
        "The Garden Shed is produced for Rex.",
        "The Garden Shed is produced by a builder.",
        "The Garden Shed is produced by Rex and Ann.",
        "The Garden Shed is produced by Rex in London.",
        "The Garden Shed is produced and sold by Rex.",
        "The Garden and Market Shed is produced by Rex.",
        "The 2 Garden Sheds are produced by Rex.",
    ],
)
def test_adjacent_constructions_stay_unread(surface, logic_reg):
    assert _facts(surface, logic_reg) == []
