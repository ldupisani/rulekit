"""The FOLIO Phase 1 increment's contracts (all synthetic — never a corpus
string): verdict commitment, the phrase-keyed logic pipeline, the fragment
guard, and the null controls that tell a capability from a guess.

Loads the folio pack list explicitly — packs/logic lives in projects/scratch only
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
            ROOT / "projects/scratch/packs/logic",
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


def test_qualified_phrase_survives_KNOWN_vocabulary(logic_reg):
    # the Fiedler trap held only while modifiers were UNKNOWN words (unmerged,
    # verbatim in the span). With both modifiers in the lexicon, condense
    # merges each compound to ONE unit whose lemma is the bare head, and the
    # old bare-lemma phrase render collapsed both sides to 'tree' — answering
    # 'yes' to a DIFFERENT qualified phrase. _canonical_phrase now renders a
    # merged unit as its full qualified phrase. Admitting a word must never
    # loosen a phrase key.
    got = _verdict(
        "Rex is a coconut tree. Is it true that Rex is a mango tree?", logic_reg
    )
    assert got in ("undetermined", "decline")


def test_qualified_phrase_still_matches_itself_when_merged(logic_reg):
    got = _verdict(
        "Rex is a coconut tree. Is it true that Rex is a coconut tree?", logic_reg
    )
    assert got == "yes"


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


# ---- intersective decomposition of atoms (option A) ---------------------------
# Intersection-elimination at the predicate's top level, gated on the opt-in
# `intersective_modifier` category. ONE shared contract definition
# (patterns.intersective_split) serves both the copular fold and this layer.

@pytest.fixture(scope="module")
def intersective_logic_reg(tmp_path_factory):
    root = tmp_path_factory.mktemp("intersective-logic-pack")
    (root / "pack.yaml").write_text(
        "format: rulekit/pack@1\nname: intersective-logic-test\nversion: 0.0.1\n"
        "description: synthetic intersective members for the atom layer\n"
    )
    (root / "categories").mkdir()
    (root / "categories" / "c.yaml").write_text(
        "format: rulekit/categories@1\n"
        "categories:\n"
        "    intersective_modifier: {parent: noun}\n"
        "    nationality_noun: {parent: intersective_modifier}\n"
        "members:\n"
        "    nationality_noun: [czech]\n"
    )
    (root / "lexicon").mkdir()
    (root / "lexicon" / "l.yaml").write_text(
        "format: rulekit/lexicon@1\n"
        "entries:\n"
        "    czech: {senses: [noun]}\n"
        "    conductor: {senses: [noun], plural: conductors}\n"
        "    choral: {senses: [adjective]}\n"
        "    european: {senses: [noun], plural: europeans}\n"
    )
    return compile_registry(
        load_packs([
            ROOT / "packs/core-english",
            ROOT / "packs/arithmetic",
            root,
            ROOT / "projects/scratch/packs/logic",
        ])
    )


def test_atom_decomposes_only_the_gated_modifier(intersective_logic_reg):
    from rulekit.kernel.model import Atom

    r = engine.solve("Miroslav was a Czech choral conductor.",
                     intersective_logic_reg, tracing=False)
    preds = {f.pred for f in r.store.by_kind(Atom)}
    # full phrase + stripped-intersective variant + the modifier alone;
    # NEVER a bare head — 'choral' is ungated, so it pins the head qualified
    # (the 'former president' safety: head-entailment is not free here)
    assert preds == {"czech choral conductor", "choral conductor", "czech"}


def test_decomposition_composes_with_instantiation(intersective_logic_reg):
    got = _verdict(
        "Miroslav was a Czech choral conductor. Every Czech is a European. "
        "Is it true that Miroslav is a European?",
        intersective_logic_reg,
    )
    assert got == "yes"


def test_negative_atom_never_decomposes(intersective_logic_reg):
    from rulekit.kernel.model import Atom

    r = engine.solve("Miroslav was not a Czech choral conductor.",
                     intersective_logic_reg, tracing=False)
    facts = [(f.pred, f.polarity) for f in r.store.by_kind(Atom)]
    assert facts == [("czech choral conductor", False)]


def test_no_category_means_no_atom_decomposition(logic_reg):
    from rulekit.kernel.model import Atom

    r = engine.solve("Rex is a coconut tree.", logic_reg, tracing=False)
    assert {f.pred for f in r.store.by_kind(Atom)} == {"coconut tree"}


# ---- the fold's laxities still cannot reach a verdict (no-bridge pins) --------

def test_if_antecedent_cannot_reach_a_verdict(logic_reg):
    # `at_start` keeps the ground rules off the embedded antecedent, and no
    # bridge lifts fold facts into the atom layer — a hypothetical must
    # never answer as an assertion
    got = _verdict(
        "If Rex is a dog, then Rex is a barker. Is it true that Rex is a dog?",
        logic_reg,
    )
    assert got in ("undetermined", "decline")


def test_passive_junk_cannot_reach_a_verdict(logic_reg):
    # the fold's be+noun laxity on passives ("mints junk", Phase 0a) stays
    # quarantined below the verdict layer; the atom's phrase key is exact
    got = _verdict(
        "Rex is trained by dogs. Is it true that Rex is a dog?", logic_reg
    )
    assert got in ("undetermined", "decline")
