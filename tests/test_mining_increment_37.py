"""Mining candidate partition-of-noun: definite-NP partitions ("N of the
NOUN are ADJ/NOUN"). Extends increments 16/17's PartitionQuantity machinery
(which matches only the pronoun form "N of THEM are ADJ/NOUN") with a
sibling premise surface where the collection is a plural common noun named
directly ("the marbles") instead of a pronoun. "The" is a SKIPPABLE article
(never a literal in the match), so the pattern is just number-of-plural-
noun-verb-attribute. Because the noun IS the measure, resolution is
trivial: the partition synthesizer's "already names a real measure" branch
fires (or, absent a prior quantity fact at all, the directly-emitted
PartitionQuantity stands on its own — nothing to resolve). The same
partition-complement consumer and membership->Quantity companion synth are
reused unchanged; the only widening is a structural one (both the
unresolved-derivation guard and the membership synth now treat "collection
already names a known measure" as equivalent to "resolved via
synth/partition"), never a per-rule special case. Synthetic only."""

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


def test_direct_partition_answer(full_registry):
    r = solve(
        "There are 20 marbles in a jar. 6 of the marbles are red. "
        "How many marbles are red?",
        full_registry,
    )
    assert r.answer.value == 6


def test_complement_answer(full_registry):
    r = solve(
        "There are 20 marbles in a jar. 6 of the marbles are red. "
        "How many marbles are not red?",
        full_registry,
    )
    assert r.answer.value == 14


def test_membership_partition_answers_entity_less_ask(full_registry):
    r = solve(
        "There are 20 animals. 8 of the animals are dogs. How many dogs are there?",
        full_registry,
    )
    assert r.answer.value == 8


def test_no_partition_premise_declines(full_registry):
    # the ask shape exists but no partition fact backs the asked attribute
    r = solve(
        "There are 20 marbles. How many marbles are red?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_ambiguous_total_declines_the_complement_only(full_registry):
    # two entities hold the same measure — the complement needs a SINGLE
    # total and must decline, but the directly-named part still resolves
    # (unlike the pronoun form, naming the collection noun directly is
    # never itself ambiguous — only the whole-total needed for a complement
    # can be)
    r_complement = solve(
        "Tom has 12 marbles. Sam has 8 marbles. 6 of the marbles are red. "
        "How many marbles are not red?",
        full_registry,
    )
    assert r_complement.answer.kind == "decline"
    r_direct = solve(
        "Tom has 12 marbles. Sam has 8 marbles. 6 of the marbles are red. "
        "How many marbles are red?",
        full_registry,
    )
    assert r_direct.answer.value == 6


def test_ambiguous_holder_declines_membership_companion(full_registry):
    # two entities both hold the collection's measure — the collection
    # NAME still resolves trivially ("animal"), but the companion Quantity
    # must NOT guess which holder the subset belongs to
    r = solve(
        "Tom has 12 animals. Sam has 8 animals. 8 of the animals are dogs. "
        "How many dogs are there?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_pronoun_partition_unaffected_by_noun_form(full_registry):
    # the pre-existing pronoun form ("N of THEM are ADJ") still fires
    # unchanged alongside the new definite-NP form — mutually exclusive
    # word senses (pronoun vs. plural noun) never double-fire on the same
    # text
    r = solve(
        "There are 20 marbles. Ten of them are red. How many marbles are red?",
        full_registry,
    )
    assert r.answer.value == 10
