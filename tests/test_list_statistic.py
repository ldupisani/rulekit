"""List-statistic domain (difg): "What is the AVERAGE of ...?"

SYNTHETIC ONLY (constitution rule 3): invented number lists, not difg CASES.

The statistic WORDS live in per-operation sub-categories (categories/
statistics.yaml); answer.py's `list-statistic` consumer reads every number in the
question and applies the general math operation for the word's sub-category
(mean/median/max/min/product/mode) — no word list in Python.
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
        ("What is the average of 10, 20, and 30?", 20.0),
        ("What is the median of 1, 100, and 7?", 7.0),
        ("What is the highest of 3, 99, and 42?", 99.0),
        ("What is the minimum of 6, 2, 9, and 4?", 2.0),
        ("What is the product of 2, 5, and 10?", 100.0),
        ("What is the mode of 8, 8, 3, and 5?", 8.0),
    ],
)
def test_statistic(reg, question, want):
    r = solve(question, reg, tracing=False)
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == want


def test_average_via_literal_variant(reg):
    """'average' is the aggregate marker (not a noun); the literal-variant ask
    maps it to the mean without a noun sense (which broke the average consumer)."""
    r = solve("What is the average of 10, 20, and 30?", reg, tracing=False)
    assert r.answer.committed and r.answer.value == 20.0


def test_ambiguous_mode_declines(reg):
    """Definitive-or-decline: two values tie for most frequent -> no unique mode."""
    r = solve("What is the mode of 1, 1, 2, and 2?", reg, tracing=False)
    assert not r.answer.committed
