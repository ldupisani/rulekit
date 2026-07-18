"""Affine (zero-point) scale conversion: temperature.

SYNTHETIC ONLY (constitution rule 3): invented temperatures, not difg CASES.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/difg")).registry


def test_fahrenheit_to_celsius(reg):
    assert solve("Convert 212 degrees Fahrenheit to Celsius.", reg).answer.value == (
        pytest.approx(100.0)
    )


def test_kelvin_to_celsius_reads_a_bare_number(reg):
    # "300 Kelvin" leaves a BARE number -- a scale name is not a lexicon unit,
    # so nothing merges, unlike "212 degrees Fahrenheit"
    assert solve("Convert 373.15 Kelvin to Celsius", reg).answer.value == (
        pytest.approx(100.0)
    )


def test_the_inverse_direction_is_stored_too(reg):
    # forward is (x+offset)*factor, so the inverse is x/factor - offset --
    # itself affine, and the registry derives it rather than the table
    # listing it twice
    assert solve("Convert 100 degrees Celsius to Fahrenheit.", reg).answer.value == (
        pytest.approx(212.0)
    )
    assert solve("Convert 100 degrees Celsius to Kelvin.", reg).answer.value == (
        pytest.approx(373.15)
    )


def test_a_factor_alone_cannot_express_this(reg):
    # THE reason this is not `rulekit/conversions@1`: the scales disagree
    # about where zero is. A pure factor would send 0 to 0; the real answer
    # is 32.
    assert solve("Convert 0 degrees Celsius to Fahrenheit.", reg).answer.value == (
        pytest.approx(32.0)
    )


def test_an_unlisted_scale_pair_declines(reg):
    # a PAIR table, not a graph. Fahrenheit <-> Kelvin is a real conversion
    # that no measured question asks for, so it is absent and declines
    # rather than being chained or approximated.
    assert solve(
        "Convert 100 degrees Fahrenheit to Kelvin.", reg
    ).answer.kind == "decline"


def test_an_unknown_scale_declines(reg):
    assert solve("Convert 100 degrees Rankine to Celsius.", reg).answer.kind == "decline"


def test_the_ordinary_unit_conversions_are_unaffected(reg):
    # the two families are disjoint by construction: unit-convert gates both
    # slots on `measure_unit`, and a scale name is a NAME, never a member
    assert solve("Convert 7 kilometers to meters.", reg).answer.value == pytest.approx(7000.0)
    assert solve("Convert 60 degrees to radians.", reg).answer.value == (
        pytest.approx(1.0471975511965976)
    )
