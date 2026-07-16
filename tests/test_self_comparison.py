"""A difference ask that resolves both sides to ONE entity is a misreading.

|X - X| is 0 for every X, so a self-comparison can never carry information: it
is always the ask having misread the sentence, never a question whose answer is
0. The `difference` consumer now declines instead of committing that 0.

THE WITNESS IS AN EVENT COMPARATIVE. "He found 6 while he LOST 5. How many more
did he FIND than those he LOST?" compares two events on ONE person, but the
consumer compares two ENTITIES under a single ask_verb — so both slots resolved
to the same person and it committed 0 against a gold of 1. Reading it properly
needs a verb-vs-verb consumer; REFUSING it needs only the observation that the
two sides are the same entity. Precision before coverage: this moves wrong ->
declined, and the capability stays unbuilt and honestly absent.

This is the pattern rules' `distinct: [who, std]` predicate, which asks never
had. Bought by SVAMP (13/2 -> 13/0, 100% precision).

Synthetic only — invented fixtures; the SHAPE is what is pinned.
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


def test_an_event_comparative_declines_rather_than_committing_zero(full_registry):
    """The regression: two events on one person, read as two entities."""
    r = solve(
        "Ravi had 3 stamps in his album. He found 6 stamps while he lost 5 stamps. "
        "How many more stamps did he find than those he lost?",
        full_registry,
    )
    assert r.answer.kind == "decline"
    assert "self-comparison" in r.answer.reason


def test_a_real_two_entity_difference_still_commits(full_registry):
    """The guard must cost the class the consumer exists for: nothing."""
    r = solve(
        "Ann has 5 marbles. Bob has 12 marbles. "
        "How many more marbles does Bob have than Ann?",
        full_registry,
    )
    assert (r.answer.kind, r.answer.value) == ("number", 7.0)


def test_a_genuine_zero_difference_still_commits(full_registry):
    """0 is only meaningless when it comes from comparing X to ITSELF. Two
    DISTINCT entities that happen to be equal is a real question with a real
    answer, and must not be swept up — the guard keys on entity identity, never
    on the value being zero."""
    r = solve(
        "Ann has 5 marbles. Bob has 5 marbles. "
        "How many more marbles does Bob have than Ann?",
        full_registry,
    )
    assert (r.answer.kind, r.answer.value) == ("number", 0.0)
