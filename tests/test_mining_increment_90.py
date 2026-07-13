"""Mining candidate appositive-relation-standards: relations whose STANDARD
is introduced by an appositive ("than his friend Sam", "than her sister,
Gigi") rather than being the standard itself. Every relation rule's `std`
slot (packs/arithmetic/rules/core.yaml) gains an optional, SKIPPABLE
appositive prefix — a possessive determiner (his/her/their/its; lexicon
sense `pronoun`, matched unconditionally) plus a common noun (any word
sensed `noun` — no kinship/role word list) immediately before the slot.
When both are present, the opt block consumes them and `std` binds the
NAME that follows instead of the descriptive role noun; a trailing comma
between the role noun and the name is already auto-skipped by the
existing SKIPPABLE_SENSES mechanism (punct), same as every other
punct-adjacent match in this file. When no such [pronoun, noun] pair sits
there, the opt block cannot match at all and every rule is byte-identical
to before this candidate. This is a PRECISION fix (constitution rule 4):
on unmodified main, an appositive-introduced standard either declines a
relation that should resolve, or — on an event verb — lets the raw delta
event be folded as if it were the whole answer (a confident wrong).
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


def test_additive_relation_over_appositive_friend_resolves(full_registry):
    # the event-verb confident-wrong this candidate's evidence traced: the
    # unresolved relation used to be dropped and the raw delta event ("runs
    # 8 miles more") folded as if it were the subject's own total (8.0
    # instead of 20.0).
    r = solve(
        "Priya runs 8 miles more than her friend Nadia. Nadia runs 12 miles. "
        "How many miles does Priya run?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 20


def test_additive_relation_over_comma_appositive_daughter_resolves(full_registry):
    # the second traced confident-wrong: a comma-set appositive ("his
    # daughter, NAME") over a state verb, asked as a combined total.
    r = solve(
        "Mr. Alvarez is three feet taller than his daughter, Renata. "
        "Renata is 4 feet tall. How many feet do they have in total?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 11


def test_times_as_many_over_appositive_buddy_resolves(full_registry):
    # a multiplicative relation ("as much as his cousin NAME") over an
    # appositive-introduced standard.
    r = solve(
        "Owen has 5 dollars. Miguel has three times as much money as his "
        "cousin Owen. How much money does Miguel have?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 15


def test_bare_name_standard_regression(full_registry):
    # regression: an ordinary bare-name standard (no appositive at all)
    # resolves exactly as it did before this candidate.
    r = solve(
        "Ann has 5 apples. Tom has 2 more apples than Ann. "
        "How many apples does Tom have?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 7


def test_bare_role_noun_standard_with_no_name_still_declines(full_registry):
    # decline-safety: the brief's explicitly out-of-scope case — a bare
    # possessive role noun with NO trailing name ("than his sister") must
    # keep declining exactly as before, never silently guess a standard.
    r = solve(
        "Tom has 2 more apples than his sister. How many apples does Tom have?",
        full_registry,
    )
    assert not r.answer.committed


def test_appositive_standard_with_no_matching_quantity_declines(full_registry):
    # decline-safety: the appositive NAME resolves as the standard, but no
    # quantity is ever stated for that name — must decline rather than
    # commit an unresolved relation.
    r = solve(
        "Jonah has 4 more marbles than his friend Wes. "
        "How many marbles does Jonah have?",
        full_registry,
    )
    assert not r.answer.committed


def test_elided_measure_relation_over_appositive_standard_resolves(full_registry):
    # the elided-measure relation sibling (increment 85) composes with the
    # appositive prefix with no further change — same opt block applies to
    # every relation rule's std slot uniformly.
    r = solve(
        "Leah has 20 stickers. Priya has 5 more than her friend Leah. "
        "How many stickers does Priya have?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 25
