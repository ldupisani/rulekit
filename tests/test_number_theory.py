"""Number-theory domain (difg): gcd/lcm/factorial/choose.

SYNTHETIC ONLY (constitution rule 3): invented inputs, not difg CASES.

The operation WORDS live in per-operation sub-categories (categories/
number-theory.yaml); answer.py's `number-theory` consumer dispatches to the
general math function (math.gcd/lcm/factorial/comb) — no word list in Python.
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
        ("What is the GCD of 12 and 18?", 6.0),
        ("What is the LCM of 6 and 8?", 24.0),
        ("What is the factorial of 4?", 24.0),
        ("What is 6 factorial?", 720.0),
        ("What is 5 choose 2?", 10.0),
    ],
)
def test_operation(reg, question, want):
    r = solve(question, reg, tracing=False)
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == want


def test_binary_op_without_second_operand_declines(reg):
    """Definitive-or-decline: GCD needs two numbers; one operand -> decline."""
    r = solve("What is the GCD of 12?", reg, tracing=False)
    assert not r.answer.committed


def test_choose_out_of_range_declines(reg):
    """math.comb is undefined for k > n; decline rather than error."""
    r = solve("What is 3 choose 8?", reg, tracing=False)
    assert not r.answer.committed
