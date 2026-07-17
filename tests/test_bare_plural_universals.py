"""Stage 8: bare-plural universal premises + the negative-chain synth.

"Mushrooms are fungi" is FOLIO-FOL's ∀ (a bare-plural copular generic);
57 dev-train premises carry the shape, 19 more the negated form. The
subject is ONE unit, definite/possessive/pronoun subjects are refused
(those are GROUND statements, not generics), and the -not variants are
unambiguous ∀¬ — a bare plural has no quantifier for negation to
out-scope, unlike the dropped "All X are not Y".

The negative-chain synth (M⊆F ∧ P∩F=∅ ⊢ P∩M=∅) is landed WITH its buyer:
its only measured use needs a bare-plural premise for the positive hop.
"""

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


def _quants(text, reg):
    r = engine.solve(text, reg, tracing=False)
    return {(f.cls, f.pred, f.polarity) for f in r.store.by_kind(Quantified)}


# ---- the two subject variants read --------------------------------------------

def test_known_plural_noun_subject(logic_reg):
    assert _quants("Dogs are animals.", logic_reg) == {("dog", "animal", True)}


def test_unknown_capitalized_subject(logic_reg):
    # 'Wugs' is in no lexicon: sentence-initial capital annotates it a NAME,
    # and the proper_name variant reads it (lemma = fold, stays verbatim)
    assert _quants("Wugs are animals.", logic_reg) == {("wugs", "animal", True)}


def test_negated_variants_read_as_negative_universal(logic_reg):
    assert _quants("Dogs are not cats.", logic_reg) == {("dog", "cat", False)}
    assert _quants("Wugs are not cats.", logic_reg) == {("wugs", "cat", False)}


# ---- definite / possessive / pronoun subjects are GROUND, never generic -------

def test_definite_subject_refused(logic_reg):
    assert _quants("The dogs are animals.", logic_reg) == set()


def test_possessive_subject_refused(logic_reg):
    assert _quants("Bob's dogs are friendly dogs.", logic_reg) == set()


def test_counted_subject_refused(logic_reg):
    # merge-count folds 'Three dogs' into ONE plural noun unit — but "Three
    # dogs are pets" is about three particular dogs, not dogkind; the
    # bare_plural type refuses a count-valued unit (this hole passed the
    # first test round and was caught by an adversarial probe)
    assert _quants("Three dogs are pets.", logic_reg) == set()


def test_resolved_pronoun_subject_refused(logic_reg):
    # 'They' resolves to Rex-and-friends territory; a pronoun subject is
    # definite reference and must never mint a universal
    got = _quants("Rex owns dogs. They are animals.", logic_reg)
    assert got == set()


# ---- composition with the existing machinery ----------------------------------

def test_bare_plural_answers_the_universal_conclusion(logic_reg):
    assert _verdict(
        "Dogs are animals. Is it true that all dogs are animals?", logic_reg
    ) == "yes"


def test_bare_plural_feeds_instantiation(logic_reg):
    assert _verdict(
        "Dogs are animals. Rex is a dog. Is it true that Rex is an animal?",
        logic_reg,
    ) == "yes"


# ---- the negative-chain synth ---------------------------------------------------

def test_negative_chain_derives_the_disjointness(logic_reg):
    # M⊆F ('Wugs are animals'), P∩F=∅ ('No plants are animals')
    # ⊢ P∩M=∅ ('no plants are wugs')
    assert _verdict(
        "No plants are animals. Wugs are animals. "
        "Is it true that no plants are wugs?", logic_reg
    ) == "yes"


def test_negative_chain_null_control(logic_reg):
    got = _verdict(
        "No plants are animals. Wugs are animals. "
        "Is it true that no plants are zorbs?", logic_reg
    )
    assert got in ("undetermined", "decline")


def test_negative_chain_wrong_direction_stays_open(logic_reg):
    # the synth derives P∩M=∅, never M⊆P or its negation: "no wugs are
    # plants" is ALSO entailed (disjointness is symmetric) but the engine
    # does not yet emit the mirror — pin today's honest undetermined so a
    # future symmetry synth is a measured, deliberate change
    got = _verdict(
        "No plants are animals. Wugs are animals. "
        "Is it true that all wugs are plants?", logic_reg
    )
    assert got in ("undetermined", "decline")
