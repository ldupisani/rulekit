"""Attribute-qualified MEASURE identity — "1 red shirt for $32 and 3 blue
shirts at $27 each" folds BOTH variants to the bare measure lemma 'shirt'
(condense.py's merge-attribute doesn't touch the noun's own `lemma`
feature), so two differently-qualified holdings/prices of the same bare
noun collide as one fact-store key and decline the whole item ("conflict:
fold and fold disagree").

Mechanism: a kernel-structural mirror of increment 25 (owner) / 34
(entity-qualifier), swapping WHICH key the qualifier disambiguates — the
MEASURE (Quantity.measure / Price.item), not the entity/holder. Measure
identity stays the bare lemma everywhere it already worked (Quantity.measure
and Price.item are unchanged, so plain unqualified folding is untouched). A
new `measure_qualifier` field on Quantity and `qualifier` field on Price
(condense.py's merge-attribute tags the counted/priced noun; learn.py
copies it onto the fact) are read ONLY by FactStore.admit's collision
handling: a same-key VALUE conflict between two facts with two DIFFERENT
non-null measure qualifiers is not a genuine disagreement — it is two
measures the bare lemma alone can't distinguish — so both re-key to
measure[qualifier] (or item[qualifier]) and admit separately instead of
quarantining. NO consumer change: the increment-10 purchase-total consumer
already matches Quantity.measure against Price.item, so once both sides
re-key identically, qualified-price purchase totals resolve with no new
code path.

A null-vs-non-null pairing (a collection total vs. one named subset, e.g.
"20 marbles" then "12 white marbles") is NOT a naming collision — it is a
genuine part/whole relation and must keep declining (needs rest-partition
machinery, a separate candidate, to ever resolve). That guard alone is not
enough when the total uses a DIFFERENT verb/occurrence than its qualified
parts ("collected 40 total ... found 9 grey, 6 black, 15 brown, and 10
gold"): the total's key never even collides with the parts' key, so a
chain of 3+ mutually-different-qualifier parts can pairwise-split itself
completely clean, leaving the untouched bare total looking like an
uncontested, independent holding — a confident wrong caught on dev-holdout
during development (item id withheld; this test reproduces the class with
fresh names/numbers/nouns). The fix generalizes the null-vs-non-null
invariant across the WHOLE store, not just the colliding pair: a split is
refused whenever ANY other already-admitted fact for the same entity/item
shares the bare measure with a null qualifier. Synthetic only.
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


def test_qualified_purchase_total_resolves(full_registry):
    # the payoff class: two differently-qualified purchase variants both
    # fold to the bare measure/item ('hat') — without the split this
    # collides and declines the whole total; with it, the pre-existing
    # increment-10 purchase-total consumer sums 1*15 + 4*9 unchanged.
    r = solve(
        "Maria buys one purple hat for $15 and four green hats at $9 each. "
        "How much does Maria spend in total?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 51


def test_bare_total_alongside_qualified_subset_still_declines(full_registry):
    # a stated collection total, SAME verb as its qualified subsets, is a
    # genuine part/whole relation (null-vs-non-null qualifier) — must keep
    # declining, not silently re-key.
    r = solve(
        "Priya has 30 pebbles. She has 9 red pebbles and 5 orange pebbles. "
        "How many pebbles does Priya have?",
        full_registry,
    )
    assert not r.answer.committed


def test_bare_total_different_verb_from_qualified_parts_still_declines(full_registry):
    # the regression this candidate caught mid-development: a total stated
    # with a DIFFERENT verb from its 4-way qualified breakdown must not let
    # the breakdown's clean pairwise splits launder the store into looking
    # uncontested — the whole item must still decline.
    r = solve(
        "Marcus collected 40 stones in total. He found 9 grey stones, "
        "6 black stones, 15 brown stones, and 10 gold stones. "
        "How many stones did Marcus collect in total?",
        full_registry,
    )
    assert not r.answer.committed


def test_split_without_wired_ask_still_declines_safely(full_registry):
    # the split itself is scoped to fact ADMISSION only (no consumer
    # change): two qualified state-quantities split cleanly (no collision)
    # but a question asking for ONE qualified subset has no consumer wired
    # to read `measure_qualifier` yet, so it must decline rather than guess
    # — never silently answer with the bare, unqualified-ask total either.
    r = solve(
        "Nadia has 12 red marbles and 5 green marbles. "
        "How many red marbles does Nadia have?",
        full_registry,
    )
    assert not r.answer.committed


def test_unqualified_folding_is_unaffected(full_registry):
    # decline-safety / no-regression: a plain unqualified holding, no
    # attributive modifier anywhere, must still answer exactly as before
    # this change (measure_qualifier is None throughout, so the new branch
    # never fires and never touches the ordinary single-fact fold).
    r = solve(
        "Owen has 7 shells. How many shells does Owen have?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 7
