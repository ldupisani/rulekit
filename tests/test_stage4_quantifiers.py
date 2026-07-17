"""Stage 4 (projects/scratch/ROADMAP.md): quantifier morphology +
existentials. 'any' is an ARTICLE (auto-skipped) made matchable by the
opt-in `consume_skipped` lit flag; 'each' is a plain quantifier; 'everyone
who is P is Q' is a pronoun-quantified universal; 'some' premises emit
Existential facts and CONSUME the quantifier (relaxing the fragment veto by
capability). All synthetic."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Quantified

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


# ---- 'any' universals (the consume_skipped flag) ------------------------------

def test_any_universal_instantiates(logic_reg):
    got = _verdict(
        "Any dog is an animal. Rex is a dog. Is it true that Rex is an animal?",
        logic_reg)
    assert got == "yes"


def test_other_articles_never_match_the_any_rule(logic_reg):
    # 'The dog is friendly' is a SPECIFIC dog, not a universal — the
    # consume_skipped lit stops only at 'any', every other article is
    # skipped and the rule fails
    r = engine.solve("The dog is friendly.", logic_reg, tracing=False)
    assert not list(r.store.by_kind(Quantified))
    r = engine.solve("A dog is friendly.", logic_reg, tracing=False)
    assert not list(r.store.by_kind(Quantified))


# ---- 'each' and 'everyone who' universals -------------------------------------

def test_each_universal_instantiates(logic_reg):
    got = _verdict(
        "Each dog is an animal. Rex is a dog. Is it true that Rex is an animal?",
        logic_reg)
    assert got == "yes"


def test_everyone_who_universal(logic_reg):
    got = _verdict(
        "Everyone who is a runner is healthy. Ann is a runner. "
        "Is it true that Ann is healthy?", logic_reg)
    assert got == "yes"


def test_everyone_who_negative_consequent(logic_reg):
    got = _verdict(
        "Everyone who is a runner is not lazy. Ann is a runner. "
        "Is it true that Ann is lazy?", logic_reg)
    assert got == "no"


# ---- 'some': existential premises and conclusions -----------------------------

def test_some_premise_no_longer_vetoes(logic_reg):
    # the pre-Stage-4 fragment veto (test_unconsumed_quantifier_vetoes_verdict
    # pinned it for UNREAD 'some') relaxes by capability: the rule consumes
    # the quantifier, so an unrelated ground verdict may commit again
    got = _verdict(
        "Rex is a dog. Some dogs are pets. Is it true that Rex is a dog?",
        logic_reg)
    assert got == "yes"


def test_existential_echo(logic_reg):
    got = _verdict(
        "Some dogs are pets. Is it true that some dogs are pets?", logic_reg)
    assert got == "yes"


def test_existential_witness(logic_reg):
    # ∃-introduction at query time: one entity holding both atoms
    got = _verdict(
        "Rex is a dog. Rex is a pet. Is it true that some dogs are pets?",
        logic_reg)
    assert got == "yes"


def test_existential_negative_witness(logic_reg):
    got = _verdict(
        "Rex is a dog. Rex is not a pet. "
        "Is it true that some dogs are not pets?", logic_reg)
    assert got == "yes"


def test_negative_universal_refutes_existential(logic_reg):
    # ∀¬ soundly refutes ∃ — the ONLY route to 'no' on an open world
    got = _verdict(
        "No dog is a cat. Is it true that some dogs are cats?", logic_reg)
    assert got == "no"


def test_no_existential_import_from_positive_universal(logic_reg):
    # classical FOL: "all dogs are animals" proves no dog EXISTS
    got = _verdict(
        "Every dog is an animal. Is it true that some dogs are animals?",
        logic_reg)
    assert got == "undetermined"


def test_open_world_stays_undetermined(logic_reg):
    got = _verdict(
        "Rex is a dog. Is it true that some dogs are pets?", logic_reg)
    assert got == "undetermined"
