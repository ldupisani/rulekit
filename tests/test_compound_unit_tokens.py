"""Compound scientific units stay whole before lexical interpretation."""

from rulekit.kernel.tokenize import tokenize


def test_slash_units_and_exponents_are_one_token():
    units = tokenize("Rates: 11 m/s, 3 m/s^2, and 5 cm^3.", tracing=False).units
    surfaces = [unit.surface for unit in units]

    assert "m/s" in surfaces
    assert "m/s^2" in surfaces
    assert "cm^3" in surfaces
    assert surfaces.count("2") == 0
    assert surfaces.count("3") == 1  # the stated count, never either exponent
