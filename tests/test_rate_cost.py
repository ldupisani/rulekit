"""Unit-converted rate costing (difg): cost = convert(quantity) x rate.

SYNTHETIC ONLY (constitution rule 3): invented quantities and rates.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/difg")).registry


def test_the_quantity_is_converted_into_the_rates_unit(reg):
    # THE increment. 20 miles is 32.18688 km; at $2/km that is $64.37.
    # Multiplying the two stated numbers gives $40 -- the conversion is the
    # whole point, so this test would pass trivially without it only if the
    # units happened to match.
    assert solve(
        "What is the cost of 20 miles at $2 per km?", reg
    ).answer.value == pytest.approx(64.37376)


def test_the_total_frame_is_the_same_question(reg):
    assert solve(
        "What is the total cost of 20 miles at $2 per km?", reg
    ).answer.value == pytest.approx(64.37376)


def test_matching_units_need_no_conversion(reg):
    assert solve(
        "What is the cost of 20 kilometers at $2 per km?", reg
    ).answer.value == pytest.approx(40.0)


def test_an_unreachable_unit_pair_declines(reg):
    # the conversions table is a PAIR table and this consumer reads it
    # DIRECTLY -- no transitive chaining (see the pack header: the one DEV
    # item a chain would reach has a defective gold). 'yard' and 'kilometer'
    # are not paired, so this declines rather than guessing a factor.
    assert solve(
        "What is the cost of 100 yards at $3 per km?", reg
    ).answer.kind == "decline"


def test_a_pair_the_table_cannot_reach_at_all_declines(reg):
    assert solve(
        "What is the cost of 20 miles at $2 per gallon?", reg
    ).answer.kind == "decline"


def test_this_ask_outranks_the_generic_cost_asks(reg):
    # these questions already matched generic money asks, which then declined
    # ("a combined ask needs at least two holders of 'cost'"). match_ask ranks
    # by (consumed units, category-gate depth) and this ask wins on both --
    # if a future ask ever outranks it, this is the test that should fail.
    got = solve("What is the total cost of 20 miles at $2 per km?", reg)
    assert got.answer.kind == "number"
    assert "rate-cost" in got.answer.reason
