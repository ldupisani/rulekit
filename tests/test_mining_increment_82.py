"""Relations whose subject or standard is an index-labeled entity ("Jar A" /
"Jar B" / "Box P"). Increment 74 (index-labeled entity identity) gave
Quantity a `label` field and FactStore.admit a collision-time re-key so two
directly-stated same-noun holdings distinguished only by a trailing index
letter no longer collide as one fact-store entity — but a RELATION between
two labeled entities ("Jar B has 12 more marbles than jar A") emitted
NOTHING at all: the relation pattern rules' `who`/`std` slots (already
widened to `type: entity`, so they structurally accept a labeled common
noun) still bare-fold both sides to the SAME lemma ('jar'), and every
`distinct: [who, std]` self-reference guard treats that as "X compares to
itself" and silently declines the whole relation.

Mechanism (kernel + YAML, additive only):

1. `_check_where`'s `distinct` predicate (patterns.py) compares (lemma,
   label) pairs instead of bare lemma alone — two units sharing a lemma AND
   carrying two DIFFERENT non-null labels are no longer treated as the same
   referent. Every existing distinct check (both sides unlabeled, i.e.
   label=None on both) compares exactly as before.
2. `Relation` (model.py) gains `subject_label`/`standard_label` fields,
   included in `key()` so two differently-labeled relations that happen to
   share the same bare subject/standard/measure/verb never collide or
   dedupe against each other. Both fields default to a value that makes an
   ordinary (unlabeled) relation's key identical in shape to before.
3. The seven relation rules whose `who`/`std` slots already accept
   `type: entity` (anchored-relation, anchored-relation-postfix,
   anchored-relation-postfix-dimension, times-as-many, fraction-as-many,
   affine-times-as-many, affine-fraction-as-many — packs/arithmetic/rules/
   core.yaml) additionally emit `subject_label: "{who.label}"` /
   `standard_label: "{std.label}"`. The `type: name`-only relation rules
   (times-as-much, fraction-as-much, the age/frame relations, ...) are
   untouched — a labeled common noun has sense "noun", never "name", so
   they were never reachable by this class and stay that way.
4. `saturate.py::_relations_synth` gains a label-keyed index alongside its
   existing bare-entity one: when a relation names a labeled standard, it
   resolves against the SPECIFIC same-label Quantity (never an arbitrary
   same-lemma sibling, never a different label) or declines; the derived
   Quantity for the relation's subject is tagged with the subject's own
   label so a later same-lemma sibling can be told apart from it via the
   SAME facts.py collision-time re-key increment 74 already ships. The
   inverse direction (subject known, standard derived) is symmetric.

Every relation test below deliberately uses a STATE verb ('has') on both
sides — a pre-existing, unrelated latent gap in `_relations_synth`'s
round-2 fallthrough (branches 2/3 are reachable even when branch 1's own
anchor succeeded but is blocked by the re-derivation guard) can double-count
a relation stated with an EVENT verb ("Ann picked up 6 more than Tom")
against an anchor stated with a DIFFERENT verb ("Tom has..."); reproduced
on unmodified `main` with no labels involved at all, so it is out of scope
for this candidate's class and is not exercised here.

Synthetic only — every proper noun/number/object below is invented; none
is drawn from any GSM8K item.
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


def test_prefix_relation_between_two_labeled_entities_resolves(full_registry):
    # "N more ITEM than STD" (arithmetic/anchored-relation) — the class's
    # core failure: who/std both bare-fold to 'jar', so without the
    # (lemma, label) distinct fix this declined outright.
    r = solve(
        "Jar X has 15 marbles. Jar Y has 6 more marbles than jar X. "
        "How many marbles are there in total?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 36


def test_postfix_relation_between_two_labeled_entities_resolves(full_registry):
    # "ITEM more than STD" (arithmetic/anchored-relation-postfix) — same
    # class, the postfix comparative order.
    r = solve(
        "Jar A has 18 marbles. Jar B has 6 marbles more than jar A. "
        "How many marbles are there in total?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 42


def test_times_as_many_labeled_relation_resolves(full_registry):
    # arithmetic/times-as-many — a pure-ratio labeled relation.
    r = solve(
        "Team A has 20 players. Team B has twice as many players as team A. "
        "How many players are there in total?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 60


def test_fraction_as_many_labeled_relation_resolves(full_registry):
    # arithmetic/fraction-as-many — the fraction-ratio sibling.
    r = solve(
        "Team A has 20 players. Team B has half as many players as team A. "
        "How many players are there in total?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 30


def test_three_way_labeled_chain_resolves(full_registry):
    # a chain of two labeled relations (anchored-relation then
    # times-as-many), mirroring the payoff class this candidate's
    # evidence names: the second relation's standard is itself only
    # resolved by the FIRST relation, across saturate() rounds, and the
    # by-verb re-derivation guard must not block the second link just
    # because the bare-lemma 'box' key was already used by the first.
    r = solve(
        "Box P has 10 pencils. Box Q has 4 more pencils than box P. "
        "Box R has twice as many pencils as box Q. "
        "How many pencils are there altogether?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 52


def test_inverse_direction_resolves_a_labeled_standard(full_registry):
    # the subject is known directly, the STANDARD is the labeled entity
    # that must be derived (saturate.py's inverse branch) — the mirror of
    # every test above, where the label sits on the FORWARD side instead.
    r = solve(
        "Jar B has 40 marbles. Jar B has 4 times as many marbles as jar A. "
        "Jar C has 5 marbles. How many marbles are there altogether?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 55


def test_same_label_self_reference_still_declines(full_registry):
    # decline-safety: two mentions of the SAME label ('A' both sides) are
    # the genuine self-referential case every `distinct` guard exists to
    # block — the (lemma, label) widening must not let this through.
    r = solve(
        "Jar A has 5 more marbles than jar A. "
        "How many marbles are there in total?",
        full_registry,
    )
    assert not r.answer.committed


def test_unlabeled_self_reference_regression(full_registry):
    # decline-safety / no-regression: the ORIGINAL bare-lemma self-
    # reference case (no labels at all) must still decline exactly as
    # before this change.
    r = solve(
        "The jar has 5 more marbles than the jar. "
        "How many marbles are there in total?",
        full_registry,
    )
    assert not r.answer.committed


def test_labeled_standard_with_no_matching_quantity_declines(full_registry):
    # decline-safety: a relation names a SPECIFIC labeled standard ('jar
    # B') that is never itself stated anywhere — must decline rather than
    # silently borrowing a DIFFERENT labeled sibling's ('jar A') value.
    r = solve(
        "Jar A has 18 marbles. Jar C has 6 more marbles than jar B. "
        "How many marbles are there in total?",
        full_registry,
    )
    assert not r.answer.committed


def test_plain_unlabeled_relation_is_unaffected(full_registry):
    # regression: an ordinary named (unlabeled) relation resolves exactly
    # as it did before this candidate — subject_label/standard_label
    # default to no-label and never intrude.
    r = solve(
        "Tom has 18 apples. Ann has 6 more apples than Tom. "
        "How many apples are there in total?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 42
