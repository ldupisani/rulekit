"""Increment 16: partitioned collections ("N of them are ADJ" premises) +
adjective-qualified count asks ("how many NOUN are (not) ADJ"). A new
PartitionQuantity fact captures a stated subset of a prior collection; the
plural pronoun ('them') resolves against the unique prior collection fact
via the same unique-pool-in-play principle fraction-of-pronoun already uses
(never document-level pronoun binding, which deliberately excludes plural
pronouns). A new complement consumer answers the named subset directly, or
its EXACT complement (total minus that subset — never an exhaustive-
enumeration assumption) only when the collection's total resolves to a
single holder. Synthetic only."""

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
        "There are 20 marbles. Ten of them are red. How many marbles are red?",
        full_registry,
    )
    assert r.answer.value == 10


def test_complement_answer(full_registry):
    r = solve(
        "There are 20 marbles. Ten of them are red. How many marbles are not red?",
        full_registry,
    )
    assert r.answer.value == 10


def test_complement_uses_exact_total_not_enumeration(full_registry):
    # 30 total, 12 are red — "not red" is exactly 18 regardless of how many
    # OTHER colors exist among them (never an exhaustive-enumeration guess)
    r = solve(
        "There are 30 marbles. Twelve of them are blue. How many marbles are not blue?",
        full_registry,
    )
    assert r.answer.value == 18


def test_no_partition_premise_declines(full_registry):
    # the ask shape exists but no partition fact backs the asked attribute
    r = solve(
        "There are 20 marbles. How many marbles are red?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_ambiguous_collection_declines(full_registry):
    # two prior collections in play ("marbles" and "books") — 'them' cannot
    # resolve to a unique pool, so the partition stays unresolved and the
    # guard vetoes ANY commit in the document (definitive-or-decline)
    r = solve(
        "There are 20 marbles. There are 15 books. Ten of them are red. "
        "How many books are there?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_ambiguous_total_declines_the_complement_only(full_registry):
    # two entities hold the same measure — the complement needs a SINGLE
    # total and must decline, but the directly-named part still resolves
    r_complement = solve(
        "Tom has 12 marbles. Sam has 8 marbles. Ten of them are red. "
        "How many marbles are not red?",
        full_registry,
    )
    assert r_complement.answer.kind == "decline"
    r_direct = solve(
        "Tom has 12 marbles. Sam has 8 marbles. Ten of them are red. "
        "How many marbles are red?",
        full_registry,
    )
    assert r_direct.answer.value == 10
