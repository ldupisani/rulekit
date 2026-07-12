"""Mining candidate average-asks: "What is/was/'s the average (number/amount)
of ITEM (that) they VERB?" — the average sibling of ask/what-total-combined
(increment 40). IDENTICAL shape, 'average' fronting instead of 'total',
routed to a NEW 'average' consumer (answer.py) that reuses the 'combined'
consumer's own holder-enumeration helper UNCHANGED (Sigma over every entity
holding the resolved measure, >=2-holders-or-decline, same state/event-verb
fallback) and divides by the holder count. No new fact kind. 'average' is
now lexiconed with sense 'aggregate' (moved from difg-mined, alongside
'total'/'combined') so condense.py's general NOUN+NOUN merge-compound pass
never eats it into an "average number" compound before the ask pattern sees
a separate 'average' token. Synthetic only."""

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


def test_what_is_the_average_number_of_they_scored(full_registry):
    r = solve(
        "Nadia scored 14 points. Omar scored 22 points. "
        "What is the average number of points they scored?",
        full_registry,
    )
    assert r.answer.value == 18


def test_what_was_the_average_amount_of_they_have(full_registry):
    r = solve(
        "Nadia has 14 marbles. Omar has 22 marbles. "
        "What was the average amount of marbles they have?",
        full_registry,
    )
    assert r.answer.value == 18


def test_whats_contraction_average_number_of(full_registry):
    r = solve(
        "Nadia has 10 marbles. Omar has 20 marbles. "
        "What's the average number of marbles they have?",
        full_registry,
    )
    assert r.answer.value == 15


def test_that_clause_variant(full_registry):
    r = solve(
        "Nadia has 10 marbles. Omar has 20 marbles. "
        "What is the average number of marbles that they have?",
        full_registry,
    )
    assert r.answer.value == 15


def test_three_holders_non_integer_average(full_registry):
    r = solve(
        "Nadia caught 4 fish. Omar caught 5 fish. Priya caught 9 fish. "
        "What is the average number of fish they caught?",
        full_registry,
    )
    assert r.answer.value == 6


def test_the_two_subject_does_not_commit_wrong(full_registry):
    # "the two" is a counted/named subject this candidate deliberately
    # scopes out (holder-count logic is out of scope, mirrors what-total-
    # combined's own scoping) — it must never commit a WRONG answer,
    # decline is the only acceptable outcome.
    r = solve(
        "Nadia has 10 marbles. Omar has 20 marbles. "
        "What is the average number of marbles the two have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_single_holder_declines(full_registry):
    # decline-safety: an average ask needs at least TWO holders of the
    # measure — one holder must never silently divide by one.
    r = solve(
        "Nadia has 10 marbles. What is the average number of marbles she has?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_weighted_rate_average_declines(full_registry):
    # decline-safety: a per-unit rate average ("average speed ... per
    # hour") is out of class — no >=2 named holders of the asked measure
    # exist to enumerate, so the reused 'combined' holder gate declines it
    # rather than dividing an unrelated single value.
    r = solve(
        "A car travels 240 miles in 4 hours. "
        "What is the average speed of the car in miles per hour?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_bare_average_without_frame_noun_declines(full_registry):
    # "average of ITEM" with no 'number'/'amount' frame noun in between:
    # the item slot must bind a noun directly after the literal, and 'of'
    # is not one — declines rather than mis-binding.
    r = solve(
        "Nadia has 10 marbles. Omar has 20 marbles. "
        "What is the average of marbles they have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_total_combined_ask_unaffected(full_registry):
    # ask/what-total-combined (increment 40) must still resolve unchanged
    # — 'average' and 'total' are mutually exclusive literals, never a
    # specificity contest between the two sibling asks.
    r = solve(
        "Nadia has 10 marbles. Omar has 20 marbles. "
        "What is the total number of marbles they have?",
        full_registry,
    )
    assert r.answer.value == 30
