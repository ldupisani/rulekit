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
    # the fragment guard's contract: a truth-scoping word NO rule reads
    # vetoes the story. Stage 4 gave 'some' a reader (the sentence that
    # originally pinned this now commits — test_some_premise_no_longer_vetoes),
    # so the pin moves to a quantifier surface that remains UNREAD: every
    # reader is at_start-anchored, so a MID-SENTENCE quantifier has no rule
    # and must still veto (readers are construction-scoped, not word-scoped)
    text = ("Rex is a dog. Bob owns all the cats. "
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
            ROOT / "packs/difg-mined",
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


# ---- Stage 2.1: restrictive relative clauses drop (structural) ----------------

def test_relative_clause_drops_to_the_lead_nominal(logic_reg):
    from rulekit.kernel.model import Atom

    r = engine.solve("Rex is a dog who barks.", logic_reg, tracing=False)
    assert {f.pred for f in r.store.by_kind(Atom)} == {"dog who barks", "dog"}


def test_relative_drop_composes_with_instantiation(logic_reg):
    got = _verdict(
        "Bob is a tree that grows in the park. Every tree is a plant. "
        "Is it true that Bob is a plant?", logic_reg)
    assert got == "yes"


def test_relative_drop_composes_with_intersective_strip(intersective_logic_reg):
    from rulekit.kernel.model import Atom

    r = engine.solve(
        "Miroslav was a Czech choral conductor who specialized in music.",
        intersective_logic_reg, tracing=False)
    preds = {f.pred for f in r.store.by_kind(Atom)}
    # the four lead variants x {with tail, without tail}, minus bare head
    # ('choral' is ungated so 'conductor' alone must NEVER appear)
    assert "czech choral conductor" in preds       # relative dropped
    assert "choral conductor" in preds             # both dropped
    assert "czech" in preds
    assert "conductor" not in preds


def test_relative_drop_fires_on_an_unknown_word_lead(logic_reg):
    # 'blicket' is in no lexicon. The decomposable fields are all copular
    # predicate positions, so the construction (copula + article + span)
    # guarantees a nominal lead where the lexicon is silent — the sense
    # gate alone refused every unknown-word lead, which was exactly the
    # class whose keys the lexicon cannot fold (the Stage 8d family).
    from rulekit.kernel.model import Atom

    r = engine.solve("Rex is a blicket who runs.", logic_reg, tracing=False)
    assert "blicket" in {f.pred for f in r.store.by_kind(Atom)}


def test_unknown_lead_drop_composes_with_the_singular_fold(logic_reg):
    assert _verdict(
        "Rex is a blicket who runs. Blickets are gleebs. "
        "Is it true that Rex is a gleeb?", logic_reg,
    ) == "yes"


def test_unknown_lead_drop_null_control(logic_reg):
    got = _verdict(
        "Rex is a blicket who runs. Blickets are gleebs. "
        "Is it true that Rex is a zorp?", logic_reg,
    )
    assert got in ("undetermined", "decline")


def test_unknown_lead_pp_tail_drops_too(logic_reg):
    # the Stage 2.2 sibling under the same gate: a PP after an unknown
    # lead is a restriction — "is a blicket at Yale" is a blicket
    from rulekit.kernel.model import Atom

    r = engine.solve("Rex is a blicket at Yale.", logic_reg, tracing=False)
    assert "blicket" in {f.pred for f in r.store.by_kind(Atom)}


def test_verb_sensed_lead_still_refuses(logic_reg):
    # only the lexicon's SILENCE defers to the construction — a unit with
    # a different sense keeps refusing (a misparse must not decompose)
    from rulekit.kernel.model import Atom

    r = engine.solve("Rex is a dog who runs fast.", logic_reg, tracing=False)
    preds = {f.pred for f in r.store.by_kind(Atom)}
    assert "runs fast" not in preds and "run" not in preds


def test_negative_atom_gets_no_relative_drop(logic_reg):
    from rulekit.kernel.model import Atom

    r = engine.solve("Rex is not a dog who barks.", logic_reg, tracing=False)
    assert [(f.pred, f.polarity) for f in r.store.by_kind(Atom)] == [
        ("dog who barks", False)
    ]


# ---- Stage 2.2: PP restrictions drop (with the quantifier guard) --------------

def test_pp_restriction_drops_to_the_lead_nominal(logic_reg):
    got = _verdict(
        "Bob is a tree in the park. Every tree is a plant. "
        "Is it true that Bob is a plant?", logic_reg)
    assert got == "yes"


def test_pp_with_a_quantifier_never_drops(logic_reg):
    from rulekit.kernel.model import Atom

    # 'no' flips the surface restriction into a denial — the drop is blocked
    r = engine.solve("Bob is a friend of no person.", logic_reg, tracing=False)
    assert {f.pred for f in r.store.by_kind(Atom)} == {"friend of no person"}


def test_relative_with_a_quantifier_still_drops(logic_reg):
    from rulekit.kernel.model import Atom

    # a relative's finite verb scopes its own quantifiers: "a man who knows
    # every senator" is still a man
    r = engine.solve("Bob is a man who knows every senator.", logic_reg,
                     tracing=False)
    assert "man" in {f.pred for f in r.store.by_kind(Atom)}


# ---- Stage 2.3: top-level conjunctive predicates assert both conjuncts --------

def test_conjunctive_predicate_asserts_both_sides(logic_reg):
    from rulekit.kernel.model import Atom

    r = engine.solve("Rex is a dog and a cat.", logic_reg, tracing=False)
    assert {f.pred for f in r.store.by_kind(Atom)} == {"dog and cat", "dog", "cat"}


def test_conjunct_feeds_instantiation(logic_reg):
    got = _verdict(
        "Rex is a dog and a pet. Every pet is loved. "
        "Is it true that Rex is loved?", logic_reg)
    assert got == "yes"


def test_disjunction_asserts_neither_side(logic_reg):
    from rulekit.kernel.model import Atom, Disjunction

    # a disjunctive premise asserts NEITHER disjunct. Stage 2.3 pinned this
    # as an opaque or-atom; Stage 3 reads the construction properly — the
    # copular rules refuse the disjunctive marker and the store holds ONE
    # Disjunction fact and ZERO atoms (case analysis derives, never splits)
    r = engine.solve("Rex is a dog or a cat.", logic_reg, tracing=False)
    assert not [f for f in r.store.by_kind(Atom) if f.entity == "rex"]
    assert [(f.left, f.right, f.exclusive) for f in r.store.by_kind(Disjunction)] == [
        ("dog", "cat", False)
    ]


def test_negative_conjunction_stays_whole(logic_reg):
    from rulekit.kernel.model import Atom

    r = engine.solve("Rex is not a dog and a cat.", logic_reg, tracing=False)
    assert [(f.pred, f.polarity) for f in r.store.by_kind(Atom)] == [
        ("dog and cat", False)
    ]


# ---- Stage 2.4: Quantified.pred / Conditional.then_pred decompose -------------
# (upward-monotone consequents only; cls NEVER strips — downward-monotone)

def test_quantified_pred_decomposes(intersective_logic_reg):
    got = _verdict(
        "Ann is a european. Every european is a czech conductor. "
        "Is it true that Ann is a conductor?", intersective_logic_reg)
    assert got == "yes"


def test_quantified_cls_never_decomposes(intersective_logic_reg):
    # widening the antecedent is unsound: a conductor is not thereby a
    # czech conductor
    got = _verdict(
        "Ann is a conductor. Every czech conductor is a european. "
        "Is it true that Ann is a european?", intersective_logic_reg)
    assert got in ("undetermined", "decline")


def test_negative_quantified_pred_stays_whole(intersective_logic_reg):
    from rulekit.kernel.model import Quantified

    r = engine.solve("No european is a czech conductor.",
                     intersective_logic_reg, tracing=False)
    assert [(f.pred, f.polarity) for f in r.store.by_kind(Quantified)] == [
        ("czech conductor", False)
    ]


def test_quantified_pred_relative_drop_chains(logic_reg):
    got = _verdict(
        "Rex is a student. Every student is a person who studies. "
        "Is it true that Rex is a person?", logic_reg)
    assert got == "yes"


def test_conditional_then_pred_decomposes(intersective_logic_reg):
    got = _verdict(
        "Rex is a dog. Rex is hungry. "
        "If a dog is hungry, then it is a czech conductor. "
        "Is it true that Rex is a conductor?", intersective_logic_reg)
    assert got == "yes"


# ---- Stage 5.1: the indefinite-existential gate (the closure's banked hazard) --

def test_indefinite_premise_mints_no_atom(logic_reg):
    from rulekit.kernel.model import Atom

    # "A Kliner is ..." is an EXISTENTIAL: 'Kliner' (unknown, capitalized)
    # reads as a name and at_start ignores the skipped article, so before
    # the gate this minted atom('kliner', 'spy') — an existential asserted
    # as a ground fact about an entity
    r = engine.solve("A Kliner is a spy.", logic_reg, tracing=False)
    assert not list(r.store.by_kind(Atom))


def test_indefinite_conclusion_subject_declines(logic_reg):
    # "...that A Kliner is a spy?" bound subj='kliner' before the gate; the
    # ask now refuses the construction outright
    got = _verdict(
        "Rex is a spy. Is it true that A Kliner is a spy?", logic_reg)
    assert got in ("undetermined", "decline")


def test_definite_reference_passes_the_gate(logic_reg):
    # 'the' is a REFERENCE, not an existential — the gate must let the ask
    # MATCH (the consumer runs). It stays undetermined for a PRE-EXISTING
    # reason unrelated to the gate: sentence-initial "The Kliner" reads
    # article+name (entity 'kliner') while the mid-sentence question
    # name-merges ('the kliner') — inconsistent keys, decline-safe, present
    # since v2. The assertion is the REASON: the logic consumer ran, so the
    # ask was not refused the way the indefinite is.
    r = engine.solve(
        "The Kliner is a ship. Is it true that The Kliner is a ship?",
        logic_reg, tracing=False)
    assert "logic" in r.answer.reason


def test_bare_name_subject_unchanged(logic_reg):
    got = _verdict("Rex is a dog. Is it true that Rex is a dog?", logic_reg)
    assert got == "yes"


# ---- Stage 9a: the 'All CLS <verb>' restrictor folds like its copular twin ----

def test_verbal_all_restrictor_folds_to_the_singular(logic_reg):
    # 'All' + a bare verb is the PLURAL-AGREEING construction, so its
    # restrictor is plural by grammar while every ground fact naming the
    # class is singular. Without the fold the two keys never join and the
    # instantiation is invisible.
    assert _verdict(
        "All blickets visit the park. Rex is a blicket. "
        "Is it true that Rex visits the park?", logic_reg,
    ) == "yes"


def test_verbal_all_restrictor_fold_null_control(logic_reg):
    # swap the predicate: the answer must MOVE, or the 'yes' above was
    # invariant to its own question
    assert _verdict(
        "All blickets visit the park. Rex is a blicket. "
        "Is it true that Rex visits the museum?", logic_reg,
    ) in ("undetermined", "decline")


def test_verbal_all_restrictor_fold_needs_the_ground_membership(logic_reg):
    assert _verdict(
        "All blickets visit the park. Rex is a gleeb. "
        "Is it true that Rex visits the park?", logic_reg,
    ) in ("undetermined", "decline")


def test_verbal_every_restrictor_never_folds(logic_reg):
    # 'every'/'each' take a SINGULAR restrictor, so folding it would
    # TRUNCATE an s-final singular ('every species' -> 'specie') and mint a
    # key nothing can join. The asymmetry is the contract.
    from rulekit.kernel.model import Quantified

    r = engine.solve("Every blickes visits the park.", logic_reg, tracing=False)
    assert {f.cls for f in r.store.by_kind(Quantified)} == {"blickes"}


def test_verbal_and_copular_all_fold_their_restrictor_alike(logic_reg):
    # the symmetry the Stage 8d invariant demands: one family, one rule
    from rulekit.kernel.model import Quantified

    verbal = engine.solve("All blickets visit the park.", logic_reg, tracing=False)
    copular = engine.solve("All blickets are gleebs.", logic_reg, tracing=False)
    assert {f.cls for f in verbal.store.by_kind(Quantified)} == {"blicket"}
    assert {f.cls for f in copular.store.by_kind(Quantified)} == {"blicket"}


# ---- Stage 9b: a negation is never swallowed into a phrase key ----

def test_neither_nor_mints_no_positive_atom(logic_reg):
    # "X is neither A nor B" asserts ¬A ∧ ¬B. Keying an atom on the whole
    # negated phrase asserts the OPPOSITE of the sentence, and no consumer
    # can see a negation hiding inside a key ('neither' is an ADJECTIVE, so
    # `span_blocks: negation` never caught it).
    from rulekit.kernel.model import Atom

    r = engine.solve("Rex is neither a dog nor a cat.", logic_reg, tracing=False)
    assert list(r.store.by_kind(Atom)) == []


def test_neither_nor_conclusion_is_not_echo_answered(logic_reg):
    # the live hazard the atom above would have created: a conclusion of the
    # same shape echo-matching the junk key and committing a verdict that
    # was never reasoned
    assert _verdict(
        "Rex is neither a dog nor a cat. "
        "Is it true that Rex is neither a dog nor a cat?", logic_reg,
    ) in ("undetermined", "decline")


def test_plain_copular_reading_is_untouched(logic_reg):
    # the marker is scoped to the construction it names -- an ordinary
    # copular premise still mints its atom
    from rulekit.kernel.model import Atom

    r = engine.solve("Rex is a dog.", logic_reg, tracing=False)
    assert {f.pred for f in r.store.by_kind(Atom)} == {"dog"}


def test_a_predicate_merely_containing_neither_still_refuses(logic_reg):
    # fail-closed: any surface carrying the marker is refused rather than
    # read partially, whatever the rest of the construction looks like
    from rulekit.kernel.model import Atom

    r = engine.solve("Rex is neither happy.", logic_reg, tracing=False)
    assert list(r.store.by_kind(Atom)) == []
