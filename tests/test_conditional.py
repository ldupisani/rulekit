"""Stage 1 (projects/scratch/ROADMAP.md): copular if-then conditionals.

"If a X is P, then it/they is/are [not] Q" -> Conditional(cls, pred,
then_pred, polarity), instantiated over TWO positive atoms by
synth/conditional-instantiation. The someone-form is the 1-antecedent
degenerate case and emits `quantified` directly.

The contracts pinned here are the FAIL-CLOSED directions: negated
antecedents match nothing (whole sentence unread, monotone-safe), unread
variants ('unless') stay unread, negative atoms license nothing, and a
hypothetical antecedent still never asserts. All synthetic."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Atom, Conditional

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


# ---- modus ponens, both consequent polarities --------------------------------

def test_conditional_instantiation_positive(logic_reg):
    got = _verdict(
        "Rex is a dog. Rex is hungry. If a dog is hungry, then it is grumpy. "
        "Is it true that Rex is grumpy?", logic_reg)
    assert got == "yes"


def test_conditional_instantiation_negative_consequent(logic_reg):
    text = ("Rex is a dog. Rex is hungry. If a dog is hungry, then it is not calm. ")
    assert _verdict(text + "Is it true that Rex is calm?", logic_reg) == "no"
    assert _verdict(text + "Is it true that Rex is not calm?", logic_reg) == "yes"


def test_conditional_they_are_form(logic_reg):
    got = _verdict(
        "Rex is a dog. Rex is hungry. If a dog is hungry, then they are grumpy. "
        "Is it true that Rex is grumpy?", logic_reg)
    assert got == "yes"


def test_someone_form_is_a_universal(logic_reg):
    got = _verdict(
        "If someone is a runner, then they are healthy. Ann is a runner. "
        "Is it true that Ann is healthy?", logic_reg)
    assert got == "yes"


# ---- the antecedent is a CONJUNCTION: both conjuncts or nothing --------------

def test_missing_antecedent_conjunct_derives_nothing(logic_reg):
    got = _verdict(
        "Rex is a dog. If a dog is hungry, then it is grumpy. "
        "Is it true that Rex is grumpy?", logic_reg)
    assert got in ("undetermined", "decline")


def test_negative_atom_never_satisfies_the_antecedent(logic_reg):
    got = _verdict(
        "Rex is a dog. Rex is not hungry. If a dog is hungry, then it is grumpy. "
        "Is it true that Rex is grumpy?", logic_reg)
    assert got in ("undetermined", "decline")


# ---- fail-closed surfaces ----------------------------------------------------

def test_negated_antecedent_matches_nothing(logic_reg):
    # span_blocks: negation on the antecedent spans — the sentence stays
    # WHOLE-unread (monotone-safe); no Conditional fact may exist
    r = engine.solve(
        "If a dog is not hungry, then it is calm. Rex is a dog. "
        "Is it true that Rex is calm?", logic_reg, tracing=False)
    assert not list(r.store.by_kind(Conditional))
    assert r.answer.value != "yes"


def test_unless_variant_stays_unread(logic_reg):
    got = _verdict(
        "Unless a dog is hungry, it is calm. Rex is a dog. "
        "Is it true that Rex is calm?", logic_reg)
    assert got in ("undetermined", "decline")


def test_embedded_if_never_fires(logic_reg):
    # `at_start` on 'if': a trailing conditional clause is not the fronted
    # construction these rules read — nothing may be minted from it
    r = engine.solve(
        "Rex is grumpy if a dog is hungry. Rex is a dog. Rex is hungry. "
        "Is it true that Rex is grumpy?", logic_reg, tracing=False)
    assert not list(r.store.by_kind(Conditional))


def test_antecedent_is_hypothetical_never_asserted(logic_reg):
    # the conditional alone asserts neither its antecedent nor consequent
    text = "If a dog is hungry, then it is grumpy. "
    assert _verdict(text + "Is it true that Rex is grumpy?", logic_reg) in (
        "undetermined", "decline")
    assert _verdict(text + "Is it true that Rex is hungry?", logic_reg) in (
        "undetermined", "decline")


# ---- composition with intersective decomposition (Stage A feeds Stage 1) -----

@pytest.fixture(scope="module")
def intersective_logic_reg(tmp_path_factory):
    root = tmp_path_factory.mktemp("cond-intersective-pack")
    (root / "pack.yaml").write_text(
        "format: rulekit/pack@1\nname: cond-intersective-test\nversion: 0.0.1\n"
        "description: intersective members for the conditional stage\n"
    )
    (root / "categories").mkdir()
    (root / "categories" / "c.yaml").write_text(
        "format: rulekit/categories@1\n"
        "categories:\n"
        "    intersective_modifier: {parent: noun}\n"
        "members:\n"
        "    intersective_modifier: [czech]\n"
    )
    (root / "lexicon").mkdir()
    (root / "lexicon" / "l.yaml").write_text(
        "format: rulekit/lexicon@1\n"
        "entries:\n"
        "    czech: {senses: [noun]}\n"
        "    conductor: {senses: [noun], plural: conductors}\n"
        "    choral: {senses: [adjective]}\n"
    )
    return compile_registry(
        load_packs([
            ROOT / "packs/core-english",
            ROOT / "packs/arithmetic",
            root,
            ROOT / "projects/scratch/packs/logic",
        ])
    )


def test_decomposed_atoms_feed_the_antecedent(intersective_logic_reg):
    # atom(m,'czech') and atom(m,'choral conductor') both come from A's
    # decomposition of ONE premise — the conditional's two antecedent slots
    # bind them, proving the stages compose
    got = _verdict(
        "Miroslav was a Czech choral conductor. "
        "If a Czech is a choral conductor, then it is busy. "
        "Is it true that Miroslav is busy?", intersective_logic_reg)
    assert got == "yes"
