"""Possessive-qualified entity identity — "Kennedy's house has 5 rooms.
Benedict's house has 3 rooms." both fold to the bare noun lemma 'house'
(condense.py's merge-possessive doesn't touch the noun's own `lemma`
feature), so two DIFFERENT possessors' same-noun holdings collide as one
fact-store entity and decline the whole item ("conflict: fold and fold
disagree").

Mechanism: entity identity stays the bare lemma everywhere it already
worked (Quantity.entity is unchanged, so "Tom's dog ... the dog ..."
keeps folding into one entity exactly as before). A NEW `owner` field on
Quantity (condense.py tags the merged noun; learn.py copies it onto the
fact) is read ONLY by FactStore.admit's collision handling: a same-key
VALUE conflict between two Quantity facts with two DIFFERENT non-null
owners is not a genuine disagreement — it is two entities the bare lemma
alone can't distinguish — so both re-key to entity[owner] and admit
separately instead of quarantining. A new ask id
(ask/how-many-entity-possessed, gated on a new `possessed` slot type that
requires the noun to carry an owner) resolves a possessive-qualified
subject the same way, with an owner-scoped fallback in the single-entity
consumer so a bare (non-conflicting) holding can still answer, but never
across a different NAMED owner. Synthetic only.
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


def test_two_possessors_same_noun_no_longer_conflict(full_registry):
    r = solve(
        "Kennedy's house has 5 rooms. Benedict's house has 3 rooms. "
        "How many rooms does Kennedy's house have?",
        full_registry,
    )
    assert r.answer.value == 5
    assert r.answer.kind == "number"


def test_the_other_possessor_resolves_independently(full_registry):
    r = solve(
        "Kennedy's house has 5 rooms. Benedict's house has 3 rooms. "
        "How many rooms does Benedict's house have?",
        full_registry,
    )
    assert r.answer.value == 3


def test_cross_mention_coreference_still_folds(full_registry):
    # a possessive introduced ONCE, then referred to by a bare noun in a
    # LATER sentence, must still be treated as the SAME entity (no owner
    # conflict ever arose here, so entity identity stays untouched, bare,
    # exactly as before this change) — a regression this candidate's first
    # attempt actually introduced and had to be walked back.
    #
    # Asserted at the STORE, not the answer: both events must fold onto
    # the one bare 'dog' entity. This test used to accept the committed
    # ANSWER (abs(value) == 8 — the fold's anchorless events-only -8),
    # but that commit was itself the negative-holdings artifact
    # `_entity_total`'s anchor guard now refuses, and blessing it with
    # abs() was always a smell. Coreference is provable without it.
    from rulekit.kernel.model import Quantity

    r = solve(
        "Tom's dog ate 5 apples. The dog ate 3 apples. "
        "How many apples are there?",
        full_registry,
    )
    dog_events = sorted(
        q.value for q in r.store.by_kind(Quantity)
        if q.entity == "dog" and q.measure == "apple"
    )
    assert dog_events == [3.0, 5.0], (
        f"coreference broke — dog/apple events are {dog_events}"
    )
    # the answer itself now DECLINES: an anchorless events-only fold
    # summing negative is the unstated-prior-holdings class, not a count.
    assert not r.answer.committed


def test_unmentioned_possessor_declines_not_borrows(full_registry):
    # decline-safety: only ONE owner's holding is ever stated (Kennedy's) —
    # a question about a DIFFERENT, never-mentioned owner's same-noun
    # entity must decline, never silently answer with Kennedy's number
    # just because the bare lemma never collided.
    r = solve(
        "Kennedy's house has 5 rooms. How many rooms does Benedict's house have?",
        full_registry,
    )
    assert not r.answer.committed
