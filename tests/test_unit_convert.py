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


# --- the ANGLE pair: degrees <-> radians ------------------------------------
# SYNTHETIC angles (360/45/720), never the corpus's 180 and 90.


def test_degrees_convert_to_radians(reg):
    assert solve("Convert 360 degrees to radians.", reg).answer.value == pytest.approx(
        6.283185307179586
    )


def test_radians_convert_back_to_degrees(reg):
    # the table is stored in BOTH directions, so the reverse needs no entry
    assert solve("Convert 3.141592653589793 radians to degrees.", reg).answer.value == (
        pytest.approx(180.0)
    )


def test_the_radian_symbol_is_a_number_form_of_its_unit(reg):
    # 'rad' folds to 'radian' exactly as 'km' folds to 'kilometer'
    assert solve("Convert 45 degrees to rad.", reg).answer.value == pytest.approx(
        0.7853981633974483
    )


def test_the_factor_is_precise_enough_for_the_1_percent_comparator(reg):
    # difg's golds are rounded to 4dp ("3.1416"), and the typed-gold
    # comparator is TOL + 1% RELATIVE -- so a 4dp FACTOR would still pass the
    # bench while being wrong. Pin the full-precision value instead, or the
    # test cannot tell a correct table from a sloppy one.
    got = solve("Convert 720 degrees to radians.", reg).answer.value
    assert abs(got - 12.566370614359172) < 1e-12


def test_the_trig_asks_keep_their_territory(reg):
    # 'degree' now sits in measure_unit AND angle_degrees. The trig asks gate
    # on the latter alone, so admitting the former must not move them -- and
    # the degrees->degree plural map must not break the gate either.
    assert solve("What is the sine of 30 degrees?", reg).answer.value == pytest.approx(0.5)
    assert solve("What is the cosine of 60 degrees?", reg).answer.value == pytest.approx(0.5)


def test_a_non_angle_unit_pair_is_unaffected(reg):
    assert solve("Convert 5 kilometers to meters.", reg).answer.value == pytest.approx(5000.0)


# --- 'seconds': the literal-variant ask -------------------------------------


def test_seconds_convert_via_the_literal_variant(reg):
    # 'second' is an ADJECTIVE in the lexicon (the ordinal), so it cannot join
    # the noun-rooted `measure_unit` category. Without a literal variant the
    # question lost to ask/how-many-in-place, which reads '5 minutes' as a
    # PLACE -- while minute -> second sat in the table the whole time.
    assert solve("How many seconds are in 4 minutes?", reg).answer.value == 240.0
    assert solve("How many seconds is 2 minutes?", reg).answer.value == 120.0


def test_the_seconds_variant_still_needs_a_real_conversion(reg):
    # the literal only fixes which ask READS the question; the pair must
    # still exist in the table
    assert solve("How many seconds are in 3 gallons?", reg).answer.kind == "decline"


def test_the_general_conversion_asks_are_unaffected(reg):
    assert solve("How many minutes are in 5 hours?", reg).answer.value == 300.0
