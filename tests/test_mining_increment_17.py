"""Increment 17: membership partitions ("N of them are NOUN"). Extends
increment 16's PartitionQuantity machinery (adjective
form: "N of them are ADJ") with a MEMBERSHIP form where the subset label is
a plural common noun ("8 of them are dogs") rather than an adjective. The
plural pronoun resolves against the unique prior collection exactly as
before (same synthesizer, same unique-pool-in-play principle, same
ambiguous-collection decline discipline). The new part is a companion synth
step: once the collection resolves, a membership-kind partition ALSO
synthesizes a Quantity for the named subset noun — but only when the
resolved collection's measure has exactly one holding entity — so the
EXISTING general entity-less "how many NOUN are there" ask answers it
directly, with no bespoke consumer. Synthetic only."""

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


def test_membership_partition_answers_entity_less_ask(full_registry):
    r = solve(
        "There are 20 pets. 8 of them are dogs. How many dogs are there?",
        full_registry,
    )
    assert r.answer.value == 8


def test_membership_partition_resolves_against_named_holder(full_registry):
    # the collection's holder is a NAME, not the bare 'world' existential —
    # the companion Quantity must attach to Tom, not silently drop the
    # holder, and the general entity-less ask still answers it
    r = solve(
        "Tom has 20 pets. 8 of them are dogs. How many dogs are there?",
        full_registry,
    )
    assert r.answer.value == 8


def test_no_membership_partition_premise_declines(full_registry):
    # the ask shape exists but no partition fact backs the asked noun
    r = solve(
        "There are 20 pets. How many dogs are there?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_ambiguous_collection_declines(full_registry):
    # two prior collections in play ("pets" and "toys") — 'them' cannot
    # resolve to a unique pool, so the partition stays unresolved and the
    # guard vetoes ANY commit in the document (definitive-or-decline)
    r = solve(
        "There are 20 pets. There are 15 toys. 8 of them are dogs. "
        "How many dogs are there?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_ambiguous_holder_declines(full_registry):
    # two entities both hold the collection's measure — the collection
    # NAME still resolves uniquely ("pet"), but the companion Quantity must
    # NOT guess which holder the subset belongs to, so it declines rather
    # than attach to an arbitrary one
    r = solve(
        "Tom has 12 pets. Sam has 8 pets. 8 of them are dogs. "
        "How many dogs are there?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_adjective_partition_unaffected_by_membership_rule(full_registry):
    # the pre-existing adjective form ("N of them are ADJ") still fires
    # unchanged alongside the new noun form — the two pattern rules gate on
    # mutually exclusive word senses, never double-fire on the same text
    r = solve(
        "There are 20 marbles. Ten of them are red. How many marbles are red?",
        full_registry,
    )
    assert r.answer.value == 10
