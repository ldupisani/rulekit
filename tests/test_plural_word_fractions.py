"""Plural spelled fraction words ("two thirds", "three fifths"): pack-data
only change to packs/core-english/numbers.yaml's `fractions` table, adding
the plural spelling beside each existing singular (halves, thirds, fourths,
fifths, sixths, sevenths, eighths, ninths, tenths). `quarters` also carries a
coin sense. The reader licenses its fraction reading in a definite partitive
that names a nonmoney collection. The existing word-count x
word-fraction merge (`annotate_numbers`) already reads any `fold` present
in `reg.fractions`, so "two thirds" is read as 2/3 the same way "two
fifths" already was; the increment-28 fraction-partition machinery and the
fraction-of-remainder consumer then run unchanged. Synthetic only."""

import pytest

from rulekit.kernel.engine import solve


def test_two_thirds_of_them_are_adjective(full_registry):
    r = solve(
        "Maria has 18 pencils. Two thirds of them are blue. "
        "How many pencils are blue?",
        full_registry,
    )
    assert r.answer.value == 12


def test_three_fourths_of_them_are_adjective(full_registry):
    r = solve(
        "Priya has 16 stickers. Three fourths of them are gold. "
        "How many stickers are gold?",
        full_registry,
    )
    assert r.answer.value == 12


def test_three_fifths_of_them_are_noun_membership(full_registry):
    r = solve(
        "Tom has 20 pets. Three fifths of them are dogs. "
        "How many dogs does Tom have?",
        full_registry,
    )
    assert r.answer.value == pytest.approx(12)


def test_spent_two_thirds_of_the_money_leaves_remainder(full_registry):
    r = solve(
        "Ellen has 30 dollars. Ellen spent two thirds of the money. "
        "How much does Ellen have left?",
        full_registry,
    )
    assert r.answer.value == 10


def test_unadmitted_plural_fraction_word_still_declines(full_registry):
    # "twelfths" has no singular or plural entry in the fractions table —
    # the mechanism must not generalize beyond the admitted family.
    r = solve(
        "Nadia has 40 beads. Twelfths of them are silver. "
        "How many beads are silver?",
        full_registry,
    )
    assert r.answer.kind == "decline"
