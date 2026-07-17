"""The FOLIO Phase 1 increment's contracts (all synthetic — never a corpus
string): verdict commitment, the phrase-keyed logic pipeline, the fragment
guard, and the null controls that tell a capability from a guess.

Loads the folio pack list explicitly — packs/logic is folio-only by design
(pack scoping IS the cross-corpus containment), so the default test registry
must not see it."""
from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.answer import Answer

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


# ---- commitment semantics ---------------------------------------------------

def test_committed_admits_yes_no_never_undetermined():
    assert Answer("verdict", "yes", "").committed
    assert Answer("verdict", "no", "").committed
    assert not Answer("verdict", "undetermined", "").committed
    assert not Answer("decline", None, "").committed


# ---- the ground polarity matrix ----------------------------------------------

def test_ground_polarity_matrix(logic_reg):
    assert _verdict("Rex is a dog. Is it true that Rex is a dog?", logic_reg) == "yes"
    assert _verdict("Rex is not a dog. Is it true that Rex is a dog?", logic_reg) == "no"
    assert _verdict("Rex is a dog. Is it true that Rex is not a dog?", logic_reg) == "no"
    assert _verdict("Rex is not a dog. Is it true that Rex is not a dog?", logic_reg) == "yes"


# ---- null controls: an answer invariant to its question is not an answer -----

def test_null_control_unmentioned_subject(logic_reg):
    got = _verdict("Rex is a dog. Is it true that Ann is a dog?", logic_reg)
    assert got in ("undetermined", "decline")


def test_null_control_unmentioned_predicate(logic_reg):
    got = _verdict("Rex is a dog. Is it true that Rex is a cat?", logic_reg)
    assert got in ("undetermined", "decline")


# ---- the Fiedler trap: a qualified phrase never answers for another ----------

def test_qualified_phrase_never_loosens(logic_reg):
    got = _verdict(
        "Rex is a guard dog. Is it true that Rex is a police dog?", logic_reg
    )
    assert got in ("undetermined", "decline")


# ---- universals: instantiation and chaining -----------------------------------

def test_universal_instantiation(logic_reg):
    text = ("Every dog is an animal. Rex is a dog. "
            "Is it true that Rex is an animal?")
    assert _verdict(text, logic_reg) == "yes"


def test_universal_instantiation_negative(logic_reg):
    text = ("No dog is a cat. Rex is a dog. "
            "Is it true that Rex is a cat?")
    assert _verdict(text, logic_reg) == "no"


def test_universal_chain(logic_reg):
    text = ("Every dog is an animal. Every animal is an organism. Rex is a dog. "
            "Is it true that Rex is an organism?")
    # multi-hop via fixpoint saturation, exactly synth/transitive-before's shape
    assert _verdict(text, logic_reg) == "yes"


def test_negative_atom_licenses_nothing(logic_reg):
    # "Rex is NOT a dog" must not instantiate dog-properties onto Rex
    text = ("Every dog is an animal. Rex is not a dog. "
            "Is it true that Rex is an animal?")
    assert _verdict(text, logic_reg) in ("undetermined", "decline")


# ---- the fragment guard --------------------------------------------------------

def test_unconsumed_quantifier_vetoes_verdict(logic_reg):
    # 'some' has quantifier sense but NO logic rule reads it -> the story is
    # only partially supported and no verdict may commit, even though a ground
    # fact matches the question
    text = ("Rex is a dog. Some dogs are pets. "
            "Is it true that Rex is a dog?")
    r = engine.solve(text, logic_reg, tracing=False)
    assert not r.answer.committed
    assert "verdict-fragment" in r.answer.reason


def test_clause_split_vetoes_verdict(logic_reg):
    # the textual clause pre-split erases its boundary word (a promoted
    # DISJUNCT would read as an asserted fact) — any split story declines.
    # This sentence splits because both clauses carry their own subject,
    # finite verb and digit (engine._looks_like_new_clause).
    text = ("Rex is a dog. Ann has 3 cats, Ben has 4 cats. "
            "Is it true that Rex is a dog?")
    r = engine.solve(text, logic_reg, tracing=False)
    assert not r.answer.committed


# ---- full-read: the b1db917 lesson generalized to every value kind -------------

def test_trailing_restriction_is_part_of_the_phrase(logic_reg):
    # "at the pound" rides INSIDE the pred span, so the query phrase is
    # "dog at the pound" — it must not match the bare 'dog' atom (sound:
    # exact-phrase mismatch declines; it must never answer 'yes')
    got = _verdict(
        "Rex is a dog. Is it true that Rex is a dog at the pound?", logic_reg
    )
    assert got in ("undetermined", "decline")


# ---- the TEST-look-#1 narrowing is pinned (copular-only) ------------------------

def test_verbal_shapes_stay_unread(logic_reg):
    # the first landing's verbal universals / ground-verbal / verbal asks were
    # DROPPED after folio TEST look #1 (0 correct / 1 WRONG) — see the rules
    # file header. A verbal premise+conclusion must therefore produce NO
    # commitment; each dropped family returns only as its own increment with
    # its own TEST look.
    r = engine.solve("Rex owns a bone. Is it true that Rex owns a bone?",
                     logic_reg, tracing=False)
    assert not r.answer.committed


def test_all_are_not_stays_unread(logic_reg):
    # "All X are not Y" is scope-ambiguous (∀¬ vs ¬∀, decided per item by the
    # annotator) and was dropped in the narrowing; it must not produce facts
    r = engine.solve(
        "All dogs are not cats. Rex is a dog. Is it true that Rex is a cat?",
        logic_reg, tracing=False)
    assert not r.answer.committed


# ---- pack scoping: the default registry has no verdict producers ----------------

def test_default_registry_cannot_verdict(registry):
    # `registry` is the standard test fixture (no packs/logic): the embedded
    # wrapper must fall through to a plain decline — no ask, no verdict
    r = engine.solve("Rex is a dog. Is it true that Rex is a dog?", registry,
                     tracing=False)
    assert r.answer.kind == "decline"


# ---- the four suite pins, moved here verbatim (curated suite.yaml note) ------

def test_suite_pin_member_yes(logic_reg):
    assert _verdict("Bob is a student. Is Bob a student?", logic_reg) == "yes"


def test_suite_pin_member_no(logic_reg):
    assert _verdict("Bob is not a student. Is Bob a student?", logic_reg) == "no"


def test_suite_pin_member_undetermined(logic_reg):
    got = _verdict("The rose wilted. Is Bob a student?", logic_reg)
    assert got == "undetermined"


def test_suite_pin_ambig_rose_noun(logic_reg):
    # sense arbitration: 'rose' the noun wilts; 'Rose' the name is asked about
    got = _verdict("The rose wilted. Is Rose a teacher?", logic_reg)
    assert got == "undetermined"


def test_is_membership_cannot_shadow_the_wrapper(logic_reg):
    # 'true' is an ADJECTIVE in packs/logic: ask/is-membership's coll slot
    # (type: noun) can never bind it, so the wrapper cannot parse as
    # "is <it> <a true>" (the Phase 0a shadow). The embedded ask must win.
    r = engine.solve("Rex is a dog. Is it true that Rex is a dog?", logic_reg,
                     tracing=False)
    assert "logic" in r.answer.reason  # answered by logic-verdict, not membership
