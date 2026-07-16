"""Trigonometry domain (difg): named trig function applied to one angle.

SYNTHETIC ONLY (constitution rule 3): invented angles, not difg CASES. difg's own
items ask for the sine of 30 and 90 degrees; every angle below is deliberately
different so this file never encodes a corpus string.

The function WORDS are grammatical skeleton in rules/trig-ops.yaml (literals);
answer.py's `trigonometry` consumer applies a general function selected by a
structural opcode — no English word enumerated in Python.
"""

import math
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/difg")).registry


@pytest.mark.parametrize(
    "question, want",
    [
        ("What is the sine of 45 degrees?", math.sqrt(2) / 2),
        ("What is the cosine of 45 degrees?", math.sqrt(2) / 2),
        ("What is the tangent of 60 degrees?", math.sqrt(3)),
        ("What is the sine of 0 degrees?", 0.0),
        ("What is the cosine of 0 degrees?", 1.0),
        # the abbreviated function name is its own ask, same opcode
        ("What is the sin of 45 degrees?", math.sqrt(2) / 2),
        # a single degree, so the unit is singular rather than plural
        ("What is the tangent of 1 degree?", math.tan(math.radians(1))),
    ],
)
def test_function(reg, question, want):
    r = solve(question, reg, tracing=False)
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(want)


@pytest.mark.parametrize("angle", [90, 270, -90])
def test_tangent_singularity_declines(reg, angle):
    """Definitive-or-decline: tan is undefined at 90 + 180k degrees. math.tan
    does not raise there (float error returns ~1.6e16), so the consumer's
    cosine guard is the only thing standing between us and a confident-wrong."""
    r = solve(f"What is the tangent of {angle} degrees?", reg, tracing=False)
    assert not r.answer.committed


def test_non_angle_operand_declines(reg):
    """The operand is gated on the `angle_degrees` category, so a count of
    something that is not an angle must not commit a nonsense number."""
    r = solve("What is the sine of 30 apples?", reg, tracing=False)
    assert not r.answer.committed


def test_unrelated_what_is_question_declines(reg):
    """The family is anchored on the function-name skeleton; a bare 'what is'
    question with no trig function must not spuriously commit."""
    r = solve("What is the capital of France?", reg, tracing=False)
    assert not r.answer.committed
