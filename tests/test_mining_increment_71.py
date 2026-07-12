"""Mining candidate age-equative-recut: equative age comparatives ("X is
twice as old as Y") and their bare-age anchors. A re-cut of the retained
branch mining/cand-age-equative-relations, which gated clean on dev but
failed constitution review for hardcoding the measure word "year" in
Python; this version gates the bare-age synth on a pack-declared
`age_measure` category instead.

Two coordinated, general mechanisms:

1. `arithmetic/times-as-old-as` (packs/arithmetic/rules/core.yaml) — the
   EQUATIVE sibling of `arithmetic/times-comparative-age-relation` ("N
   times OLDER THAN Y"). Same implicit-'old' anchor, same emitted Relation
   shape (measure 'year', factor k, offset 0), same `distinct: [who, std]`
   self-reference guard; the existing saturate.py relation fixpoint,
   anchored-relation-postfix and ask/how-old-is resolve it unchanged.
   Decline-safety: `absent: {cat: temporal_marker}` blocks the rule when
   the SAME sentence also carries a trailing 'today' — that shape pairs
   with an offset-anchored premise elsewhere in the document ("X turned N
   a year ago") that this rule cannot read, so the item must decline
   rather than commit the plain ratio over the anchor's raw pre-offset
   number.

2. `_bare_age_anchor_synth` (src/rulekit/kernel/saturate.py) — a bare-age
   anchor synth. A leading 'if'-clause split turns "If NAME is N" into an
   ordinary premise, a copula with a bare number and no measure noun,
   which the generic SVO fold can only turn into a valueless Predication.
   The synth promotes it to a Quantity(entity, measure, n) ONLY when that
   entity is already the subject or standard of an `age_measure`-category
   Relation elsewhere in the document — read via
   `reg.word_in_category(measure, "age_measure")`, never a hardcoded
   'year' string (constitution rule 1; mirrors `currency`'s reference
   implementation in answer.py). A bare copula number in a non-age
   document can never become an age, since no age_measure Relation names
   it.

Synthetic only.
"""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import solve

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def full_registry():
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", mined])
    )


def test_equative_forward(full_registry):
    r = solve(
        "Priya is three times as old as Owen. Owen is 6 years old. How old is Priya?",
        full_registry,
    )
    assert r.answer.value == 18


def test_equative_inverse(full_registry):
    # standard unknown, subject known — the existing relation fixpoint's
    # inverse resolution, reached through the new equative rule
    r = solve(
        "Nadia is four times as old as Wren. Nadia is 20 years old. How old is Wren?",
        full_registry,
    )
    assert r.answer.value == 5


def test_equative_chained_with_additive_offsets(full_registry):
    # a chain of four siblings: a stated age, then two additive offsets
    # sandwiching one equative relation — mirrors the class's own
    # chain shape, all synthetic names/numbers
    r = solve(
        "Marisol was 7 years old. Her sister Nadia was 3 years older than "
        "Marisol. Their oldest sister Wren was twice as old as Nadia. "
        "Devon was four years older than Wren. How old was Devon?",
        full_registry,
    )
    assert r.answer.value == 24


def test_bare_age_anchor_via_leading_if(full_registry):
    # "If Felix is 9" — a bare copula number inside a leading conditional,
    # no 'years old'; Felix is the standard of an already-supported
    # comparative relation (times-comparative-age-relation), so the
    # bare-age anchor synth alone (piece 2) must resolve the whole chain
    r = solve(
        "Roman is 6 years older than Theo. Theo is three times as old as "
        "Felix. If Felix is 9, how old is Roman?",
        full_registry,
    )
    assert r.answer.value == 33


def test_self_reference_declines(full_registry):
    r = solve("Wren is twice as old as Wren. How old is Wren?", full_registry)
    assert r.answer.kind == "decline"


def test_trailing_today_declines_rather_than_commits(full_registry):
    # decline-safety: the relation clause carries a trailing 'is today'
    # reading over an anchor phrased as 'turned N a year ago' — the
    # temporal_marker gate must block the equative rule so this stays
    # declined rather than committing the plain ratio over the anchor's
    # raw, un-offset number
    r = solve(
        "Isla is twice as old as Callum is today. If Callum turned 4 a "
        "year ago, how old is Isla today?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_bare_copula_number_unrelated_to_any_age_relation_declines(full_registry):
    # decline-safety: a bare copula number ("If Roman is 9") in a document
    # that DOES contain an age relation, but for OTHER entities (Theo,
    # Felix) — Roman is never a subject/standard of any age_measure
    # Relation, so the bare-age anchor synth must not fire for him, and
    # the ask (about Theo, whose own anchor Felix is never stated) stays
    # declined
    r = solve(
        "Theo is three times as old as Felix. If Roman is 9, how old is Theo?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_bare_copula_number_in_non_age_document_declines(full_registry):
    # decline-safety at the category boundary: no age_measure Relation
    # exists anywhere in the document (this is a currency/count problem),
    # so the bare-age anchor synth must never promote the bare number
    r = solve(
        "If Owen has 9 dollars, how much does Priya have?",
        full_registry,
    )
    assert r.answer.kind == "decline"
