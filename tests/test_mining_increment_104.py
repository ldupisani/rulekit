"""Mining candidate relation-count-frames: relation STANDARDS in count-noun
frames ("K times / half THE NUMBER OF ITEM (that) STANDARD VERBs", "the
amount of ITEM as STANDARD"), including verb-preposition-separated heads.

YAML-only, packs/arithmetic/rules/core.yaml. Reuses the EXISTING
`aggregate_noun` category (packs/core-english/categories/core.yaml --
"the NUMBER of X" / "the AMOUNT of X" frame nouns for ratio rules) rather
than declaring a new one: no new category was needed, satisfying
constitution rule 1 with zero lexicon admission.

Four independent, additive changes:

1. `arithmetic/times-the-number-of` widens `who`/`std` from `type: name` to
   `type: entity` (a common-noun-headed subject/standard, "Dana Point beach
   has four times the number of sharks AS Newport Beach" — the same
   widening arithmetic/times-as-many already carries), plus the paired
   `distinct: [item, std]` self-reference guard, plus an OPTIONAL
   `verb_prep` (cat: preposition) between `verb` and the multiplier for a
   verb-preposition-separated head ("traveled TO twice...", "throws IN 3
   times..." — this exact surface breaks even the canonical 'as many'
   frame; both this rule and the new sibling below tolerate it).

2. `arithmetic/affine-frame-relation` gains an OPTIONAL repeated item noun
   right after `dir` ("Seth sold 6 more CANDY BARS than 3 times the number
   of candy bars that Max sold" — anchored-relation's own "N more ITEM
   than..." headword, restated before the frame continuation; unread,
   never emitted, the `item` slot after 'of' still supplies the measure),
   plus the same `std, type: entity` + `distinct: [item, std]` widening.
   The complementizer `c` stays MANDATORY here — unwidened, deliberately:
   every proven case for this rule already states 'that' explicitly.

3. NEW rule `arithmetic/times-frame-relation-clause`: the PLAIN multiplier
   ratio in the frame form ending in a bare RELATIVE-CLAUSE standard
   instead of times-the-number-of's mandatory "as STD" tail — "Zack has
   traveled to twice the number of countries Patrick traveled to". This
   rule deliberately REQUIRES THE ABSENCE of a complementizer: 'that' is
   lexiconed sense `complementizer`, never in SKIPPABLE_SENSES, so when
   'that' IS present the match simply fails to bind `std` and the whole
   rule declines rather than reading past it. This is the invariant that
   keeps tests/test_mining_increment_94.py's own
   test_partitive_frame_noun_never_misread_as_anaphor passing: "Mark has
   double the number of birds THAT Wendy has" (an unrelated measure, no
   ask ever names it) must keep declining exactly as before this
   candidate — a plain multiplier frame ending in an explicit "that STD"
   clause is arithmetic/affine-frame-relation's / arithmetic/fraction-
   frame-relation's own territory (both require an "N more/fewer than"
   prefix or a fraction respectively), never this rule's.

4. `arithmetic/fraction-frame-relation` widens `std` to `type: entity` (+
   `distinct: [item, std]`), makes its own complementizer `c` OPTIONAL
   ("Joseph traveled to half the number of countries George traveled to" —
   no 'that' at all), and gains the same OPTIONAL `verb_prep` preposition-
   tolerant head as times-the-number-of. Unlike the plain-multiplier case,
   the "with 'that'" span here was ALREADY reachable by the unmodified,
   already-shipped rule (mandatory `c` + `type: name` std) before this
   candidate — only the "no 'that'" sub-case is new, so this widening
   carries no comparable risk to point 3's.

None of these four widen any rule's own literal skeleton (the multiplier/
fraction must still sit immediately before 'the number of' / 'the amount
of'), so a bare "the number of X" with no preceding ratio word — the
overwhelmingly common surface inside GSM8K questions ("what is the total
number of...") — never matches any of them, before or after this candidate.

Gates (full dev, on this junior's own worktree cut from main): dev-train
diff SOLVED 3 / BROKE 0 / DECL->WRONG 0 (VERDICT SHIP, 79 -> 82 correct);
dev-holdout diff SOLVED 1 / BROKE 0 / DECL->WRONG 0 (VERDICT SHIP, 32 -> 33
correct); pytest 830 passed (was 830, no net new — this file itself lands
at the SAME count since the integrator renames/renumbers it); suite 52/52;
lint 0 errors / 1 known-good warning.

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


def test_times_the_number_of_common_noun_subject_and_standard(full_registry):
    # arithmetic/times-the-number-of widened to `type: entity`: both the
    # subject ("Sunset Ridge farm") and the standard ("Prairie View Farm")
    # are common-noun-headed place names, not bare proper names.
    r = solve(
        "Sunset Ridge farm has three times the number of goats as Prairie "
        "View Farm. If Prairie View Farm has 8 goats, how many goats are "
        "there in total on the two farms?",
        full_registry,
    )
    assert r.answer.value == 32


def test_times_the_number_of_preposition_tolerant_head(full_registry):
    # OPTIONAL `verb_prep` between `verb` and the multiplier: a particle
    # sitting between the verb and the ratio must not block the match.
    r = solve(
        "Nadia throws in three times the number of pebbles as Farah. If "
        "Farah throws in 4 pebbles, how many pebbles are there in total?",
        full_registry,
    )
    assert r.answer.value == 16


def test_affine_frame_relation_repeated_item_noun(full_registry):
    # "N more ITEM than K times the number of ITEM that STD sold" — the
    # item noun restated right after `dir`, arithmetic/affine-frame-
    # relation's own new optional `item_echo` slot.
    r = solve(
        "Priya sold 4 more stickers than 2 times the number of stickers "
        "that Omar sold. If Omar sold 15 stickers, how many did Priya "
        "sell?",
        full_registry,
    )
    assert r.answer.value == 34


def test_plain_multiplier_bare_relative_clause_standard(full_registry):
    # arithmetic/times-frame-relation-clause: "K the number of ITEM STD
    # VERBs" with NO complementizer and NO "as" — the candidate's own
    # proven minimal pair (declines today; only the Relation is missing).
    r = solve(
        "Nadia has twice the number of shells Farah has. Farah has 9 "
        "shells. How many shells does Nadia have?",
        full_registry,
    )
    assert r.answer.value == 18


def test_chained_plain_and_fraction_frame_relations_with_preposition_head(
    full_registry,
):
    # a three-hop chain mixing arithmetic/times-frame-relation-clause
    # (twice/three times) and arithmetic/fraction-frame-relation (half,
    # now complementizer-optional) through a preposition-separated verb
    # head ("traveled TO ..."), resolved by the existing chained-relation
    # fixpoint (increment 48) against the one stated anchor.
    r = solve(
        "Deng has traveled to twice the number of cities Amara traveled "
        "to. Amara traveled to three times the number of cities Priya "
        "traveled to. Priya traveled to half the number of cities Tomas "
        "traveled to. If Tomas traveled to 8 cities, how many cities did "
        "Deng travel to?",
        full_registry,
    )
    assert r.answer.value == 24


def test_bare_relative_clause_never_reads_past_an_explicit_complementizer(
    full_registry,
):
    # DECLINE-SAFETY (the increment-94 invariant this candidate must not
    # regress): a plain multiplier frame with 'that' explicit, over an
    # UNRELATED measure the ask never names, must keep declining — 'that'
    # is never skippable, so arithmetic/times-frame-relation-clause simply
    # fails to bind `std` here, and no other rule in this family covers a
    # plain (non-affine, non-fraction) "that STD" tail.
    r = solve(
        "Farid has 12 cookies. Farid has triple the number of ducks that "
        "Lina has. How many cookies does Farid have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_as_frame_and_bare_relative_clause_rules_never_double_fire(full_registry):
    # arithmetic/times-the-number-of (mandatory 'as') and arithmetic/
    # times-frame-relation-clause (no complementizer at all) are
    # structurally disjoint: 'as' is lexiconed sense `particle`, never
    # noun/name-sensed, so it can never satisfy the clause rule's own
    # `std, type: entity` slot. Exactly one Relation fact must be emitted.
    r = solve(
        "Sunset Ridge farm has three times the number of goats as Prairie "
        "View Farm. If Prairie View Farm has 8 goats, how many goats are "
        "there in total on the two farms?",
        full_registry,
    )
    relations = [f for f in r.store.facts if isinstance(f, Relation)]
    assert len(relations) == 1
    assert relations[0].standard == "prairie view farm"


def test_self_referential_standard_declines(full_registry):
    # `distinct: [who, std]` guard: the standard resolves to the SAME
    # entity as the subject ("Wendy ... that Wendy has") — a degenerate
    # comparison, must decline rather than mint a self-referential
    # Relation.
    r = solve(
        "Wendy has twice the number of stickers that Wendy has. How many "
        "stickers does Wendy have?",
        full_registry,
    )
    assert r.answer.kind == "decline"
