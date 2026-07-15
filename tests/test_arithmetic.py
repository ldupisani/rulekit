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
