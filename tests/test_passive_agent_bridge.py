"""S2 (composition-design.md): VerbalRelation + the passive-agent
membership bridge.

"Nash built the tower. Nash is a farmer. ⊢ the tower is built by a
farmer" — ∃-introduction over the AGENT, sound for any verb because the
premise itself supplies the witness. All segmentation is match-token
work: the premise rule captures subj/v/obj separately (direct objects
only — a PP tail falls back to the flat atom), the ask captures
subj/v/cls and CLAIMS the 'a/an' (consume_skipped). No key surgery
anywhere, and the flat atom keeps being emitted beside the structured
fact (echo behavior byte-identical — pinned).
"""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Atom, VerbalRelation

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def logic_reg():
    return compile_registry(
        load_packs([
            ROOT / "packs/core-english",
            ROOT / "packs/arithmetic",
            ROOT / "packs/difg-mined",
            ROOT / "projects/scratch/packs/user",
            ROOT / "packs/logic",
        ])
    )


def _verdict(text, reg):
    r = engine.solve(text, reg, tracing=False)
    return r.answer.value if r.answer.kind == "verdict" else r.answer.kind


# ---- emission: the structured fact rides BESIDE the flat atom -----------------

def test_verbal_relation_emitted_beside_the_flat_atom(logic_reg):
    r = engine.solve("Rex eats mice.", logic_reg, tracing=False)
    vrs = [(f.entity, f.verb, f.obj) for f in r.store.by_kind(VerbalRelation)]
    atoms = {f.pred for f in r.store.by_kind(Atom) if f.entity == "rex"}
    assert vrs == [("rex", "eat", "mouse")]  # known plural folds to its lemma
    assert "eat mouse" in atoms  # the flat echo key is untouched


def test_pp_tail_reads_flat_only(logic_reg):
    # a PP after the object would mis-segment obj — the dobj rule refuses
    # (span_blocks: preposition) and only the flat atom is emitted
    r = engine.solve("Rex eats mice in Spain.", logic_reg, tracing=False)
    assert list(r.store.by_kind(VerbalRelation)) == []
    assert "eat mouse in spain" in {f.pred for f in r.store.by_kind(Atom)}


# ---- the bridge ---------------------------------------------------------------

def test_passive_agent_bridge(logic_reg):
    assert _verdict(
        "Nash designed Oxford Circus. Nash is a British architect. "
        "Is it true that Oxford Circus is designed by a British architect?",
        logic_reg,
    ) == "yes"


def test_bridge_uses_decomposed_class_variants(logic_reg):
    # 'a British architect who eats mice' decomposes (Stage 2.1) to
    # 'british architect' — the bridge reads variants, not just direct atoms
    assert _verdict(
        "Nash designed Oxford Circus. Nash is a British architect who eats mice. "
        "Is it true that Oxford Circus is designed by a British architect?",
        logic_reg,
    ) == "yes"


# ---- null controls ------------------------------------------------------------

def test_null_control_class_swapped(logic_reg):
    got = _verdict(
        "Nash designed Oxford Circus. Nash is a British architect. "
        "Is it true that Oxford Circus is designed by a British musician?",
        logic_reg,
    )
    assert got in ("undetermined", "decline")


def test_null_control_membership_cut(logic_reg):
    got = _verdict(
        "Nash designed Oxford Circus. "
        "Is it true that Oxford Circus is designed by a British architect?",
        logic_reg,
    )
    assert got in ("undetermined", "decline")


def test_null_control_relation_cut(logic_reg):
    got = _verdict(
        "Nash is a British architect. "
        "Is it true that Oxford Circus is designed by a British architect?",
        logic_reg,
    )
    assert got in ("undetermined", "decline")


# ---- soundness edges ----------------------------------------------------------

def test_definite_agent_declines(logic_reg):
    # 'by THE architect' — a definite agent needs reference resolution; the
    # a/an lits do not match and no other ask claims the construction
    got = _verdict(
        "Nash designed Oxford Circus. Nash is a British architect. "
        "Is it true that Oxford Circus is designed by the British architect?",
        logic_reg,
    )
    assert got in ("undetermined", "decline")


def test_indefinite_object_relation_never_matches_a_referent(logic_reg):
    # "designed a tower" is SOME tower — it must not witness a question
    # about the particular entity Tower (VerbalRelation.indef_obj)
    got = _verdict(
        "Nash designed a Tower. Nash is a British architect. "
        "Is it true that Tower is designed by a British architect?",
        logic_reg,
    )
    assert got in ("undetermined", "decline")


def test_copular_echo_with_by_still_unaffected_premise_side(logic_reg):
    # the agent_marker span block is ASK-side only: a copular PREMISE
    # containing 'by' still mints its atom (the Edwin Smith shape)
    r = engine.solve("Rex is a dog trained by Nash.", logic_reg, tracing=False)
    assert any("trained by nash" in f.pred for f in r.store.by_kind(Atom))


# ---- S2: conjunctive subjects distribute (the fragment-veto unlock) -----------

def test_conjunctive_subjects_distribute(logic_reg):
    r = engine.solve("Ann and Bob are teachers.", logic_reg, tracing=False)
    got = {(f.entity, f.pred) for f in r.store.by_kind(Atom)}
    assert got == {("ann", "teacher"), ("bob", "teacher")}


def test_collective_predicate_never_distributes(logic_reg):
    # "are A team": the indefinite article is the collective's structural
    # signal — neither conjunct is a team; the sentence stays unread and
    # the fragment guard keeps vetoing its story
    r = engine.solve("Ann and Bob are a team.", logic_reg, tracing=False)
    assert list(r.store.by_kind(Atom)) == []


def test_distribution_lifts_the_fragment_veto(logic_reg):
    # the buyer's shape: an and-subject premise used to veto every verdict
    # in its story; once READ, the unrelated bridge conclusion answers
    assert _verdict(
        "Ann and Bob are in Spain. Nash designed Oxford Circus. "
        "Nash is a British architect. "
        "Is it true that Oxford Circus is designed by a British architect?",
        logic_reg,
    ) == "yes"


# ---- S1: active relative-clause predication + the negated PP-object ask -------

def test_relative_clause_emits_the_verbal_relation(logic_reg):
    r = engine.solve("Rex is a dog who plays for Ann.", logic_reg, tracing=False)
    vrs = [(f.entity, f.verb, f.prep, f.obj) for f in r.store.by_kind(VerbalRelation)]
    assert vrs == [("rex", "play", "for", "ann")]
    # the copular atom keeps reading the sentence beside it
    assert any("dog who play for ann" in f.pred for f in r.store.by_kind(Atom))


def test_passive_relative_stays_unread_here(logic_reg):
    # 'who was …' fails the nonstate_verb slot — the passive-relative form
    # is its own deferred increment; the copular atom still reads
    r = engine.solve("Rex is a dog who was trained by Ann.", logic_reg, tracing=False)
    assert list(r.store.by_kind(VerbalRelation)) == []


def test_negated_pp_object_claim_refuted_by_witness(logic_reg):
    assert _verdict(
        "Rex is a dog who plays for Ann. Ann is a farmer. "
        "Is it true that Rex does not play for a farmer?", logic_reg
    ) == "no"


def test_pp_object_null_control_class_swapped(logic_reg):
    got = _verdict(
        "Rex is a dog who plays for Ann. Ann is a farmer. "
        "Is it true that Rex does not play for a musician?", logic_reg
    )
    assert got in ("undetermined", "decline")


def test_pp_object_null_control_membership_cut(logic_reg):
    got = _verdict(
        "Rex is a dog who plays for Ann. "
        "Is it true that Rex does not play for a farmer?", logic_reg
    )
    assert got in ("undetermined", "decline")


def test_pp_object_null_control_relation_cut(logic_reg):
    got = _verdict(
        "Ann is a farmer. "
        "Is it true that Rex does not play for a farmer?", logic_reg
    )
    assert got in ("undetermined", "decline")


def test_absence_never_proves_the_negation(logic_reg):
    # ¬∃ from silence would be closed-world — the one thing this consumer
    # must never do
    got = _verdict(
        "Rex is a dog. Is it true that Rex does not play for a farmer?",
        logic_reg,
    )
    assert got in ("undetermined", "decline")
