"""Mining increment 73: "the rest are X" remainder partitions cashed in
against attribute-qualified how-many asks, built on top of the parked
qualified-measure-keys enabler (increment 70).

Carries forward the rest-partition premise machinery (two pattern rules,
arithmetic/partition-rest-attribute and arithmetic/partition-rest-membership,
keying on the REST determiner instead of a number/fraction slot, and the
`_partition_synth` sizing extension in saturate.py that resolves an
`is_rest=True` PartitionQuantity to the collection's total minus the signed
sum of every already-resolved sibling partition, once every sibling has
itself resolved). That machinery alone measured ZERO net SOLVED against
main: the fact chain resolves correctly, but no existing ASK SHAPE reads a
resolved PartitionQuantity when the attribute sits PRENOMINAL ("how many
GREY cats are in this house?") instead of postfix ("how many cats are
grey?", the only form ask/how-many-partition matches).

This candidate closes that ask-shape gap with two new, general asks:

- ask/how-many-attribute-partition-in-place ("how many ADJ NOUN
  verb prep place") and
- ask/how-many-attribute-partition-there ("how many ADJ NOUN verb there")

Both use a `type: qualified` item slot — condense.py's merge-attribute
already fuses ADJECTIVE+NOUN into ONE unit before asks ever run (the same
convention ask/how-many-entity-qualified relies on for its subject), so
`item.qualifier` reads the fused modifier directly; there is no separate
adjective token left to match. Both route to the existing
partition-complement consumer, unchanged. Because a `qualified` item is a
strict subset of the generic asks' bare `type: noun` item, and merge
already collapsed the modifier into the same single unit either way (no
extra token to out-consume the generic ask with), patterns.match_ask's tie
(equal consumed-unit counts) is broken by its own documented id-sort-order
mechanism: both new ids are spelled to sort before their generic
siblings ("...-attribute-..." before "...-in-place"/"...-there").

Also fixes a pre-existing bug this class tripped over (batch 26 free
finding #2): `_partition_membership_synth`'s companion Quantity for a
resolved membership partition's subset noun ("5 of them are dogs" ->
Quantity(measure='dog', ...), so the general entity-less "how many dogs"
ask can read it) used to count as a candidate collection measure in
`_partition_synth`'s own unique-pool-in-play scan, so a LATER pronoun/
remnant in the same document saw two distinct measures in play and
permanently failed to resolve. Now excluded by source, mirroring
`_pool_before`'s existing `synth/rest` exclusion.

The bare-total-vs-qualified-subset collision ("Eric has 20 marbles. He has
12 white marbles...") is explicitly NOT resolved by this candidate or by
the enabler it rides on — increment 70 deliberately declines to re-key a
null-vs-non-null qualifier pair (a genuine part/whole relation, not a
naming collision), so that shape keeps declining safely. Synthetic only."""

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


def test_rest_attribute_complement_of_two_partitions(full_registry):
    r = solve(
        "There are 24 birds. 3 of them are red. 5 of them are blue. "
        "The rest are yellow. How many birds are yellow?",
        full_registry,
    )
    assert r.answer.value == 16


def test_rest_attribute_of_named_collection(full_registry):
    # "the rest OF THE BIRDS are yellow" — the optional named-collection
    # span is consumed but never bound into `collection`, so it resolves
    # through the same unique-pool-in-play step as the bare surface.
    r = solve(
        "There are 24 birds. 3 of them are red. "
        "The rest of the birds are yellow. How many birds are yellow?",
        full_registry,
    )
    assert r.answer.value == 21


def test_rest_membership_complement(full_registry):
    r = solve(
        "There are 40 animals. 6 of them are small. The rest are cats. "
        "How many cats are there?",
        full_registry,
    )
    assert r.answer.value == 34


def test_rest_attribute_feeds_negated_complement_ask(full_registry):
    # "how many are NOT yellow" — the general partition-complement consumer
    # takes the exact complement of the resolved rest partition itself,
    # same as it already does for a stated cardinal partition.
    r = solve(
        "There are 24 birds. 3 of them are red. 5 of them are blue. "
        "The rest are yellow. How many birds are not yellow?",
        full_registry,
    )
    assert r.answer.value == 8


def test_rest_with_no_prior_partition_declines(full_registry):
    # "the rest" names the EXACT COMPLEMENT of the STATED subsets — with
    # none stated, committing the whole collection risks a confident wrong
    # whenever some other, non-partition subset exists in the text that
    # this general mechanism can't see. Decline rather than assume "the
    # rest" is everything.
    r = solve(
        "There are 24 birds. The rest are yellow. How many birds are yellow?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_rest_over_subtraction_declines(full_registry):
    # siblings sum past the collection's own total — an inconsistent
    # premise; decline rather than commit a negative count.
    r = solve(
        "There are 10 marbles. 4 of them are red. 8 of them are blue. "
        "The rest are yellow. How many marbles are yellow?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_rest_ambiguous_collection_declines(full_registry):
    # two distinct measures known before the rest partition's sentence —
    # same decline discipline as the cardinal/fractional pronoun forms.
    r = solve(
        "There are 20 marbles. There are 15 books. 4 of them are red. "
        "The rest are green. How many marbles are green?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_qualified_partition_in_place_ask_prenominal_attribute(full_registry):
    # ask/how-many-attribute-partition-in-place: the attribute sits BEFORE
    # the noun ("how many YELLOW birds"), not after a copula — the ask
    # shape gap this candidate closes. Two prior attribute partitions plus
    # a rest, all resolved by the carried-forward machinery above; only
    # the ASK was missing.
    r = solve(
        "There are 30 birds in the garden. 6 of them are red, and 9 of them "
        "are blue. The rest of the birds are yellow. "
        "How many yellow birds are in the garden?",
        full_registry,
    )
    assert r.answer.value == 15


def test_qualified_partition_there_ask_prenominal_attribute(full_registry):
    # ask/how-many-attribute-partition-there: the entity-less sibling —
    # "how many ADJ NOUN are there?" with no place named.
    r = solve(
        "There are 20 marbles. 5 of them are red. "
        "The rest are green. How many green marbles are there?",
        full_registry,
    )
    assert r.answer.value == 15


def test_qualified_partition_in_place_does_not_shadow_bare_item_ask(full_registry):
    # Non-regression: an UNQUALIFIED item ("how many birds are in this
    # garden?") must still resolve through the ordinary
    # ask/how-many-in-place + single-entity consumer path, unaffected by
    # the new qualified-only sibling ask (a `type: qualified` item never
    # matches a bare noun, so it simply fails to match here).
    r = solve(
        "There are 12 birds in the garden. How many birds are in the garden?",
        full_registry,
    )
    assert r.answer.value == 12


def test_qualified_partition_in_place_declines_without_resolved_partition(full_registry):
    # The new ask still routes through the SAME partition-complement
    # consumer, which declines when the named attribute never resolved to
    # a partition fact at all — never guesses from the bare collection.
    r = solve(
        "There are 30 birds in the garden. "
        "How many purple birds are in the garden?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_sequential_membership_partitions_no_longer_mutually_pollute(full_registry):
    # Batch 26 free finding #2: a resolved membership partition's
    # companion Quantity ("5 of them are dogs" -> Quantity(measure='dog'))
    # used to count as a second candidate collection measure, so a LATER
    # rest/pronoun partition in the same document saw an ambiguous
    # unique-pool-in-play scan and never resolved. Fixed in
    # `_partition_synth`'s `_candidate_measure` helper.
    r = solve(
        "There are 20 animals. 5 of them are dogs. The rest are cats. "
        "How many cats are there?",
        full_registry,
    )
    assert r.answer.value == 15
