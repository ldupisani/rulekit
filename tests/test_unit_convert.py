"""Typed-gold LOADER + the first typed-gold domain (difg `unit_conversion`).

SYNTHETIC ONLY (constitution rule 3): invented golds and invented conversion
questions, not difg CASES.

The judge itself is pinned in test_typed_gold.py; this file pins the two halves
that made difg's non-numeric golds reachable at all — the loader that classifies
a gold payload, and the first domain whose golds are quantities rather than bare
numbers.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.harness.firewall import parse_gold, parse_typed_gold
from rulekit.kernel.engine import solve


# --- the loader: STRUCTURAL classification, never a unit list ---------------


@pytest.mark.parametrize(
    "payload, kind, value, unit",
    [
        ("#### 42", "number", 42.0, None),
        ("#### -3.5", "number", -3.5, None),
        ("#### 1,048,576", "number", 1048576.0, None),   # comma = thousands mark
        ("#### $215.14", "money", 215.14, None),
        ("#### 50%", "percent", 50.0, None),
        ("#### -25%", "percent", -25.0, None),
        ("#### 68.04 kg", "quantity", 68.04, "kg"),
        ("#### 134 days", "quantity", 134.0, "days"),
        ("#### 96.56 km/h", "quantity", 96.56, "km/h"),
        # a unit the harness has never heard of parses anyway: classification is
        # structural, so there is no unit list for it to be missing from — which
        # is also why no lexicon leaks into the harness (constitution rule 1)
        ("#### 12.5 zorkmids", "quantity", 12.5, "zorkmids"),
        ("#### True", "verdict", "true", None),
        ("#### no", "verdict", "no", None),
    ],
)
def test_parse_typed_gold(payload, kind, value, unit):
    g = parse_typed_gold(payload)
    assert g is not None
    assert (g.kind, g.value, g.unit) == (kind, value, unit)


def test_bare_number_is_kind_number_not_quantity():
    """Ordering is the classification: a bare number must be `number` so it takes
    the identical numeric comparison the float path uses. If `quantity` were
    tried first, every plain gold would acquire a phantom unit."""
    assert parse_typed_gold("#### 5").kind == "number"


def test_float_path_is_untouched():
    """`gold: typed` is opt-in and no project but difg sets it. The default path
    must stay byte-for-byte — this is why no GSM8K item can take the typed
    branch, and why byte-identity is a property of the SHAPE of the change."""
    assert parse_gold("#### 18") == 18.0
    assert parse_gold("#### 1,234") == 1234.0
    assert parse_gold("no gold here") is None


# --- the unit_conversion domain --------------------------------------------


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/difg")).registry


@pytest.mark.parametrize(
    "question, want",
    [
        ("How many inches are in 2 feet?", 24.0),
        ("How many ounces are in 3 pounds?", 48.0),
        ("How many minutes are in 4 hours?", 240.0),
        ("How many hours are in 2 days?", 48.0),
        ("How many meters are in 7 kilometers?", 7000.0),
    ],
)
def test_unit_convert(reg, question, want):
    r = solve(question, reg, tracing=False)
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(want)


@pytest.mark.parametrize(
    "question, want",
    [
        # the IMPERATIVE frame — a task sentence with no question mark. Works
        # only because 'convert' carries the `imperative` sense in the lexicon
        # (an ASK_CUE_SENSE), exactly as 'compute'/'calculate' already do.
        ("Convert 3 kilometers to meters", 3000.0),
        ("Convert 250 grams to kilograms", 0.25),
        ("Convert 2 hours to minutes", 120.0),
        ("Convert 4 liters to milliliters", 4000.0),
    ],
)
def test_unit_convert_imperative(reg, question, want):
    r = solve(question, reg, tracing=False)
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(want)


def test_imperative_is_a_question_without_a_question_mark(reg):
    """The blocker this closed: an imperative used to die at "no question found"
    BEFORE any ask was tried — 50 difg items, 26 of them 'Convert ...'."""
    r = solve("Convert 2 feet to inches", reg, tracing=False)
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(24.0)


def test_metric_imperial_pairs(reg):
    """The added factors, checked against real magnitudes rather than echoed:
    a meter is ~3.28 feet and a gallon ~3.79 litres."""
    assert solve("How many feet are in 10 meters?", reg, tracing=False).answer.value == pytest.approx(32.8084, rel=1e-4)
    assert solve("Convert 2 gallons to liters", reg, tracing=False).answer.value == pytest.approx(7.5708, rel=1e-4)
    assert solve("Convert 100 centimeters to inches", reg, tracing=False).answer.value == pytest.approx(39.3701, rel=1e-4)


def test_unit_symbols_resolve_to_their_unit(reg):
    """A SYMBOL is a number-form of its unit, carried by the ordinary plural map
    ('kg' was already among kilogram's plurals; 'km' was missing from
    kilometer's). No abbreviation mechanism is needed — a comment once claimed
    otherwise and was wrong."""
    assert solve("Convert 10 pounds to kg", reg, tracing=False).answer.value == pytest.approx(4.5359, rel=1e-4)
    assert solve("How many km is 2 miles?", reg, tracing=False).answer.value == pytest.approx(3.2187, rel=1e-4)


def test_unknown_pair_declines(reg):
    """The factors are DATA (rulekit/conversions@1). A pair the table does not
    know declines rather than guessing — no unit is named in Python."""
    r = solve("How many gallons are in 3 kilometers?", reg, tracing=False)
    assert not r.answer.committed


def test_a_non_convert_imperative_is_not_a_question(reg):
    """'convert' was admitted as a task cue; 'find'/'solve'/'evaluate' were NOT
    (they open 4 GSM8K TEST and 69 SciBench sentences — see lexicon/a-f.yaml).
    Pin that the admission stayed scoped to the one measured word."""
    r = solve("Find 2 feet in inches", reg, tracing=False)
    assert not r.answer.committed


def test_a_non_unit_place_question_is_untouched(reg):
    """The `measure_unit` gate is what lets the conversion ask outrank
    ask/how-many-in-place on an equal-length match. When the nouns are NOT units,
    no member matches, the conversion ask cannot fire, and that ask keeps the
    question exactly as it always read it."""
    r = solve(
        "There are 16 apples in a bowl. How many apples are in the bowl?",
        reg, tracing=False,
    )
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(16.0)
