"""Increment 28 (fraction-percent-partitions): fraction/percent partitions
("N% / half of them are ADJ|NOUN") — the PREMISE-side counterpart of the
increment-16/17 count-valued partition machinery ("N of them are ADJ/NOUN").
Two new pattern rules emit a PartitionQuantity with `is_fraction=True` and a
raw fraction (0-1) as its value; the existing collection synthesizer
(`synth/partition-of-collection`) resolves the plural-pronoun collection
exactly as before and additionally sizes the fraction against the resolved
collection's own total before re-emitting it as a real count. Reuses the
increment-16/17 consumer (partition-complement) and the membership-count
companion synth unchanged. Synthetic only."""

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


def test_percent_of_them_are_adjective(full_registry):
    r = solve(
        "Tom has 20 apples. 25% of them are red. How many apples are red?",
        full_registry,
    )
    assert r.answer.value == 5


def test_half_of_them_are_adjective(full_registry):
    r = solve(
        "Tom has 20 apples. Half of them are red. How many apples are red?",
        full_registry,
    )
    assert r.answer.value == 10


def test_percent_of_them_are_noun_membership(full_registry):
    r = solve(
        "Tom has 20 pets. 40% of them are dogs. How many dogs does Tom have?",
        full_registry,
    )
    assert r.answer.value == 8


def test_complement_ask_on_fractional_partition(full_registry):
    # "how many are NOT red" takes the exact complement of the resolved
    # count, same consumer as the cardinal form (increment 16/17)
    r = solve(
        "Tom has 20 apples. 25% of them are red. How many apples are not red?",
        full_registry,
    )
    assert r.answer.value == 15


def test_ambiguous_collection_declines(full_registry):
    # two distinct measures known before the partition sentence — the
    # pronoun's collection cannot resolve, same decline discipline as the
    # cardinal form
    r = solve(
        "Tom has 20 apples. Tom has 15 oranges. 25% of them are red. "
        "How many apples are red?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_no_prior_collection_declines(full_registry):
    r = solve(
        "25% of them are red. How many apples are red?",
        full_registry,
    )
    assert r.answer.kind == "decline"
