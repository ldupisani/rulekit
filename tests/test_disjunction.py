"""Stage 3 (projects/scratch/ROADMAP.md): disjunction, case analysis,
exclusivity. The semantics are MEASURED from folio DEV golds, never assumed:
bare 'or' is INCLUSIVE, 'either...or' is EXCLUSIVE (the James minimal pair —
identical story and disjuncts, bare-or conclusion golds True while the
either-or conclusion golds False; plus the banked TikTok witness).

Every synth here is sound under BOTH readings except XOR-elimination, which
fires only on exclusive facts. All synthetic."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Disjunction

ROOT = Path(__file__).resolve().parents[1]


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


def _verdict(text, reg):
    r = engine.solve(text, reg, tracing=False)
    return r.answer.value if r.answer.kind == "verdict" else r.answer.kind


# ---- case analysis (sound under both readings) --------------------------------

def test_case_analysis(logic_reg):
    got = _verdict(
        "Rex is a dog or a cat. Every dog is an animal. Every cat is an animal. "
        "Is it true that Rex is an animal?", logic_reg)
    assert got == "yes"


def test_case_analysis_needs_both_branches(logic_reg):
    got = _verdict(
        "Rex is a dog or a cat. Every dog is an animal. "
        "Is it true that Rex is an animal?", logic_reg)
    assert got in ("undetermined", "decline")


def test_quantified_disjunction_instantiates_then_cases(logic_reg):
    # the full pipeline: qdisj -> ground disj -> case analysis
    got = _verdict(
        "Every pet is a dog or a cat. Rex is a pet. Every dog is an animal. "
        "Every cat is an animal. Is it true that Rex is an animal?", logic_reg)
    assert got == "yes"


# ---- disjunctive syllogism (sound under both readings) ------------------------

def test_disjunctive_syllogism(logic_reg):
    got = _verdict(
        "Rex is a dog or a cat. Rex is not a dog. "
        "Is it true that Rex is a cat?", logic_reg)
    assert got == "yes"


# ---- exclusivity: measured, not assumed ---------------------------------------

def test_xor_elimination_fires_on_either(logic_reg):
    got = _verdict(
        "Rex is either a dog or a cat. Rex is a dog. "
        "Is it true that Rex is a cat?", logic_reg)
    assert got == "no"


def test_bare_or_never_xor_eliminates(logic_reg):
    # THE inclusive/exclusive distinction: an inclusive disjunct's truth
    # says nothing about the other side
    got = _verdict(
        "Rex is a dog or a cat. Rex is a dog. "
        "Is it true that Rex is a cat?", logic_reg)
    assert got in ("undetermined", "decline")


# ---- disjunctive conclusions ---------------------------------------------------

def test_inclusive_conclusion_from_one_true_disjunct(logic_reg):
    got = _verdict(
        "Rex is a dog. Is it true that Rex is a dog or a cat?", logic_reg)
    assert got == "yes"


def test_exclusive_conclusion_no_when_both_true(logic_reg):
    # the James/TikTok gold shape: both disjuncts hold -> the either-form
    # conclusion is FALSE
    got = _verdict(
        "Rex is a dog. Rex is a cat. "
        "Is it true that Rex is either a dog or a cat?", logic_reg)
    assert got == "no"


def test_exclusive_conclusion_yes_when_exactly_one(logic_reg):
    got = _verdict(
        "Rex is a dog. Rex is not a cat. "
        "Is it true that Rex is either a dog or a cat?", logic_reg)
    assert got == "yes"


def test_exclusive_conclusion_undetermined_on_open_world(logic_reg):
    # one disjunct unknown: XOR cannot commit either way
    got = _verdict(
        "Rex is a dog. Is it true that Rex is either a dog or a cat?", logic_reg)
    assert got == "undetermined"


def test_disjunctive_question_routes_to_its_consumer(logic_reg):
    # the ask ties ask/logic-embedded-copular on ranking; id order is the
    # documented final tie-break and 'logic-disj...' sorts first — if this
    # ever breaks, the inclusive conclusion above regresses to undetermined
    r = engine.solve("Rex is a dog. Is it true that Rex is a dog or a cat?",
                     logic_reg, tracing=False)
    assert "or" in r.answer.reason or "disj" in r.answer.reason


def test_echo_answers_the_matching_surface(logic_reg):
    assert _verdict(
        "Rex is either a dog or a cat. "
        "Is it true that Rex is either a dog or a cat?", logic_reg) == "yes"


# ---- fail-closed surfaces ------------------------------------------------------

def test_negated_disjunction_stays_unread(logic_reg):
    r = engine.solve("Rex is not a dog or a cat.", logic_reg, tracing=False)
    assert not list(r.store.by_kind(Disjunction))


def test_null_control_unmentioned_subject(logic_reg):
    got = _verdict(
        "Rex is a dog or a cat. Every dog is an animal. Every cat is an animal. "
        "Is it true that Ann is an animal?", logic_reg)
    assert got in ("undetermined", "decline")
