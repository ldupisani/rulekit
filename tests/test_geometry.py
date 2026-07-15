"""Geometry formula-selection (the difg geometry domain).

SYNTHETIC ONLY (constitution rule 3): different values/shapes than any difg
CASES item — the mechanism, not the benchmark strings.

"What is the AREA of a CIRCLE with RADIUS r?" -> look up the (shape, quantity)
formula in the declarative table (packs/difg-mined/geometry.yaml), bind the named
dimensions, evaluate. The formulas are DATA; answer.py's `geometry` consumer is
the generic evaluator (no per-domain Python branch)."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/gsm8k")).registry


def test_one_dimension_formula(reg):
    r = solve("What is the area of a circle with radius 10?", reg, tracing=False)
    assert r.answer.committed and r.answer.value == 314.16  # pi * 100, 2dp


def test_two_dimension_formula(reg):
    r = solve("What is the area of a rectangle with length 5 and width 7?", reg, tracing=False)
    assert r.answer.committed and r.answer.value == 35.0


def test_integer_result_is_not_mangled_by_rounding(reg):
    r = solve("What is the volume of a cube with side 4?", reg, tracing=False)
    assert r.answer.committed and r.answer.value == 64.0


def test_square_shape_noun(reg):
    """'square' carries an adjective sense too; in "a square with side N" the
    disambiguator picks the shape noun."""
    r = solve("What is the area of a square with side 6?", reg, tracing=False)
    assert r.answer.committed and r.answer.value == 36.0


def test_surface_area_merges_to_the_area_quantity(reg):
    """'surface area' merges (adjective+noun) to the 'area' quantity; a sphere's
    area IS its surface area, so (sphere, area) answers it."""
    r = solve("What is the surface area of a sphere with radius 3?", reg, tracing=False)
    assert r.answer.committed and r.answer.value == 113.1  # 4*pi*9, 2dp


def test_wrong_dimension_for_the_shape_declines(reg):
    """Definitive-or-decline: circle area needs RADIUS; given LENGTH, the formula
    has an unbound variable and must decline, never guess."""
    r = solve("What is the area of a circle with length 5?", reg, tracing=False)
    assert not r.answer.committed


def test_unknown_shape_quantity_pair_declines(reg):
    """No (circle, perimeter) formula in the table -> decline."""
    r = solve("What is the perimeter of a circle with radius 5?", reg, tracing=False)
    assert not r.answer.committed
