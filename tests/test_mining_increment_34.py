"""Attribute-qualified entity identity — "The coconut tree has 12 branches.
The mango tree has 8 branches." both fold to the bare noun lemma 'tree'
(condense.py's merge-attribute / merge-compound don't touch the noun's own
`lemma` feature), so two DIFFERENT modifier-qualified holdings of the same
noun collide as one fact-store entity and decline the whole item
("conflict: fold and fold disagree").

Mechanism: a kernel-structural mirror of increment 25 (possessive-qualified
entity identity), swapping the qualifier's SOURCE from possessive 's to an
attributive modifier. Entity identity stays the bare lemma everywhere it
already worked (Quantity.entity is unchanged, so "the tree ... it ..."
keeps folding into one entity exactly as before). A NEW `qualifier` field
on Quantity (condense.py's merge-attribute / merge-compound tags the
merged noun with its modifier's lemma; learn.py copies it onto the fact,
independently of `owner`) is read ONLY by FactStore.admit's collision
handling: a same-key VALUE conflict between two Quantity facts with two
DIFFERENT non-null qualifiers is not a genuine disagreement — it is two
entities the bare lemma alone can't distinguish — so both re-key to
entity[qualifier] and admit separately instead of quarantining. A new ask
id (ask/how-many-entity-qualified, gated on a new `qualified` slot type
that requires the noun to carry a qualifier) resolves an attribute-
qualified subject the same way, with a qualifier-scoped fallback in the
single-entity consumer so a bare (non-conflicting) holding can still
answer, but never across a different NAMED modifier (increment-26
discipline: never borrow a sibling's number). Synthetic only.
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


def test_two_qualified_same_noun_no_longer_conflict(full_registry):
    r = solve(
        "The coconut tree has 12 apples. The mango tree has 8 apples. "
        "How many apples does the coconut tree have?",
        full_registry,
    )
    assert r.answer.value == 12
    assert r.answer.kind == "number"


def test_the_other_qualifier_resolves_independently(full_registry):
    r = solve(
        "The coconut tree has 12 apples. The mango tree has 8 apples. "
        "How many apples does the mango tree have?",
        full_registry,
    )
    assert r.answer.value == 8


def test_cross_mention_coreference_still_folds(full_registry):
    # a possessive/attribute-qualified subject introduced ONCE, then
    # referred to by a BARE noun of the same lemma in a LATER sentence, must
    # still accumulate as the SAME entity via the ordinary event fold (no
    # qualifier conflict ever arises here — the two facts have DIFFERENT
    # `occurrence` indices, so they never collide at the same key at all;
    # this only regresses if the new `qualifier` field somehow disturbed
    # the untouched entity-identity or event-accumulation paths).
    r = solve(
        "The coconut tree found 5 apples. The tree found 3 apples. "
        "How many apples are there?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 8


def test_unmentioned_qualifier_declines_not_borrows(full_registry):
    # decline-safety: only ONE modifier's holding is ever stated (coconut) —
    # a question about a DIFFERENT, never-mentioned modifier's same-noun
    # entity must decline, never silently answer with the coconut tree's
    # number just because the bare lemma never collided.
    r = solve(
        "The coconut tree has 12 apples. "
        "How many apples does the mango tree have?",
        full_registry,
    )
    assert not r.answer.committed
