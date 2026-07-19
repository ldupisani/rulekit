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
    # `span_blocks: negation` never caught it). At 9b this asserted an
    # EMPTY store (the surface was refused, unread); the 9g De Morgan
    # reader the 9b bank prescribed now reads it as the two NEGATIVE atoms
    # — the invariant that never changes is: no POSITIVE atom, and no key
    # carrying the marker.
    from rulekit.kernel.model import Atom

    r = engine.solve("Rex is neither a dog nor a cat.", logic_reg, tracing=False)
    atoms = list(r.store.by_kind(Atom))
    assert {(a.pred, a.polarity) for a in atoms} == {("dog", False), ("cat", False)}
    assert not any("neither" in a.pred or "nor" in a.pred for a in atoms)


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


# ---- Stage 9c: `bare_form` fails closed on the -s agreement suffix ----

def test_ground_sentence_with_a_self_lemma_verb_mints_no_universal(logic_reg):
    # THE leak. `bare_form` reads `fold == lemma` as "uninflected", which is
    # only as good as the lemma data -- and 'lives' is a lexicon verb with NO
    # mapping to 'live', so it is its own lemma and the most inflected form
    # there is passed the bare-form test. A ground sentence about one named
    # individual was minting a UNIVERSAL over the class 'rochelle'.
    from rulekit.kernel.model import Quantified

    r = engine.solve("Rochelle lives in Europe.", logic_reg, tracing=False)
    assert list(r.store.by_kind(Quantified)) == []


def test_the_generic_it_guards_still_reads(logic_reg):
    # the fix must not cost the capability it protects: a REAL bare-plural
    # generic still mints its universal
    from rulekit.kernel.model import Quantified

    r = engine.solve("Writers create books.", logic_reg, tracing=False)
    assert {(f.cls, f.pred) for f in r.store.by_kind(Quantified)} == {
        ("writer", "create book")
    }


def test_an_agreeing_verb_after_a_name_stays_ground(logic_reg):
    # the same contract through a verb that DOES carry a lemma mapping --
    # 'creates' -> 'create'. Both routes must refuse, or the guard only
    # covers the witness it was written for.
    from rulekit.kernel.model import Quantified

    r = engine.solve("Mary creates books.", logic_reg, tracing=False)
    assert list(r.store.by_kind(Quantified)) == []


def test_a_universal_from_a_ground_sentence_cannot_be_instantiated(logic_reg):
    # why the leak matters: a junk universal is only harmless while nothing
    # joins its class key. Pin the consequence, not just the fact.
    assert _verdict(
        "Blicket attends school. Rex is a Blicket. "
        "Is it true that Rex attends school?", logic_reg,
    ) in ("undetermined", "decline")


# ---- the a/an alternation: one ask reads both articles ----

def test_both_indefinite_articles_reach_the_existential_ask(logic_reg):
    # 'a'/'an' is ALLOMORPHY — one article, two surfaces chosen by the
    # following sound — so it is one alternation, not two asks.
    #
    # It is also the case a CATEGORY cannot serve: both are article-sensed,
    # but `article` is a SKIPPABLE sense, so a gated slot would be skipped past
    # rather than matched. Only `consume_skipped` on the literal stops the skip
    # AT the article, which is why the skip loop had to learn membership.
    from rulekit.kernel import condense, numbers, senses, tokenize
    from rulekit.kernel.patterns import match_all

    # verbs chosen from THIS fixture's pack set — 'published'/'chases' are
    # senseless here (they live in the scratch user pack), and a senseless verb
    # fails the `nonstate_verb` slot before the article is ever reached
    for text in ("Is it true that a dog attends school?",
                 "Is it true that an athlete attends school?"):
        r = tokenize.tokenize(text)
        numbers.annotate_numbers(r, logic_reg)
        senses.annotate_senses(r, logic_reg)
        condense.condense(r, logic_reg)
        hits = [
            a.id for a in logic_reg.asks
            if a.match.get("question")
            and any(True for _ in match_all(r, a.match["question"], logic_reg))
        ]
        assert hits == ["ask/logic-existential-verbal"], text


@pytest.mark.parametrize(
    "text, want",
    [
        ("Is it true that Rex is attended by a dog?", "ask/logic-passive-agent"),
        ("Is it true that Rex is attended by an athlete?", "ask/logic-passive-agent"),
        ("Is it true that Rex was attended by a dog?", "ask/logic-passive-agent"),
        ("Is it true that Rex was attended by an athlete?", "ask/logic-passive-agent"),
        ("Is it true that Rex is a dog?", "ask/logic-embedded-copular"),
        ("Is it true that Rex was a dog?", "ask/logic-embedded-copular"),
        ("Is it true that Rex is not a dog?", "ask/logic-embedded-copular-not"),
        ("Is it true that Rex was not a dog?", "ask/logic-embedded-copular-not"),
    ],
)
def test_tense_and_article_alternations_route_to_one_ask(logic_reg, text, want):
    # Eight asks became three. On the ASK side the copula tense is not read by
    # the consumer, so is/was resolved identically all along — the split was
    # spelling, not meaning.
    from rulekit.kernel import condense, numbers, senses, tokenize
    from rulekit.kernel.patterns import match_all

    r = tokenize.tokenize(text)
    numbers.annotate_numbers(r, logic_reg)
    senses.annotate_senses(r, logic_reg)
    condense.condense(r, logic_reg)
    hits = [
        a.id for a in logic_reg.asks
        if a.match.get("question")
        and any(True for _ in match_all(r, a.match["question"], logic_reg))
    ]
    assert hits == [want], text


def test_the_PREMISE_copula_split_is_NOT_merged(logic_reg):
    # The guard-rail on all of this. On the premise side the copula carries the
    # Stage 8d `.singular` fold: 'are' folds the restrictor, 'is' does not.
    # Merging those the way the ASK side was merged would be a soundness
    # regression, so the two rules must stay distinct with distinct emits.
    from rulekit.kernel.model import Quantified

    are = engine.solve("All blickets are gleebs.", logic_reg, tracing=False)
    assert {f.cls for f in are.store.by_kind(Quantified)} == {"blicket"}   # folded
    is_ = engine.solve("All blickets is gleebs.", logic_reg, tracing=False)
    assert {f.cls for f in is_.store.by_kind(Quantified)} == {"blickets"}  # NOT folded


# ---- Stage 9d: the reduced relative + the restricted bare-plural qdisj ------
# A participial verb heading a predicate nominal's tail is a restrictive
# postmodifier ("a van produced by Chevrolet" IS a van), so the head drops
# exactly as with an overt 'who'/'that'. The guards are structural: a
# 3sg-finite form never postmodifies (single-s suffix, the 9c fail-closed
# precedent), a non-finite participle cannot scope a quantifier in its own
# clause (the PP guard verbatim), and negatives never decompose.


def test_a_participial_tail_drops_to_the_head(logic_reg):
    assert _verdict(
        "Rex is a dog owned by Mary. Is it true that Rex is a dog?", logic_reg
    ) == "yes"


def test_a_participial_tail_with_a_quantifier_refuses(logic_reg):
    assert _verdict(
        "Rex is a dog owned by no farmer. Is it true that Rex is a dog?", logic_reg
    ) == "undetermined"


def test_a_negated_participial_pred_licenses_nothing(logic_reg):
    assert _verdict(
        "Rex is not a dog owned by Mary. Is it true that Rex is a dog?", logic_reg
    ) == "undetermined"


def test_a_finite_verb_tail_refuses(logic_reg):
    # a 3sg-finite verb in this position can only come from a garbled
    # sentence — the head must not be asserted from garbage
    assert _verdict(
        "Bob is a chef serves dinner. Is it true that Bob is a chef?", logic_reg
    ) == "undetermined"


def test_the_participial_drop_never_answers_a_different_head(logic_reg):
    assert _verdict(
        "Rex is a dog owned by Mary. Is it true that Rex is a cat?", logic_reg
    ) == "undetermined"


def test_a_restricted_bare_plural_qdisj_reads_and_lifts_the_veto(logic_reg):
    # the qdisj rule's effect is READING: with the disjunctive premise
    # consumed, the fragment guard lets the story's OTHER commit through
    text = ("The Rover is a wagon owned by Mary. "
            "Wagons owned by Mary are either red or blue. "
            "Is it true that The Rover is a wagon?")
    assert _verdict(text, logic_reg) == "yes"


def test_the_qdisj_restrictor_stays_in_the_cls_key(logic_reg):
    # downward-monotone position: the restriction may never be dropped
    from rulekit.kernel.model import QuantifiedDisjunction

    r = engine.solve("Wagons owned by Mary are either red or blue.",
                     logic_reg, tracing=False)
    facts = list(r.store.by_kind(QuantifiedDisjunction))
    assert len(facts) == 1
    assert facts[0].cls == "wagon own by mary"
    assert (facts[0].left, facts[0].right, facts[0].exclusive) == ("red", "blue", True)


def test_a_qdisj_asserts_neither_disjunct(logic_reg):
    # a disjunction asserts neither side — for the quantified form too
    text = ("The Rover is a wagon owned by Mary. "
            "Wagons owned by Mary are either red or blue. "
            "Is it true that The Rover is red?")
    assert _verdict(text, logic_reg) == "undetermined"


# ---- Stage 9e: the stated alias --------------------------------------------
# "NAME is/was (also) known as NAME2" states an identity between two names;
# ground atoms carry across it in both directions and at both polarities.
# Narrow by design: proper names only (a description is not a name), and the
# negated surface never matches.


def test_atoms_carry_forward_across_a_stated_alias(logic_reg):
    assert _verdict(
        "Mary Poppins is a nanny. Mary Poppins is also known as Sky Danvers. "
        "Is it true that Sky Danvers is a nanny?", logic_reg
    ) == "yes"


def test_atoms_carry_backward_across_a_stated_alias(logic_reg):
    assert _verdict(
        "Sky Danvers is a nanny. Mary Poppins is also known as Sky Danvers. "
        "Is it true that Mary Poppins is a nanny?", logic_reg
    ) == "yes"


def test_a_negative_atom_carries_too(logic_reg):
    # identity transfers what is DENIED as much as what is asserted
    assert _verdict(
        "Mary Poppins is not a nanny. Mary Poppins is also known as Sky Danvers. "
        "Is it true that Sky Danvers is a nanny?", logic_reg
    ) == "no"


def test_no_alias_no_carry(logic_reg):
    assert _verdict(
        "Mary Poppins is a nanny. Is it true that Sky Danvers is a nanny?",
        logic_reg
    ) == "undetermined"


def test_the_optional_also_is_optional(logic_reg):
    assert _verdict(
        "Mary Poppins is a nanny. Mary Poppins is known as Sky Danvers. "
        "Is it true that Sky Danvers is a nanny?", logic_reg
    ) == "yes"


def test_a_definite_epithet_is_not_an_alias(logic_reg):
    # "known as THE Governess" is a description; the definite-article gate
    # refuses it and nothing carries
    assert _verdict(
        "Mary Poppins is a nanny. Mary Poppins is also known as the Governess. "
        "Is it true that Governess is a nanny?", logic_reg
    ) == "undetermined"


def test_a_negated_known_as_states_no_alias(logic_reg):
    # 'not' between the copula and 'known' breaks the lit adjacency — the
    # rule has no polarity field to get wrong because the surface never
    # matches
    assert _verdict(
        "Mary Poppins is a nanny. Mary Poppins is not known as Sky Danvers. "
        "Is it true that Sky Danvers is a nanny?", logic_reg
    ) == "undetermined"


def test_the_alias_match_is_not_subsumed_by_the_copular_span(logic_reg):
    # the regression the trailing-punct opt token exists for: the general
    # copular rule's pred span swallows the final '.', and a strict-superset
    # match silently drops this rule's at admit_rule_results
    from rulekit.kernel.model import Alias

    r = engine.solve("Mary Poppins is also known as Sky Danvers.",
                     logic_reg, tracing=False)
    facts = list(r.store.by_kind(Alias))
    assert len(facts) == 1
    assert (facts[0].a, facts[0].b) == ("mary poppins", "sky danvers")


# ---- Stage 9f: the appointive passive + the unmerged lead run ---------------
# "NAME was APPOINTED as PRED" asserts the resulting role (appointive_verb is
# a SOUNDNESS category — resultative members only, never 'regarded/described').
# The buyer's pred carries a temporal PP whose drop needs the lead nominal to
# extend across an UNMERGED noun run ('museum curator' when the lexicon knows
# neither word as a compound partner).


def test_an_appointive_passive_asserts_the_role(logic_reg):
    assert _verdict(
        "Nora Vale was appointed as a museum curator. "
        "Is it true that Nora Vale is a museum curator?", logic_reg
    ) == "yes"


def test_the_temporal_pp_drops_after_an_unmerged_lead_run(logic_reg):
    assert _verdict(
        "Nora Vale was appointed as a museum curator after her promotion. "
        "Is it true that Nora Vale is a museum curator?", logic_reg
    ) == "yes"


def test_the_asserted_role_refutes_its_negated_conclusion(logic_reg):
    assert _verdict(
        "Nora Vale was appointed as a museum curator. "
        "Is it true that Nora Vale was not a museum curator?", logic_reg
    ) == "no"


def test_a_negated_appointment_asserts_no_role(logic_reg):
    assert _verdict(
        "Nora Vale was not appointed as a museum curator. "
        "Is it true that Nora Vale is a museum curator?", logic_reg
    ) == "undetermined"


def test_the_quantifier_guard_survives_the_lead_run_extension(logic_reg):
    # "of no gallery" inside the PP: the drop must refuse exactly as it
    # does after a single-unit lead
    assert _verdict(
        "Nora Vale was appointed as a museum curator of no gallery. "
        "Is it true that Nora Vale is a museum curator?", logic_reg
    ) == "undetermined"


def test_the_appointive_role_never_leaks_to_another_pred(logic_reg):
    assert _verdict(
        "Nora Vale was appointed as a museum curator. "
        "Is it true that Nora Vale is a gardener?", logic_reg
    ) == "undetermined"


def test_a_verbal_some_premise_reads_as_an_existential(logic_reg):
    # the reading half: 'Some' is consumed (fragment-guard veto lifts) and
    # the fact is a sound ∃
    from rulekit.kernel.model import Existential

    r = engine.solve("Some referees become observers.", logic_reg, tracing=False)
    facts = list(r.store.by_kind(Existential))
    assert len(facts) == 1
    assert facts[0].cls == "referee"
    assert facts[0].pred == "become observers"
    assert facts[0].polarity is True


# ---- Stage 9g: the typed enumeration + the De Morgan neither/nor -----------
# "There are N TYPES of CLS: A, B, …, and F" reads one subtype universal per
# listed item (the per-item emit, schemas.FactEmit.each); the list's 'and' is
# consumed AND understood, which is what lifts the fragment guard for the
# story's stated facts. "X is neither A nor B" asserts two negative atoms —
# the one disjunctive surface needing no exclusivity measurement (9b bank).


def test_neither_nor_denies_both_sides(logic_reg):
    assert _verdict("Rex is neither a dog nor a cat. Is it true that Rex is a dog?",
                    logic_reg) == "no"
    assert _verdict("Rex is neither a dog nor a cat. Is it true that Rex is a cat?",
                    logic_reg) == "no"


def test_neither_nor_licenses_nothing_about_a_third_class(logic_reg):
    assert _verdict("Rex is neither a dog nor a cat. Is it true that Rex is a fox?",
                    logic_reg) == "undetermined"


def test_an_enumeration_reads_one_subtype_universal_per_item(logic_reg):
    from rulekit.kernel.model import Quantified

    r = engine.solve("There are three types of pets: dogs, cats, and foxes.",
                     logic_reg, tracing=False)
    facts = {(f.cls, f.pred, f.polarity) for f in r.store.by_kind(Quantified)}
    assert ("dog", "pet", True) in facts
    assert ("cat", "pet", True) in facts
    assert ("fox", "pet", True) in facts


def test_the_enumeration_lifts_the_veto_for_a_stated_negative(logic_reg):
    assert _verdict(
        "There are three types of pets: dogs, cats, and foxes. Rex is not a dog. "
        "Is it true that Rex is a dog?", logic_reg
    ) == "no"


def test_an_enumeration_asserts_nothing_about_an_individual(logic_reg):
    assert _verdict(
        "There are three types of pets: dogs, cats, and foxes. "
        "Is it true that Rex is a dog?", logic_reg
    ) == "undetermined"


def test_a_possessive_enumeration_is_not_a_type_list(logic_reg):
    # "districts of Russia" — the items are districts, not Russias; the
    # enumeration_type_noun gate keeps the rule off the construction, and
    # NO subtype universal may mint ('unread is sound, misread is not')
    from rulekit.kernel.model import Quantified

    r = engine.solve("There are three districts of Ruritania: North, South, and East.",
                     logic_reg, tracing=False)
    assert not [f for f in r.store.by_kind(Quantified) if f.pred == "ruritania"]


# ---- Stage 9h: the exhaustive counted enumeration + n-way elimination ------
# "There are N types of CLS: …" with exactly N listed segments mints ONE
# EnumeratedDisjunction beside the per-item universals — the numeral is what
# licenses exhaustiveness, so a mismatched count mints nothing (fail
# closed). Its only consumer is synth/enumeration-elimination: a stated
# member of the class with every option but one refuted by explicit
# negative atoms is the last option. INCLUSIVE — membership in one option
# never denies another.


def test_nway_elimination_derives_the_last_open_option(logic_reg):
    assert _verdict(
        "There are three types of pets: dogs, cats, and foxes. "
        "Rex is not a dog. Rex is not a cat. Rex is a pet. "
        "Is it true that Rex is a fox?", logic_reg
    ) == "yes"


def test_elimination_composes_with_the_de_morgan_reader(logic_reg):
    # the refutations arrive as ONE neither/nor sentence — the buyer's shape
    assert _verdict(
        "There are three types of pets: dogs, cats, and foxes. "
        "Rex is neither a dog nor a cat. Rex is a pet. "
        "Is it true that Rex is a fox?", logic_reg
    ) == "yes"


def test_elimination_needs_stated_membership(logic_reg):
    # no "Rex is a pet" premise — an entity refuted out of two options is
    # not thereby a member of the enumerated class at all
    assert _verdict(
        "There are three types of pets: dogs, cats, and foxes. "
        "Rex is not a dog. Rex is not a cat. "
        "Is it true that Rex is a fox?", logic_reg
    ) == "undetermined"


def test_elimination_needs_all_but_one_refuted(logic_reg):
    # two options still open — nothing follows
    assert _verdict(
        "There are three types of pets: dogs, cats, and foxes. "
        "Rex is not a dog. Rex is a pet. "
        "Is it true that Rex is a fox?", logic_reg
    ) == "undetermined"


def test_a_count_mismatch_mints_no_disjunction(logic_reg):
    # stated FOUR, listed three: the numeral's exhaustiveness claim fails
    # its own arithmetic, so no EnumeratedDisjunction may exist and the
    # elimination that would need it must stay silent (fail closed); the
    # per-item subtype universals are still sound and still mint
    from rulekit.kernel.model import EnumeratedDisjunction

    text = ("There are four types of pets: dogs, cats, and foxes. "
            "Rex is not a dog. Rex is not a cat. Rex is a pet. ")
    r = engine.solve(text + "Is it true that Rex is a fox?",
                     logic_reg, tracing=False)
    assert not list(r.store.by_kind(EnumeratedDisjunction))
    assert _verdict(text + "Is it true that Rex is a fox?",
                    logic_reg) == "undetermined"


def test_a_decided_member_blocks_elimination(logic_reg):
    # Rex already IS a cat: under the inclusive reading a member may
    # satisfy several options, so the last open option must NOT be
    # asserted from a positive classification
    assert _verdict(
        "There are three types of pets: dogs, cats, and foxes. "
        "Rex is not a dog. Rex is a cat. Rex is a pet. "
        "Is it true that Rex is a fox?", logic_reg
    ) == "undetermined"


def test_a_quarantined_option_blocks_elimination(logic_reg):
    # "is a dog" / "is not a dog" is a contradiction — both atoms
    # quarantine OUT of store.facts, so the dog option would read as
    # merely open to a naive elimination; the taint guard must keep it
    # from minting a fox atom, and the store's conflict machinery then
    # DECLINES the item outright (contradictory premises never commit)
    from rulekit.kernel.model import Atom

    r = engine.solve(
        "There are three types of pets: dogs, cats, and foxes. "
        "Rex is a dog. Rex is not a dog. Rex is not a cat. Rex is a pet. "
        "Is it true that Rex is a fox?", logic_reg, tracing=False)
    assert not [f for f in r.store.by_kind(Atom) if f.pred == "fox"]
    assert r.answer.kind == "decline"
