"""Arithmetic domain (difg): direct binary/unary operation asks.

SYNTHETIC ONLY (constitution rule 3): invented inputs, not difg CASES.

The operator WORDS are grammatical skeleton in rules/arithmetic-ops.yaml
(literals, or the multiplier/percent unit numbers.py folds them into);
answer.py's `arithmetic` consumer applies a general function selected by a
structural opcode — no English word enumerated in Python.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/gsm8k")).registry


@pytest.mark.parametrize(
    "question, want",
    [
        ("What is 12 plus 30?", 42.0),
        ("What is 90 minus 25?", 65.0),
        ("What is 6 times 9?", 54.0),
        ("What is 84 divided by 4?", 21.0),
        ("What is 3 to the power of 4?", 81.0),
        ("What is the square root of 169?", 13.0),
        ("What is 20 percent of 150?", 30.0),
        ("What is 40% of 5?", 2.0),
    ],
)
def test_operation(reg, question, want):
    r = solve(question, reg, tracing=False)
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(want)


def test_divide_by_zero_declines(reg):
    """Definitive-or-decline: division by zero declines rather than errors."""
    r = solve("What is 7 divided by 0?", reg, tracing=False)
    assert not r.answer.committed


def test_unrelated_what_is_question_declines(reg):
    """The ask family is anchored on the operator skeleton; a bare 'what is'
    question with no operator must not spuriously commit."""
    r = solve("What is the capital of France?", reg, tracing=False)
    assert not r.answer.committed


# --- relative change: ONE signed formula, four spellings --------------------
# SYNTHETIC inputs (80->100, 400->300), never difg's 50->75 and 200->150.


@pytest.mark.parametrize(
    "question, want",
    [
        ("What is the percentage increase from 80 to 100?", 25.0),
        ("What is the percent increase from 80 to 100?", 25.0),
        ("What is the percentage decrease from 400 to 300?", -25.0),
        ("What is the percent decrease from 400 to 300?", -25.0),
    ],
)
def test_percent_change_reads_all_four_spellings(reg, question, want):
    assert solve(question, reg).answer.value == pytest.approx(want)


def test_percent_change_is_signed_by_the_numbers_not_the_word(reg):
    # THE contract. 'increase'/'decrease' are grammatical skeleton, not a
    # semantic choice -- the sign comes from the operands. An 'increase' ask
    # over falling numbers must report the fall, not flip it to look positive,
    # or the word would be silently overriding the arithmetic.
    assert solve("What is the percentage increase from 100 to 80?", reg).answer.value == (
        pytest.approx(-20.0)
    )
    assert solve("What is the percentage decrease from 80 to 100?", reg).answer.value == (
        pytest.approx(25.0)
    )


def test_percent_change_from_zero_declines(reg):
    # no relative change is defined against a zero base -- decline, never
    # divide (and never guess a 0 or an infinity)
    assert solve("What is the percentage increase from 0 to 50?", reg).answer.kind == "decline"


def test_percent_of_keeps_its_territory(reg):
    # the pre-existing 'percent OF' ask shares the word 'percent'; the two
    # shapes must stay disjoint
    assert solve("What is 17 percent of 240?", reg).answer.value == pytest.approx(40.8)
