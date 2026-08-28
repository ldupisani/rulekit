"""Reusable chemistry pack coverage in the curated project."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def curated():
    return load_project(ROOT / "projects" / "curated")


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("What is the molar mass of NH3?", 17.031),
        ("How many moles are in 68.152 grams of H2S?", 2.0),
        ("What is the weight of 3 moles of H2S?", 1.0018344),
    ],
)
def test_formula_chemistry_is_available_in_curated(curated, question, expected):
    result = solve(question, curated.registry)
    assert result.answer.committed, result.answer.reason
    assert result.answer.value == pytest.approx(expected)


def test_unknown_element_formula_declines(curated):
    result = solve("How many moles are in 90 grams of Xx2O?", curated.registry)
    assert not result.answer.committed


def test_singular_mole_remains_unknown(curated):
    assert "mole" not in curated.registry.lexicon
