"""Mining increment 102: comparative relation STANDARDS
in un-read frames (possessive-NP standards, mass-measure affine offsets) plus
the age asks they feed (projected "how old will X be in N years", unit-
explicit "how many years old is X").

Five additions (packs/arithmetic/rules/core.yaml unless noted):
(1) arithmetic/times-as-old-as-possessive-standard / -both-possessive: a
    POSSESSIVE-NP age standard ("X is twice Y's age" / "X's age is twice
    Y's age"), sibling of the existing equative arithmetic/times-as-old-as.
(2) arithmetic/times-as-many-possessive-standard: the GENERAL (non-age)
    possessive-NP standard ("X has twice Y's money").
(3) arithmetic/affine-times-as-much: the MASS-noun sibling of arithmetic/
    affine-times-as-many ("$N less/more than K times as much MEASURE as Y").
(4) arithmetic/temporal-offset-age-future-intensified: tolerates an
    intensifier word ('more') wedged between a bare count and its noun in
    the increment-60 temporal-offset premise ("in N MORE years").
(5) Two new age asks (ask/how-many-years-old-is, ask/how-old-will-be-
    projected, ask/how-old-will-be-projected-from-now) plus a new
    `age-projected` consumer (src/rulekit/kernel/answer.py) — reads its
    measure from `query["measure"]` exactly like `single-entity` does
    (constitution rule 1: no hardcoded 'year' literal in Python).

Out of scope for this re-cut (kept OUT per review): a tokenize.py change
teaching the tokenizer the bare TRAILING-APOSTROPHE possessive spelling
("Louis' age", a name already ending in 's', no second 's'). That would
touch the master `_TOKEN` regex every reading passes through, which is
undeclared blast radius for this candidate — dropped rather than widening
shared scan machinery without its own dedicated gate. Ordinary "'s"
possessives (names NOT ending in 's') are unaffected and fully covered
below.

Synthetic only."""

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


def test_possessive_standard_one_sided_age_relation(full_registry):
    # "X is twice Y's age" — no "as old as" anywhere; the standard is a
    # possessive-NP instead. Chains through the existing anchored-relation
    # and a leading-if anchor exactly like the equative form already does.
    r = solve(
        "Priya is twice Ravi's age. Naledi is 5 years older than Priya. "
        "If Ravi is 9, how many years old is Naledi?",
        full_registry,
    )
    assert r.answer.value == 23


def test_possessive_standard_both_sided_age_relation(full_registry):
    # "X's age is twice Y's age" — BOTH subject and standard are owned age
    # NPs; the projected-age ask reads the resolved current age plus offset.
    r = solve(
        "Mateo's age is twice Farah's age. If Farah is 6, "
        "how old will Mateo be after 4 years?",
        full_registry,
    )
    assert r.answer.value == 16


def test_general_possessive_standard_non_age_measure(full_registry):
    # "X has twice Y's money" — the same possessive-NP mechanism over a
    # NON-age measure (the noun's own lemma becomes the Relation's measure,
    # never hardcoded 'year').
    r = solve(
        "Farah has twice Priya's money. If Priya has 15 dollars, "
        "how much money does Farah have?",
        full_registry,
    )
    assert r.answer.value == 30


def test_affine_mass_measure_offset_relation(full_registry):
    # "$N less than K times as much MEASURE as Y" — the mass-noun sibling
    # of the count-form affine relation.
    r = solve(
        "Naledi has 12 dollars less than twice as much money as Priya. "
        "If Priya has $20, how much money does Naledi have?",
        full_registry,
    )
    assert r.answer.value == 28


def test_unit_explicit_age_ask(full_registry):
    # "How many years old is X?" — routes to the SAME single-entity
    # consumer ask/how-old-is already uses.
    r = solve("Nia is 10 years old. How many years old is Nia?", full_registry)
    assert r.answer.value == 10


def test_projected_age_ask_in_years(full_registry):
    r = solve("Deja is 7 years old. How old will Deja be in 6 years?", full_registry)
    assert r.answer.value == 13


def test_projected_age_ask_after_years(full_registry):
    r = solve("Deja is 7 years old. How old will Deja be after 6 years?", full_registry)
    assert r.answer.value == 13


def test_projected_age_ask_years_from_now(full_registry):
    r = solve(
        "Deja is 7 years old. How old will Deja be 6 years from now?", full_registry
    )
    assert r.answer.value == 13


def test_projected_age_ask_without_known_age_declines(full_registry):
    # no current age stated anywhere for Deja — the consumer must decline
    # rather than guess, never fabricate a base age.
    r = solve("How old will Deja be in 6 years?", full_registry)
    assert not r.answer.committed


def test_intensified_temporal_offset_future(full_registry):
    # "In N MORE years" — the increment-60 temporal-offset premise, now
    # tolerant of the intervening intensifier 'more'.
    r = solve(
        "In 6 more years, Priya will be 20 years old. How old is Priya now?",
        full_registry,
    )
    assert r.answer.value == 14


def test_ordinary_more_delta_relation_still_works(full_registry):
    # decline-safety/regression: 'more' now carries BOTH the count-
    # intensifier tag and its pre-existing 'more_dir'/delta tag — the
    # ordinary additive relation reading ("N more X than Y") must still
    # resolve completely unaffected.
    r = solve(
        "Naledi has 5 more apples than Ravi. Ravi has 10 apples. "
        "How many apples does Naledi have?",
        full_registry,
    )
    assert r.answer.value == 15


def test_equative_as_old_as_still_works(full_registry):
    # regression: the pre-existing equative form ("twice AS OLD AS Y") is
    # structurally disjoint from the new possessive-NP rules (no possessive
    # noun ever follows the multiplier here) and must still resolve exactly
    # as it did before this candidate.
    r = solve(
        "Priya is twice as old as Ravi. If Ravi is 9, how old is Priya?",
        full_registry,
    )
    assert r.answer.value == 18


def test_bare_possessive_age_statement_unaffected(full_registry):
    # decline-safety/regression: an ordinary possessive age STATEMENT with
    # NO multiplier at all ("Farah's age is 12") was never read by any
    # premise rule before this candidate (arithmetic/stated-age only
    # matches the literal-'old' "WHO is N years old" copula) and the new
    # relation rules all require a `type: multiplier` slot right after the
    # verb — so this shape still declines exactly as it did before,
    # completely untouched by this candidate.
    r = solve("Farah's age is 12. How old is Farah?", full_registry)
    assert not r.answer.committed
