"""Attribute-partitioned collections (colour/type-qualified measure
variants) — mining candidate qualified-measure-keys.

Increment 70 (mining candidate qualified-measure-keys, the enabler) already
splits a same-key VALUE conflict between two differently-qualified
Quantity/Price facts into `measure[qualifier]` siblings ("12 white marbles"
vs "6 blue marbles", both bare-folding to measure='marble'). But that
qualifier was a DEAD END: nothing could address the split variants again.
This candidate closes three coupled gaps, one root cause (the qualifier was
never part of the measure KEY anywhere except facts.py's own collision
table):

(a) RELATION RESOLUTION dropped the qualifier entirely. "Owen has 14
    silver coins. Owen has 6 more purple coins than silver coins." bare-
    folds the relation's `item`/`std` slots to the SAME lemma 'coin' —
    patterns.py's `distinct`/`distinct: [item, std]` guard (which exists to
    reject a genuine self-reference, "N fewer STICKERS than STICKERS")
    could not tell that shape apart from two attribute-qualified variants
    of the SAME holder's own measure, and blocked both alike. A new
    qualifier-aware `distinct_measure` where-predicate (patterns.py)
    replaces it on the two comparative-delta relation rules
    (`arithmetic/anchored-relation`/`-postfix`): a same-lemma pair with two
    DIFFERENT non-null qualifiers is let through, carrying its own
    `measure_qualifier`/`standard_qualifier` (new Relation fields,
    saturate.py's same-holder subtype branches) so the derived sibling
    resolves against the SPECIFIC qualified quantity — never an arbitrary
    same-lemma one (a genuine confident-wrong an unrelated THIRD qualified
    sibling would otherwise silently supply, exercised below).

(b) EXISTENTIAL premises ("There are 14 white desks. There are 9 black
    desks.") conflicted instead of splitting — the `arithmetic/existential-
    premise*` rules never carried `measure_qualifier` at all, so facts.py's
    admit-time split (which requires BOTH sides non-null) never engaged.

(c) The BARE-MEASURE ROLL-UP ask ("How many desks are there?" / "How many
    coins does Owen have?") had no consumer to sum qualified siblings back
    together. `_qualified_variant_total` (answer.py) is a new, OPT-IN
    fallback (`sum_measure_variants` on the ask's own `resolves` block —
    `ask/how-many-entity`/`ask/how-many-in-place` only, mirroring increment
    26/19's opt-in flags), fired only once every other lookup has already
    come back empty.

No lexicon anywhere: 'silver'/'purple'/'white'/'black' are never named —
the mechanism is purely structural over the `qualifier` feature the
grammar already extracts (condense.py merge-attribute). Synthetic only.
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


def test_unqualified_relation_is_unaffected(full_registry):
    # regression sanity: two DISTINCT base measures (no qualifiers at all)
    # relation-resolve exactly as before this candidate — the new
    # `distinct_measure` predicate and qualifier propagation never touch
    # this path.
    r = solve(
        "Priya has 20 oranges. Priya has 8 more apples than oranges. "
        "How many apples does Priya have?",
        full_registry,
    )
    assert r.answer.value == 28


def test_qualified_relation_prefix_resolves(full_registry):
    # gap (a), prefix comparative: "N more/fewer ITEM than STD" bare-folds
    # item/std to the SAME lemma 'coin' but carries two DIFFERENT
    # qualifiers — no longer blocked as self-referential.
    r = solve(
        "Owen has 14 silver coins. Owen has 6 more purple coins than "
        "silver coins. How many purple coins does Owen have?",
        full_registry,
    )
    assert r.answer.value == 20


def test_qualified_relation_postfix_resolves(full_registry):
    # gap (a), postfix comparative: "X has N ITEM fewer than STD" — the
    # sibling rule, same qualifier-aware guard.
    r = solve(
        "Dana has 7 purple pens. Dana has 5 white pens fewer than "
        "purple pens. How many white pens does Dana have?",
        full_registry,
    )
    assert r.answer.value == 2


def test_qualified_relation_three_way_chain_resolves(full_registry):
    # a 3+-way qualified chain: once the FIRST pair (red/blue) has already
    # collision-split into 'kite[red]'/'kite[blue]', a THIRD bare-keyed
    # sibling (green, derived from blue) would never collide with either
    # already-bracketed sibling and would silently sit alongside them as
    # an orphan holding unless pre-bracketed — the total must still see
    # all three.
    r = solve(
        "Malik has 10 red kites. Malik has 4 fewer blue kites than red "
        "kites. Malik has 7 more green kites than blue kites. How many "
        "kites does Malik have in total?",
        full_registry,
    )
    assert r.answer.value == 29


def test_existential_qualified_premises_split_and_sum(full_registry):
    # gap (b): two existential premises over the SAME located measure with
    # different qualifiers used to CONFLICT (neither
    # `arithmetic/existential-premise*` rule carried `measure_qualifier`,
    # so facts.py's split never engaged) — now split and (gap (c)) sum.
    r = solve(
        "There are 14 white desks in the office. There are 9 black desks "
        "in the office. How many desks are in the office?",
        full_registry,
    )
    assert r.answer.value == 23


def test_bare_measure_rollup_over_direct_qualified_holdings(full_registry):
    # gap (c): two directly-stated qualified holdings with no bare total
    # and no relation at all — `sum_measure_variants` on ask/how-many-
    # entity sums the qualified siblings once the ordinary bare lookup
    # comes back empty.
    r = solve(
        "Priya has 18 gold coins. Priya has 25 silver coins. "
        "How many coins does Priya have?",
        full_registry,
    )
    assert r.answer.value == 43


def test_qualified_subset_ask_resolves_the_named_variant(full_registry):
    # the ask's OWN item token can carry a qualifier too ("how many SILVER
    # coins") — resolves the SPECIFIC variant directly, never the bare
    # rolled-up total.
    r = solve(
        "Priya has 18 gold coins. Priya has 25 silver coins. "
        "How many silver coins does Priya have?",
        full_registry,
    )
    assert r.answer.value == 25


def test_mismatched_qualifier_ask_declines_safely(full_registry):
    # decline-safety: asking about a qualifier that was never stated must
    # never silently answer with an unrelated sibling's count (or the
    # bare/only fact in play).
    r = solve(
        "Owen has 14 silver coins. How many gold coins does Owen have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_self_referential_relation_still_declines(full_registry):
    # decline-safety: the ORIGINAL guard's own target shape — "N fewer
    # ITEM than ITEM", same lemma AND the same (absent) qualifier on both
    # sides — is a genuine self-reference and must keep declining. The new
    # `distinct_measure` predicate only lets through pairs whose qualifiers
    # actually DIFFER.
    r = solve(
        "Owen has 14 coins. Owen has 6 more coins than coins. "
        "How many coins does Owen have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_unresolvable_qualified_standard_declines_not_borrows(full_registry):
    # decline-safety, the SAME-HOLDER SUBTYPE INVERSE regression this
    # candidate caught mid-development: a relation between two qualified
    # variants of one measure ('yellow'/'orange' spoons) where NEITHER
    # side's value is independently known, alongside an UNRELATED third
    # qualified sibling ('white' spoons) actually stated. Without the
    # qualifier-aware lookup, the inverse branch would silently borrow the
    # white count as if it were the yellow side's own value and derive a
    # confident-wrong 'orange' quantity from it. The qualified lookup
    # correctly finds neither yellow nor orange anywhere and declines
    # instead.
    r = solve(
        "Nadia has 30 fewer yellow spoons than orange spoons. Nadia has "
        "12 white spoons. How many orange spoons does Nadia have?",
        full_registry,
    )
    assert r.answer.kind == "decline"
