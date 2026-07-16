"""Coordinate geometry (difg): a named quantity over two points.

SYNTHETIC ONLY (constitution rule 3): invented coordinates, not difg CASES.

Also pins the NUMBER-READING change this domain is built on. "(3,4)" used to
read as the scalar 34 — the tokenizer strips the parens and numbers.py's _DIGIT
accepted any comma placement as a thousands separator. _DIGIT now requires a
real thousands grouping and _TUPLE claims what is left. The comma tests below
are the regression net for that: they pin BOTH directions of the ambiguity
(thousands vs tuple) and the trailing-comma case that broke three list_statistic
items the first time this was written.
"""

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
        # 3-4-5 and 8-15-17 triangles, neither of which difg asks for
        ("What is the distance between the points (0,0) and (6,8)?", 10.0),
        ("What is the distance between (0,0) and (8,15)?", 17.0),
        ("What is the distance from (1,1) to (4,5)?", 5.0),
        ("What is the slope between (0,0) and (2,8)?", 4.0),
        ("What is the slope between (1,7) and (5,7)?", 0.0),
        # a negative slope, and the from/to frame
        ("What is the slope between (0,10) and (5,0)?", -2.0),
    ],
)
def test_quantity(reg, question, want):
    r = solve(question, reg, tracing=False)
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(want)


def test_distance_is_n_dimensional(reg):
    """The distance formula sums over however many components the points have,
    so a 3-D pair reads with no extra machinery."""
    r = solve("What is the distance between (0,0,0) and (2,3,6)?", reg, tracing=False)
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(7.0)


def test_vertical_line_slope_declines(reg):
    """Definitive-or-decline: a vertical line has undefined slope. The guard is
    on dx only — a HORIZONTAL line is slope 0, not undefined (pinned above)."""
    r = solve("What is the slope between (3,1) and (3,9)?", reg, tracing=False)
    assert not r.answer.committed


def test_mismatched_arity_declines(reg):
    """Points of different arity name no distance."""
    r = solve("What is the distance between (1,1) and (4,5,9)?", reg, tracing=False)
    assert not r.answer.committed


# --- the number-reading change this domain rests on ------------------------


def test_thousands_separator_still_reads_as_one_number(reg):
    """The ambiguity resolution: a VALID thousands grouping is a scalar, which
    is what money in the word-problem corpora depends on. This must never
    regress into being read as a tuple."""
    r = solve("What is 1,234 plus 1?", reg, tracing=False)
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(1235.0)


def test_comma_pair_is_not_a_scalar(reg):
    """The latent confident-wrong this increment closes: "3,4" is not the
    number 34, so an arithmetic ask over it must DECLINE rather than answer 35."""
    r = solve("What is 3,4 plus 1?", reg, tracing=False)
    assert not r.answer.committed


def test_trailing_comma_in_a_spaced_list_still_reads(reg):
    """REGRESSION (the difg gate caught this): in a spaced list the tokenizer
    keeps the comma on the fold ("12,"), and the permissive old pattern absorbed
    it by accident. Requiring three digits after every comma silently broke
    three list_statistic items. A trailing comma is punctuation, not a
    separator."""
    r = solve("What is the highest of 11, 46, 8, and 34?", reg, tracing=False)
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(46.0)
