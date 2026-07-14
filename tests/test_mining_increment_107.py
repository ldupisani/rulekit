"""Increment 107 — number-phrase merges run to a FIXPOINT, not once per sentence.

THE BUG (live on main until now). `annotate_numbers` ran three merge passes — the
word-fraction merge, the "N times" multiplier merge, and the "N percent" merge — as a
single-shot `for ...: break`. Only the FIRST matching phrase in a sentence merged; a
SECOND was silently left as two unmerged units:

    "Sam ate one half of the pie and one third of the cake."
      main:  [('one half', 0.5), ('one', 1.0), ('third', 0.333)]   <- 'one third' never merged
      now:   [('one half', 0.5), ('one third', 0.333)]

A sentence carrying two such phrases was therefore misread — and every downstream rule
saw the wrong units.

THE FIX: run each merge pass to a fixpoint (`changed` loop) instead of stopping after the
first hit. Found inside a candidate that smuggled it into a `yaml_only` brief; the
constitution reviewer rejected it there and argued it deserved its own increment with its
own gate and its own TEST-look accounting — an increment you cannot revert independently
is not an increment. It is cut here on its own.

Blast radius is every sentence in the corpus, so the gate is what matters: dev-train
NEUTRAL, dev-holdout SHIP +1, 0 BROKE, 0 DECL->WRONG.

Synthetic strings only (NEVER benchmark items).
"""

import pytest

from rulekit.kernel.engine import analyze, solve


def _numeric_units(text, registry):
    reading = analyze(text, registry)
    return [
        (u.surface, u.features.get("value"))
        for u in reading.units
        if u.features.get("value") is not None
    ]


def test_a_second_word_fraction_in_one_sentence_merges(registry):
    """THE BUG. 'one third' was left as ('one', 1.0) + ('third', 0.333)."""
    units = _numeric_units("Sam ate one half of the pie and one third of the cake.", registry)
    surfaces = [s for s, _ in units]
    assert "one third" in surfaces, f"the second fraction never merged: {units}"
    assert "one half" in surfaces
    assert ("one", 1.0) not in units, "a stray unmerged 'one' survived the fraction merge"


def test_a_single_word_fraction_is_unchanged(registry):
    """The regression guard: one fraction behaved correctly before and must still."""
    units = _numeric_units("Sam ate one half of the pie.", registry)
    assert ("one half", 0.5) in units


def test_three_word_fractions_all_merge(registry):
    """A fixpoint, not merely two passes."""
    units = _numeric_units(
        "Sam ate one half of the pie, one third of the cake and one quarter of the tart.",
        registry,
    )
    surfaces = [s for s, _ in units]
    for expected in ("one half", "one third", "one quarter"):
        assert expected in surfaces, f"{expected!r} never merged: {units}"


def test_two_times_multipliers_in_one_sentence(registry):
    units = _numeric_units(
        "Bob has two times as many apples as Sam and three times as many pears as Sam.",
        registry,
    )
    surfaces = [s for s, _ in units]
    assert "two times" in surfaces and "three times" in surfaces, units


def test_two_percent_phrases_in_one_sentence(registry):
    units = _numeric_units("Sam saved ten percent and spent twenty percent.", registry)
    surfaces = [s for s, _ in units]
    assert "ten percent" in surfaces and "twenty percent" in surfaces, units


def test_the_engine_still_answers_a_single_fraction_document(registry):
    """End-to-end: the merge change must not disturb an ordinary reading."""
    text = "Sam has 12 apples. Sam ate one half of the apples. How many apples does Sam have?"
    assert solve(text, registry).answer.value == 6
