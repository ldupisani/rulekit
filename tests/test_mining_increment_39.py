"""Leading temporal-clause questions ("After/When X, question?"): the
question sentence embeds a leading dependent clause introduced by a
temporal subordinator instead of the conditional 'if'. `_split_leading_clause`
(engine.py) only recognized the literal 'if' marker; this candidate adds
`_split_leading_temporal_clause`, a sibling that recognizes 'when'/'after'
via category membership (packs/difg-mined/categories/clauses.yaml's
'clause_marker'/'clause_marker_prep' categories — never a Python word list)
and splits the clause into a premise ahead of the wh-question, exactly like
the 'if' form but gated (mirroring increment 12's trailing-if safety
property) on the clause containing a digit, so a bare narrative marker with
no stated quantity is never mis-promoted to a premise. Synthetic only."""

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


def test_leading_after_clause_becomes_a_premise(full_registry):
    text = (
        "Priya has 9 shells. "
        "After Priya finds 4 shells, how many shells does Priya have?"
    )
    premises, question = split_question(text, full_registry)
    assert premises == [
        "Priya has 9 shells.",
        "Priya finds 4 shells.",
    ]
    assert question == "how many shells does Priya have?"


def test_leading_when_clause_becomes_a_premise(full_registry):
    text = (
        "Priya has 9 shells. "
        "When Priya finds 4 shells, how many shells does Priya have?"
    )
    premises, question = split_question(text, full_registry)
    assert premises == [
        "Priya has 9 shells.",
        "Priya finds 4 shells.",
    ]
    assert question == "how many shells does Priya have?"


def test_leading_after_clause_solves_end_to_end(full_registry):
    text = (
        "Priya has 9 shells. "
        "After Priya finds 4 shells, how many shells does Priya have?"
    )
    r = solve(text, full_registry)
    assert r.answer.value == 13


def test_leading_when_clause_solves_end_to_end(full_registry):
    text = (
        "Priya has 9 shells. "
        "When Priya finds 4 shells, how many shells does Priya have?"
    )
    r = solve(text, full_registry)
    assert r.answer.value == 13


def test_if_clause_still_takes_priority(full_registry):
    # the pre-existing 'if' leading form must still split exactly as before
    # -- the new temporal branch only runs when the 'if' split finds nothing.
    text = (
        "Priya has 9 shells. "
        "If Priya finds 4 shells, how many shells does Priya have?"
    )
    premises, question = split_question(text, full_registry)
    assert premises == [
        "Priya has 9 shells.",
        "Priya finds 4 shells.",
    ]
    assert question == "how many shells does Priya have?"


def test_no_question_mark_imperative_form_still_splits(full_registry):
    # "When she finds 4 shells, calculate her total." -- no '?' and no
    # leading interrogative cue, but the post-comma part leads with one
    # (mirrors the 'if' imperative-form precedent in split_question).
    text = (
        "Priya has 9 shells. "
        "When Priya finds 4 shells, calculate how many shells Priya has."
    )
    premises, question = split_question(text, full_registry)
    assert premises == [
        "Priya has 9 shells.",
        "Priya finds 4 shells.",
    ]
    assert question == "calculate how many shells Priya has."


def test_decline_safety_no_digit_in_temporal_clause(full_registry):
    # a bare narrative "When/After ..." clause with no stated quantity is
    # never promoted to a premise (it is not a stated fact) -- the question
    # is left untouched rather than risk folding a non-premise clause in.
    text = "When the party ends, how many candies remain?"
    premises, question = split_question(text, full_registry)
    assert premises == []
    assert question == text


def test_decline_safety_after_as_a_plain_preposition_is_untouched(full_registry):
    # "After lunch" is a preposition phrase, not a leading clause carrying a
    # digit anywhere -- must not be promoted to a premise.
    text = "After lunch, how many candies remain?"
    premises, question = split_question(text, full_registry)
    assert premises == []
    assert question == text


def test_mid_sentence_when_is_unaffected(full_registry):
    # 'when' inside an ordinary (non-leading) premise sentence must parse
    # exactly as before -- the new category membership only changes what
    # split_question does with a SENTENCE-INITIAL marker.
    text = "Priya has 9 shells. Priya knows when she will find 4 more shells."
    premises, question = split_question(text, full_registry)
    assert premises == [
        "Priya has 9 shells.",
        "Priya knows when she will find 4 more shells.",
    ]
    assert question is None
