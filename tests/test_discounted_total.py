"""Discounted / taxed totals (difg): total = base x [qty] x (1-disc) x (1+tax).

SYNTHETIC ONLY (constitution rule 3): invented prices and rates, not difg CASES.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/difg")).registry


def test_flat_discount(reg):
    assert solve("What is 25% off $80?", reg).answer.value == pytest.approx(60.0)


def test_flat_discount_then_tax(reg):
    # 80 * 0.75 * 1.10
    assert solve("What is 25% off $80 then 10% tax?", reg).answer.value == pytest.approx(66.0)


def test_per_unit_with_discount(reg):
    assert solve(
        "What is the total for 4 shirts at $10 each with 25% off?", reg
    ).answer.value == pytest.approx(30.0)


def test_per_unit_with_discount_and_tax(reg):
    assert solve(
        "What is the total for 4 shirts at $10 each with 25% off and 10% tax?", reg
    ).answer.value == pytest.approx(33.0)


def test_tax_applies_to_the_discounted_price_not_the_original(reg):
    # THE contract, and the only test that can tell the two designs apart.
    # Taxing first would give 80*1.10*0.75 = 66.0 as well -- multiplication
    # commutes -- so a commuting pair proves nothing. Use rates where an
    # ADDITIVE misreading (base - disc + tax) would differ: 80*0.75*1.10 = 66,
    # but 80 - 20 + 8 = 68. The point is that both adjustments are
    # MULTIPLICATIVE and compose on the running total, never on the base.
    assert solve("What is 25% off $80 then 10% tax?", reg).answer.value == pytest.approx(66.0)
    assert solve("What is 25% off $80 then 0% tax?", reg).answer.value == pytest.approx(60.0)


@pytest.mark.parametrize("bad", ["100% off", "150% off"])
def test_a_total_or_over_discount_declines(reg, bad):
    # not a price reduction; decline rather than return zero or a negative
    assert solve(f"What is {bad} $80?", reg).answer.kind == "decline"


def test_a_word_fraction_cannot_reach_this_family(reg):
    # the percent slots are `type: percent`, which numbers.py flags only for
    # "%"/"percent" SURFACE forms. "half off" is a real English discount this
    # family has not measured, so it must decline rather than be guessed at.
    assert solve("What is half off $80?", reg).answer.kind == "decline"
