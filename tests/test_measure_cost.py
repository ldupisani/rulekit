"""Geometric-measure costing (difg): cost = a measure of a W-by-H rectangle
x a unit rate, optionally taxed.

SYNTHETIC ONLY (constitution rule 3): invented dimensions and rates, not difg
CASES.

The operation word is a CATEGORY gate and each ask names a structural OPCODE,
so no operation word reaches answer.py -- the `arithmetic` template's
add/subtract-per-ask discipline, one domain over.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/difg")).registry


def test_perimeter_costing(reg):
    # 2*(10+20) = 60 m of fence at $3 = 180
    assert solve(
        "How much to fence a 10 by 20 yard at $3 per meter?", reg
    ).answer.value == pytest.approx(180.0)


def test_perimeter_costing_with_tax(reg):
    assert solve(
        "How much to fence a 10 by 20 yard at $3 per meter plus 10% tax?", reg
    ).answer.value == pytest.approx(198.0)


# --- KNOWN BLOCKER, pinned so it stays visible ----------------------------
# Three of this family's four asks cannot fire yet, and NOT because the shapes
# are wrong -- they are blocked by an unrelated kernel behaviour.
# `obligations.disambiguate` commits only a UNIQUE winner, so a SECOND
# ambiguous unit anywhere in the sentence can tie the arbitration, mark every
# ambiguous unit unresolved, and let the `ambiguity` guard veto before any ask
# is tried. "How much ..." always contributes one ('much': interrogative /
# quantifier); the long frame adds 'cost' (noun / verb) and an area rate adds
# 'square' (adjective / noun).
#
# These tests assert the CURRENT behaviour and name the cause. When the
# arbitration learns to break these ties they should flip to the commented
# expectations -- that is the signal the blocker is gone.
# (A structural `interrogative`-after-`interrogative` pre-filter was tried and
# does NOT fix it: reducing 'much' to one option still leaves 'cost'/'square'
# tying two ways on their own. Measured, zero buyers, reverted.)


def test_the_long_frame_is_blocked_by_an_ambiguity_tie(reg):
    got = solve("How much does it cost to fence a 10 by 20 yard at $3 per meter?", reg)
    assert got.answer.kind == "decline"          # want: 180.0
    assert got.veto is not None and got.veto.guard == "ambiguity"


def test_an_area_rate_is_blocked_by_the_same_tie(reg):
    got = solve("How much to tile a 10 by 20 meter floor at $8 per square meter?", reg)
    assert got.answer.kind == "decline"          # want: 1600.0
    assert got.veto is not None and got.veto.guard == "ambiguity"


def test_the_first_measure_may_carry_its_own_unit(reg):
    # "10 meter by 20 yard" -- the first measure merges into a counted unit
    # rather than staying a bare value. Reachable in the SHORT frame, which
    # adds no second ambiguous unit.
    assert solve(
        "How much to fence a 10 meter by 20 yard at $3 per meter?", reg
    ).answer.value == pytest.approx(180.0)


# --- THE CROSS-CHECK: two independent signals must agree -------------------


def test_a_length_rate_on_an_area_job_declines(reg):
    # 'tile' is an AREA measure, so its ask requires "per SQUARE <unit>".
    # Quoted at a linear rate the question matches NEITHER shape and must
    # decline, rather than confidently multiplying an area by a length rate.
    assert solve(
        "How much to tile a 10 by 20 meter floor at $3 per meter?", reg
    ).answer.kind == "decline"


def test_a_perimeter_ask_cannot_claim_a_square_rate(reg):
    # a match sequence FLOATS and 'square' is itself noun-sensed, so a bare
    # `type: noun` rate-unit slot would let the PERIMETER shape match "per
    # square meter" with runit='square'. Gating on `measure_unit` is what
    # stops it -- 'square' is not one.
    assert solve(
        "How much to fence a 10 by 20 yard at $3 per square meter?", reg
    ).answer.kind == "decline"


def test_a_non_positive_measure_declines(reg):
    # not a rectangle; decline rather than return a zero cost
    assert solve(
        "How much to fence a 0 by 20 yard at $3 per meter?", reg
    ).answer.kind == "decline"


def test_the_operation_words_are_pack_data(reg):
    # constitution rule 1. 'paint' is deliberately NOT a member: it is a VERB
    # in the lexicon, and adding a noun sense to reach a noun-rooted category
    # is the `average`/`second` trap. If this ever moves into Python, this is
    # the test that should start failing.
    assert reg.word_in_category("tile", "area_measure")
    assert reg.word_in_category("carpet", "area_measure")
    assert reg.word_in_category("fence", "perimeter_measure")
    assert not reg.word_in_category("paint", "area_measure")
