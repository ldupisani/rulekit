"""Universal CONCLUSIONS: "Is it true that all/no CLS are PRED?" (scratch pack).

The machinery (Quantified facts + synth/universal-chain saturation) predates
this; only the ask family and the `universal-verdict` consumer are new.
Semantics are FOL/open-world, the same contract as the other verdict
consumers:

  yes  <- a Quantified(cls, pred) fact at the CLAIMED polarity (echo or chain)
  no   <- a counterexample WITNESS: an entity in the class holding the pred
          at the opposite polarity of the claim
  else undetermined

NO EXISTENTIAL IMPORT in either direction: "No A are B" does not falsify
"All A are B" (both are vacuously true over an empty class in FOL, and FOLIO
golds are FOL-verified) — with a witness in A, saturation instantiates the
negative universal into the atom that IS the counterexample, so the witness
path is complete without the unsound shortcut.

"All A are NOT B" stays unread (span_blocks: negation): genuinely ambiguous
scope (∀¬ vs ¬∀), the v1 revert's lesson — one mis-scoped item is one wrong.
"""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine

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


# ---- yes: echo and chain ------------------------------------------------------

def test_universal_echo(logic_reg):
    assert _verdict(
        "All dogs are mammals. Is it true that all dogs are mammals?", logic_reg
    ) == "yes"


def test_universal_chain(logic_reg):
    assert _verdict(
        "All dogs are mammals. All mammals are animals. "
        "Is it true that all dogs are animals?", logic_reg
    ) == "yes"


def test_negative_universal_echo(logic_reg):
    assert _verdict(
        "No dogs are cats. Is it true that no dogs are cats?", logic_reg
    ) == "yes"


# ---- no: counterexample witnesses only ----------------------------------------

def test_universal_refuted_by_witness(logic_reg):
    # pred words must be LEXICON-KNOWN ('cat' folds 'cats'): an unknown
    # plural stays verbatim in the span, so 'barkers' would miss 'barker' —
    # the echo-exact morphology gap, a coverage limit, not this consumer's
    assert _verdict(
        "Rex is a dog. Rex is not a cat. "
        "Is it true that all dogs are cats?", logic_reg
    ) == "no"


def test_negative_universal_refuted_by_witness(logic_reg):
    assert _verdict(
        "Rex is a dog. Rex is a cat. "
        "Is it true that no dogs are cats?", logic_reg
    ) == "no"


def test_witness_via_instantiation(logic_reg):
    # the ∀¬ premise + a member: saturation mints the counterexample atom,
    # which refutes the POSITIVE universal soundly (nonempty class)
    assert _verdict(
        "No dogs are cats. Rex is a dog. "
        "Is it true that all dogs are cats?", logic_reg
    ) == "no"


# ---- undetermined: open world, no existential import --------------------------

def test_no_existential_import_positive(logic_reg):
    # no dog is known to exist: "No A are B" and "All A are B" are both
    # vacuously satisfiable — neither refutes the other
    assert _verdict(
        "No dogs are cats. Is it true that all dogs are cats?", logic_reg
    ) == "undetermined"


def test_no_existential_import_negative(logic_reg):
    assert _verdict(
        "All dogs are cats. Is it true that no dogs are cats?", logic_reg
    ) == "undetermined"


def test_null_control_unmentioned_class(logic_reg):
    got = _verdict(
        "All dogs are animals. Is it true that all cats are animals?", logic_reg
    )
    assert got in ("undetermined", "decline")


# ---- the FOLIO wrapper's capitalized quantifier (integration with senses fix) --

def test_wrapper_capitalized_quantifier_matches(logic_reg):
    assert _verdict(
        "All dogs are mammals. Is it true that All dogs are mammals?", logic_reg
    ) == "yes"
    assert _verdict(
        "No dogs are cats. Is it true that No dogs are cats?", logic_reg
    ) == "yes"


# ---- scope-ambiguous surfaces stay unread -------------------------------------

def test_all_are_not_stays_unread(logic_reg):
    got = _verdict(
        "All dogs are mammals. Is it true that all dogs are not mammals?",
        logic_reg,
    )
    assert got in ("undetermined", "decline")


# ---- Stage 8b: the verbal 'some' conclusion (existential witness) -------------

def test_some_verbal_conclusion_by_witness(logic_reg):
    assert _verdict(
        "Rex eats mice. Rex is a dog. "
        "Is it true that some dog eats mice?", logic_reg
    ) == "yes"


def test_some_verbal_null_control(logic_reg):
    got = _verdict(
        "Rex eats mice. Rex is a dog. "
        "Is it true that some mouse eats mice?", logic_reg
    )
    assert got in ("undetermined", "decline")


def test_some_verbal_wrapper_capitalized(logic_reg):
    # the FOLIO wrapper capitalizes 'Some'; the quantifier exemption
    # (senses.py) keeps it a quantifier and the lit matches its fold
    assert _verdict(
        "Rex eats mice. Rex is a dog. "
        "Is it true that Some dog eats mice?", logic_reg
    ) == "yes"


def test_do_support_negation_stays_unread(logic_reg):
    # "Some pets do not have fur": 'do' is not verb-sensed, so the verbal
    # 'some' ask cannot claim it — the do-support family is its own
    # increment, and half-reading it here would mint pred='do ...' keys
    got = _verdict(
        "Rex is a pet. Is it true that some pets do not have fur?", logic_reg
    )
    assert got in ("undetermined", "decline")
