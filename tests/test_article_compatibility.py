"""Phase 0 of composition-design.md: the definite/indefinite matrix.

Articles are skippable senses and drop out of every phrase key, so 'plays
for a football club' and 'plays for THE football club' share the key
'play for football club' — and the indefinite premise confidently answered
the definite question (measured live before this fix). The matrix:

    premise vs question| indefinite ('a')   | definite description ('the'+noun)
    -------------------+--------------------+----------------------------------
    indefinite ('a')   | yes (echo)         | REFUSED -> undetermined  <- the fix
    definite ('the')   | yes (∃-intro)      | yes (echo; in-story coreference)

A definite-surfaced NAME ('the Emmet Building') is NOT a description — the
article is part of the name's surface — and must keep answering.

Mechanism: Atom.indef_obj (set at emission when the pred span swallowed an
'a'/'an'; inherited by decomposition variants via dataclasses.replace) +
patterns.field_definite_common (the ask FIELD's span swallowed a 'the'
whose next nominal past adjectives is a COMMON noun). Guarded in
logic-verdict, existential-verdict's witness, universal-verdict's
counterexample.
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
            ROOT / "packs/logic",
        ])
    )


def _verdict(text, reg):
    r = engine.solve(text, reg, tracing=False)
    return r.answer.value if r.answer.kind == "verdict" else r.answer.kind


# ---- the matrix, verbal ------------------------------------------------------

def test_indef_premise_refuses_definite_question(logic_reg):
    got = _verdict(
        "Rex plays for a football club. "
        "Is it true that Rex plays for the football club?", logic_reg
    )
    assert got in ("undetermined", "decline")


def test_def_premise_answers_definite_question(logic_reg):
    assert _verdict(
        "Rex plays for the football club. "
        "Is it true that Rex plays for the football club?", logic_reg
    ) == "yes"


def test_def_premise_answers_indefinite_question(logic_reg):
    # ∃-intro from a definite witness — the sound direction stays
    assert _verdict(
        "Rex plays for the football club. "
        "Is it true that Rex plays for a football club?", logic_reg
    ) == "yes"


def test_indef_premise_answers_indefinite_question(logic_reg):
    assert _verdict(
        "Rex plays for a football club. "
        "Is it true that Rex plays for a football club?", logic_reg
    ) == "yes"


# ---- the matrix, copular -----------------------------------------------------

def test_copular_indef_premise_refuses_definite_question(logic_reg):
    got = _verdict(
        "Rex is a dog. Is it true that Rex is the dog?", logic_reg
    )
    assert got in ("undetermined", "decline")


# ---- a definite-surfaced NAME is not a description ---------------------------

def test_definite_name_question_still_answers(logic_reg):
    assert _verdict(
        "John works at the Emmet Building. "
        "Is it true that John works at the Emmet Building?", logic_reg
    ) == "yes"


def test_definite_adjective_noun_is_still_a_description(logic_reg):
    # 'the' + adjective + common noun: the successor scan passes the
    # adjective and lands on the noun — still a description, still refused
    got = _verdict(
        "Rex plays for a big club. "
        "Is it true that Rex plays for the big club?", logic_reg
    )
    assert got in ("undetermined", "decline")


# ---- the flag inherits into decomposition variants ---------------------------

def test_decomposed_variant_inherits_the_indefinite_bit(logic_reg):
    # premise 'a dog who barks' decomposes to 'dog' (Stage 2.1); the variant
    # must carry indef_obj so 'the dog?' still refuses
    got = _verdict(
        "Rex is a dog who barks. Is it true that Rex is the dog?", logic_reg
    )
    assert got in ("undetermined", "decline")
