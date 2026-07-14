"""Mining candidate relation-standard-frames: relation STANDARDS in nominal
frames — a count-noun/amount-of-money AFFINE frame ending in an 'as STD' or
bare relative-clause continuation, and a POSSESSIVE-DETERMINER + common-noun
NP standard ("as her sister", "than their grandmother") with no trailing
name at all.

YAML-only, packs/arithmetic/rules/core.yaml. Four new sibling rules, each
additive and structurally disjoint from its base rule (verified below):

1. `arithmetic/times-as-many-possessive-kinship-standard`: the POSSESSIVE-
   KINSHIP sibling of arithmetic/times-as-many. The standard is a bare
   [possessive-determiner, common-noun] NP with NO trailing name — unlike
   the file's pre-existing appositive prefix ("than his friend Sam"), which
   always expects a name to follow the pair. `std_det, type: pronoun` is
   MANDATORY (never optional): this rule exists only for the bare
   determiner+noun shape. `standard: "{std}"` keys off the noun's own
   lemma, exactly the entity key the general SVO fold already uses for a
   sentence like "Her sister has 8 marbles."

2. `arithmetic/anchored-relation-possessive-kinship-standard`: the same
   mechanism one literal over ('than' in place of 'as'), sibling of
   arithmetic/anchored-relation.

3. `arithmetic/affine-frame-relation-as-standard`: the 'as'-continuation
   sibling of arithmetic/affine-frame-relation ("N more/fewer than K times
   the number of ITEM AS STD", instead of the base rule's mandatory 'that'
   complementizer) — the same 'that' vs. 'as' split arithmetic/times-the-
   number-of / arithmetic/times-frame-relation-clause already carry for the
   plain (non-affine) frame, applied here to the affine frame.

4. `arithmetic/affine-item-relation-clause`: the BARE-ITEM sibling of
   arithmetic/times-frame-relation-clause, applied to the affine frame —
   no 'the number/amount OF' framing at all (a money-NP directly, "the
   money STD has"), ending in a bare relative-clause standard with no
   complementizer. `item, type: noun` sits directly after the multiplier
   (no explicit `{lit: the}` — 'the' is sense `article`, already
   auto-skipped by the shared matcher), so it can never collide with the
   'the number of'/'the amount of' frame rules: on that text `item` would
   instead bind the frame noun itself and the next token ('of') can never
   satisfy `std, type: entity`.

In every case, when a NAME follows the [determiner, noun] pair ("as her
sister Mia"), the existing FULLER rule (which also matches through the
name) consumes strictly more tokens and the new sibling's shorter match is
dropped by `subsumes` (facts.py) — the same "bare vs. fuller sibling"
pattern already used throughout this rule file (e.g. arithmetic/times-as-
many-elided-standard vs. arithmetic/times-as-many).

No new consumer and no new fact kind: the mature `synth/relation`
(saturate.py) and the existing `combined` consumer cash in every emitted
Relation exactly as they do for every other relation rule in this file.

Synthetic only.
"""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Relation

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def full_registry():
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", mined])
    )


def test_times_as_many_possessive_kinship_standard(full_registry):
    # "K times as many ITEM as her sister" — no trailing name at all; the
    # sister's own count is stated in a separate sentence, keyed by the
    # bare kinship lemma.
    r = solve(
        "Maya has four times as many marbles as her sister. Her sister "
        "has 6 marbles. How many marbles do they have altogether?",
        full_registry,
    )
    assert r.answer.value == 30


def test_anchored_relation_possessive_kinship_standard_chain(full_registry):
    # a two-hop chain: 'as her sister' (times-as-many family) feeding into
    # 'than their grandmother' (anchored-relation family), anchored by the
    # grandmother's own stated count.
    r = solve(
        "Maya has four times as many marbles as her sister. Her sister "
        "has 5 more marbles than their grandmother. Their grandmother "
        "has 3 marbles. How many marbles do they have altogether?",
        full_registry,
    )
    assert r.answer.value == 3 + 8 + 32


def test_affine_frame_relation_as_standard(full_registry):
    # "N more ITEM than K times the number of ITEM AS STD" — the affine
    # count-noun frame ending in 'as' rather than a 'that'-relative clause.
    r = solve(
        "Talia sold 5 more stickers than 2 times the number of stickers as "
        "Rosa sold. If Rosa sold 12 stickers, how many stickers did Talia sell?",
        full_registry,
    )
    assert r.answer.value == 29


def test_affine_item_relation_clause_money_frame(full_registry):
    # "N dollars less than twice the money STD has" — a bare money-NP
    # frame (no 'of', no 'as', no complementizer) ending in a relative
    # clause.
    r = solve(
        "Talia has $15 less than twice the money Rosa has. If Rosa has "
        "30 dollars, how much money do they have together?",
        full_registry,
    )
    assert r.answer.value == (2 * 30 - 15) + 30


def test_fuller_appositive_still_wins_over_bare_kinship_sibling(full_registry):
    # DECLINE/COLLISION SAFETY: when a NAME follows the [determiner, noun]
    # pair ("as her sister Mia"), the pre-existing FULLER appositive rule
    # must still be the one that fires (subsumption), never the new bare
    # sibling — exactly one Relation, keyed to the NAME, not the noun.
    r = solve(
        "Sena has twice as many seashells as her sister Mia. Mia has 5 "
        "seashells. How many seashells does Sena have?",
        full_registry,
    )
    assert r.answer.value == 10
    relations = [f for f in r.store.facts if isinstance(f, Relation)]
    assert len(relations) == 1
    assert relations[0].standard == "mia"
    assert relations[0].provenance.source == "arithmetic/times-as-many"


def test_possessive_kinship_standard_declines_without_an_antecedent(full_registry):
    # DECLINE SAFETY: the Relation fires (the standard resolves to the
    # bare noun lemma 'sister'), but no sentence anywhere states the
    # sister's own count — the relation stays unresolved and the whole
    # item must decline, never guess.
    r = solve(
        "Maya has four times as many marbles as her sister. How many "
        "marbles does Maya have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_anchored_relation_possessive_kinship_self_reference_declines(
    full_registry,
):
    # DECLINE SAFETY: `distinct: [who, std]` — the possessive-kinship
    # standard resolves to the SAME entity as the subject (both 'sister'),
    # a degenerate self-comparison that must decline outright.
    r = solve(
        "Her sister has 8 more marbles than her sister. How many "
        "marbles does her sister have?",
        full_registry,
    )
    assert r.answer.kind == "decline"
    relations = [f for f in r.store.facts if isinstance(f, Relation)]
    assert relations == []


def test_affine_item_relation_clause_never_misreads_the_number_of_frame(
    full_registry,
):
    # COLLISION SAFETY: arithmetic/affine-item-relation-clause's bare
    # `item, type: noun` must never steal the 'the number of ITEM that
    # STD' frame's own span — on that text `item` would bind the FRAME
    # noun ('number') and the next token ('of') can never satisfy
    # `std, type: entity`, so this rule simply fails to match, leaving the
    # dedicated frame rule (arithmetic/affine-frame-relation) as the sole
    # survivor.
    r = solve(
        "Talia sold 5 more stickers than 2 times the number of stickers that "
        "Rosa sold. If Rosa sold 12 stickers, how many stickers did Talia sell?",
        full_registry,
    )
    assert r.answer.value == 29
    relations = [f for f in r.store.facts if isinstance(f, Relation)]
    assert len(relations) == 1
    assert relations[0].provenance.source == "arithmetic/affine-frame-relation"
