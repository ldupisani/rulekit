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
    # and the proper_name variant reads it. The `.singular` template attr
    # folds the unknown plural to 'wug' so the universal joins ground atoms
    # minted by the SINGULAR copular construction ("Rex is a wug") — the
    # bare-plural construction's own 'are' agreement licenses the fold.
    assert _quants("Wugs are animals.", logic_reg) == {("wug", "animal", True)}


def test_negated_variants_read_as_negative_universal(logic_reg):
    assert _quants("Dogs are not cats.", logic_reg) == {("dog", "cat", False)}
    assert _quants("Wugs are not cats.", logic_reg) == {("wug", "cat", False)}


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


# ---- the `.singular` fold: unknown plurals join singular-construction keys ----
# (the unknown-plural-morphology increment: premise↔premise joins were the
# unmeasured side of the family measured at zero on conclusion↔premise pairs)

def test_unknown_plural_universal_instantiates_the_singular_atom(logic_reg):
    # atom(rex,'wug') from the SINGULAR copular; quantified('wug','zorp',-)
    # from the folded bare-plural — the join the verbatim key missed
    assert _verdict(
        "Rex is a wug. Wugs are not zorps. Is it true that Rex is a zorp?",
        logic_reg,
    ) == "no"


def test_unknown_plural_positive_universal_instantiates(logic_reg):
    assert _verdict(
        "Rex is a wug. Wugs are gleebs. Is it true that Rex is a gleeb?",
        logic_reg,
    ) == "yes"


def test_unknown_plural_fold_is_symmetric_with_the_conclusion_ask(logic_reg):
    # the ask side folds the same family the premise side does — an
    # asymmetric fold would break the echo that works today
    assert _verdict(
        "Wugs are not zorps. Is it true that no wugs are zorps?", logic_reg
    ) == "yes"


def test_singular_unknown_never_folds():
    # the naive fold's own guards: -ss and short words stay verbatim (a
    # plural-agreeing span can still contain a non-plural s-word), the
    # -ies/-es/-s rules fold. Direct pins — a construction-level probe
    # cannot isolate them (compound generics are refused upstream).
    from rulekit.kernel.patterns import _naive_singular

    assert _naive_singular("chess") == "chess"
    assert _naive_singular("bliss") == "bliss"
    assert _naive_singular("gas") == "gas"
    assert _naive_singular("bus") == "bus"
    assert _naive_singular("wugs") == "wug"
    assert _naive_singular("stories") == "story"
    assert _naive_singular("boxes") == "box"
    assert _naive_singular("singers") == "singer"


def test_known_word_keys_are_byte_identical(logic_reg):
    # the fold touches only words the LEXICON cannot fold — known plurals
    # already fold to their lemma, and this pins that path unchanged
    assert _quants("Dogs are animals.", logic_reg) == {("dog", "animal", True)}
    assert _quants("All dogs are animals.", logic_reg) == {("dog", "animal", True)}


def test_names_inside_spans_keep_their_surface_key(logic_reg):
    # a mid-span capitalized unknown is a NAME ('Knicks players') — the
    # fold must not touch it: only SENSELESS units fold inside spans
    quants = _quants("All Knicks players are gleebs.", logic_reg)
    assert quants and all(cls == "knicks player" for cls, _p, _pol in quants)


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
