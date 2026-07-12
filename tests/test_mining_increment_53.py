"""Mining candidate commaless-trailing-if: comma-less trailing conditional
clauses ("How old is Mira if Devon is 20 years old?" -- a trailing "if"
clause with NO comma anywhere in the question). `_split_trailing_clause`
(engine.py, increment 12) only ever split at a top-level COMMA whose
following text opens with "if"; it never fired when the "if" clause was
simply appended to the wh-question with no comma at all, so these
questions declined "no ask shape recognizes this question" even though the
premises fully determine the answer.

This candidate adds a comma-less fallback, `_split_trailing_clause_
commaless`: when the existing comma-anchored split finds NOTHING (no
top-level comma+"if" boundary at all), split instead at the LAST ' if '
token boundary of the sentence, strip the trailing '?', and promote the
clause to a premise -- exactly mirroring increment 12's safety property:
the promoted clause must carry a digit, so a bare narrative tail ("...to
see if that works?") is never mis-promoted to a premise. 'if' remains
grammatical skeleton (the identical literal already used by
`_split_leading_clause` and the comma'd trailing form), never a Python word
list. The pre-existing comma path is untouched byte-for-byte: the fallback
only runs when that path returns no split at all.

Synthetic only."""

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


def test_commaless_trailing_if_clause_becomes_a_premise(full_registry):
    text = (
        "Mira has 6 times as many stamps as Devon. "
        "How many more stamps does Mira have than Devon if Devon has 15 stamps?"
    )
    premises, question = split_question(text, full_registry)
    assert premises == [
        "Mira has 6 times as many stamps as Devon.",
        "Devon has 15 stamps.",
    ]
    assert question == "How many more stamps does Mira have than Devon?"


def test_commaless_trailing_if_clause_solves_end_to_end(full_registry):
    text = (
        "Mira has 6 times as many stamps as Devon. "
        "How many more stamps does Mira have than Devon if Devon has 15 stamps?"
    )
    r = solve(text, full_registry)
    assert r.answer.value == 75


def test_comma_anchored_form_still_takes_priority(full_registry):
    # a comma'd trailing "if" tail must still be handled by the pre-
    # existing comma path exactly as before -- the comma-less fallback
    # only runs when that path finds no split at all.
    text = (
        "Mira has 6 times as many stamps as Devon. "
        "How many more stamps does Mira have than Devon, if Devon has 15 stamps?"
    )
    premises, question = split_question(text, full_registry)
    assert premises == [
        "Mira has 6 times as many stamps as Devon.",
        "Devon has 15 stamps.",
    ]
    assert question == "How many more stamps does Mira have than Devon?"


def test_leading_form_still_takes_priority_over_commaless_fallback(full_registry):
    # the leading form ("If X, question?") must still be tried first --
    # this text would ALSO contain a trailing-shaped ' if ' further in, but
    # the leading split fires first and wins.
    text = "If Devon has 15 stamps, how many stamps does Devon have?"
    premises, question = split_question(text, full_registry)
    assert premises == ["Devon has 15 stamps."]
    assert question == "how many stamps does Devon have?"


def test_decline_safety_no_digit_in_commaless_if_tail(full_registry):
    # a comma-less trailing "if" tail with no stated quantity is narrative,
    # not a premise ("wonders if X will happen") -- must not be promoted.
    text = "Does Devon wonder if Mira will come?"
    premises, question = split_question(text, full_registry)
    assert premises == []
    assert question == text


def test_decline_safety_degenerate_leading_if_with_no_wh_part(full_registry):
    # 'if' as the very first word has no leading space before it, so the
    # comma-less fallback's ' if ' token search never matches at position
    # 0 -- there is no wh-part left to ask, so this must decline rather
    # than promote the whole sentence as its own premise. (The leading
    # form is also tried first in split_question and finds no ask-cue
    # comma split here, so control reaches the trailing/fallback path.)
    text = "if 10 stamps are enough?"
    premises, question = split_question(text, full_registry)
    assert premises == []
    assert question == text


def test_last_if_boundary_used_when_multiple_if_tokens_present(full_registry):
    # mirrors the comma'd form's "keep the LAST such boundary" rule: when
    # the sentence contains more than one ' if ' token, the fallback must
    # split at the LAST one, not the first.
    text = "How many berries does Mo have if he decides if he picks 12 berries?"
    premises, question = split_question(text, full_registry)
    assert premises == ["he picks 12 berries."]
    assert question == "How many berries does Mo have if he decides?"


def test_decline_safety_last_if_clause_lacks_digit_even_if_earlier_one_has_it(
    full_registry,
):
    # the digit gate applies to the clause after the LAST ' if ' only --
    # an earlier 'if' clause carrying a digit must not rescue a digit-less
    # final clause into being promoted.
    text = "How many berries does Mo have if he ate 5 if he stops?"
    premises, question = split_question(text, full_registry)
    assert premises == []
    assert question == text


def test_word_containing_if_substring_is_not_a_false_boundary(full_registry):
    # 'differently' contains the letters "if" but is not surrounded by
    # spaces -- the ' if ' token search must not treat it as a marker.
    text = "Does Gifford solve it differently if Mira has 10 stamps?"
    premises, question = split_question(text, full_registry)
    assert premises == ["Mira has 10 stamps."]
    assert question == "Does Gifford solve it differently?"
