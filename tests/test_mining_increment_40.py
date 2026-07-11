"""Mining increment 40: wh-copular total asks — "What is/was/'s
the total (number/amount of) ITEM (that) they VERB?" fronts the aggregate
word ('total') instead of trailing it, unlike the existing "how many X ...
in total" ask (ask/how-many-combined). Both route to the SAME unchanged
'combined' consumer (Sigma over every entity holding the resolved measure).
The trailing subject clause is scoped to a bare pronoun ('they') or omitted
entirely; a counted/named subject ("the two have") is out of scope and
either declines (via the pre-existing value-accounting guard, when the
question states an unaccounted count like "the two") or falls back to the
same default-verb ('have') combined fold, never a new code path.
Synthetic only."""

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


def test_what_is_the_total_number_of_bare(full_registry):
    r = solve(
        "Priya has 12 marbles. Suresh has 7 marbles. "
        "What is the total number of marbles?",
        full_registry,
    )
    assert r.answer.value == 19


def test_what_is_the_total_number_of_they_have(full_registry):
    r = solve(
        "Priya has 12 marbles. Suresh has 7 marbles. "
        "What is the total number of marbles they have?",
        full_registry,
    )
    assert r.answer.value == 19


def test_what_was_the_total_amount_of_they_have(full_registry):
    r = solve(
        "Priya has 12 marbles. Suresh has 7 marbles. "
        "What was the total amount of marbles they have?",
        full_registry,
    )
    assert r.answer.value == 19


def test_whats_contraction_total_number_of(full_registry):
    r = solve(
        "Priya has 12 marbles. Suresh has 7 marbles. "
        "What's the total number of marbles they have?",
        full_registry,
    )
    assert r.answer.value == 19


def test_that_clause_variant(full_registry):
    r = solve(
        "Priya has 12 marbles. Suresh has 7 marbles. "
        "What is the total number of marbles that they have?",
        full_registry,
    )
    assert r.answer.value == 19


def test_single_holder_declines(full_registry):
    # decline-safety: a combined ask needs at least TWO holders of the
    # measure — one holder must never silently answer as if plural.
    r = solve(
        "Priya has 12 marbles. What is the total number of marbles she has?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_the_two_subject_does_not_commit_wrong(full_registry):
    # "the two" is a counted/named subject this candidate deliberately
    # scopes out (holder-count logic is out of scope) — it must never
    # commit a WRONG answer, decline is the only acceptable outcome.
    r = solve(
        "Priya has 12 marbles. Suresh has 7 marbles. "
        "What is the total number of marbles the two have?",
        full_registry,
    )
    assert r.answer.kind == "decline"
