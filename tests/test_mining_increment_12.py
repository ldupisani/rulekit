"""Trailing conditional-clause questions ("...question, if X has N?"): the
question sentence embeds a trailing "if" clause AFTER the wh-part instead of
before it. `_split_leading_clause` (engine.py) only handled the LEADING
form ("If X, question?"); this candidate adds `_split_trailing_clause`, a
mirror that splits at the LAST top-level comma whose following text starts
with the conditional marker "if", strips the trailing "?", and promotes the
clause to a premise sentence ahead of the wh-question -- purely structural
sentence-splitting before any grammar/obligation processing, gated on the
clause containing a number (appositives / "in total, ..." tails never do,
so they are never mis-promoted to a premise). Synthetic only."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import solve, split_question

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def full_registry():
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", mined])
    )


def test_trailing_if_clause_becomes_a_premise(full_registry):
    text = (
        "Anna has 4 times as many marbles as Carl. "
        "How many more marbles does Anna have than Carl, if Carl has 20 marbles?"
    )
    premises, question = split_question(text, full_registry)
    assert premises == [
        "Anna has 4 times as many marbles as Carl.",
        "Carl has 20 marbles.",
    ]
    assert question == "How many more marbles does Anna have than Carl?"


def test_trailing_if_clause_solves_end_to_end(full_registry):
    text = (
        "Anna has 4 times as many marbles as Carl. "
        "How many more marbles does Anna have than Carl, if Carl has 20 marbles?"
    )
    r = solve(text, full_registry)
    assert r.answer.value == 60


def test_leading_form_still_takes_priority(full_registry):
    # the pre-existing leading form must still split exactly as before --
    # the new trailing branch only runs when the leading split finds nothing.
    text = (
        "Anna has 4 times as many marbles as Carl. "
        "If Carl has 20 marbles, how many more marbles does Anna have than Carl?"
    )
    premises, question = split_question(text, full_registry)
    assert premises == [
        "Anna has 4 times as many marbles as Carl.",
        "Carl has 20 marbles.",
    ]
    assert question == "how many more marbles does Anna have than Carl?"


def test_decline_safety_no_number_in_trailing_clause(full_registry):
    # a trailing ", if ..." tail with no number is never promoted to a
    # premise (it is not a stated fact) -- the question is left untouched
    # rather than risk folding a bare non-numeric clause as a premise.
    text = "How many candies remain, if any are left over?"
    premises, question = split_question(text, full_registry)
    assert premises == []
    assert question == text


def test_decline_safety_non_conditional_trailing_comma(full_registry):
    # an ordinary trailing appositive/tail that happens to follow a comma
    # but does not start with "if" must not be split at all.
    text = "How many apples does Sam have in total, after eating three?"
    premises, question = split_question(text, full_registry)
    assert premises == []
    assert question == text
