"""Mining increment 58 (compound-rate-reland): compound rate premises ("VERB N ITEM
in T UNIT" — an amount stated over an elapsed span, e.g. "bakes 8 muffins in 4
minutes") feeding the landed rate-span / rate-span-inverse consumers,
including the now-landed MODAL ("will/would it take") phrasing of
ask/how-long-take-span and ask/how-many-timeunit-take-span (mining increment
55).

Before this increment, a compound-rate premise like "bakes 8 muffins in 4
minutes" built NO Rate fact at all — the existing per-unit article form ("4
cars a day", learn.py's `_rate_unit`) only recognizes a SINGLE stated number,
not this two-number compound shape (an amount over an elapsed span). A paired
question ("How long will it take ... to bake 30 muffins?") would then decline
"0 rates known" even though the ask ids and the rate-span-inverse consumer
were already live on main — the emission was the only missing piece, and it
now composes directly with the modal phrasing increment 55 already landed.

This is a re-cut of the once-parked `mining/parked/compound-rate-emission`
lineage, using the pack-declared `span_preposition` category
(packs/core-english/categories/core.yaml, parent: preposition, members: [in])
rather than a literal string compared in Python — mirroring the 'per'->'rate'
sense that already gates the simple per-unit rate form (constitution rule 1:
a word-specific fact belongs only in the pack).

Two coordinated pieces (no new ask ids; core.yaml's asks are reused
unchanged):

  (a) learn.py's `_compound_rate_span` recognizes the "N ITEM in T UNIT"
      premise shape (scanning forward from the counted dobj for a
      `span_preposition`-category token introducing its own counted noun; an
      intervening prepositional frame outside that category is skipped, not
      treated as a match) and emits a Rate fact carrying BOTH the derived
      per-unit `value` (numerator/denominator) AND the two raw stated numbers
      themselves (Rate.numerator/denominator, model.py) — the split exists so
      value-accounting (guards.py) can credit the TEXT's own two numbers as
      read only when a consumer's arithmetic actually uses them, never merely
      because the Rate fact exists (the look #4-#7 existence-vs-use
      invariant).
  (b) answer.py's existing `rate-span` (forward) and `rate-span-inverse`
      consumers each gain a numerator/denominator branch: a compound Rate
      divides/multiplies through its own raw stated numbers directly (rather
      than the bare derived `value`), so a compound rate answers honestly,
      value-accounted, in EITHER direction, under EITHER auxiliary or modal
      question phrasing — the plain (non-compound) Rate path in each
      consumer is untouched.

Synthetic only — every name, number, verb, and item below is invented for
this test file; none is drawn from any GSM8K item or any other test file."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import solve

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def full_registry():
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", mined])
    )


def test_forward_span_uses_the_compound_rate(full_registry):
    # ask/how-many-rate-span ("how many ITEM does WHO VERB in SPAN?"): the
    # SAME compound Rate fact (8 muffins / 4 minutes = 2/minute) answers the
    # forward direction: 2 x 20 = 40
    r = solve(
        "Priya bakes 8 muffins in 4 minutes. How many muffins does Priya "
        "bake in 20 minutes?",
        full_registry,
    )
    assert r.answer.value == 40


def test_inverse_how_long_modal_own_per_unit(full_registry):
    # ask/how-long-take-span with the modal ("will") phrasing landed in
    # increment 55 — no unit named, answer in the rate's own per-unit
    # (minute): 30 muffins / 2/minute = 15
    r = solve(
        "Priya bakes 8 muffins in 4 minutes. How long will it take Priya "
        "to bake 30 muffins?",
        full_registry,
    )
    assert r.answer.value == 15


def test_inverse_how_many_unit_modal_matching_rate_per(full_registry):
    # ask/how-many-timeunit-take-span, modal phrasing, with the asked unit
    # (minutes) matching the rate's own per-unit exactly
    r = solve(
        "Priya bakes 8 muffins in 4 minutes. How many minutes will it take "
        "Priya to bake 30 muffins?",
        full_registry,
    )
    assert r.answer.value == 15


def test_unrelated_in_phrase_is_not_misread_as_a_compound_rate(full_registry):
    # "12 muffins in her closet" — 'in' introduces an uncounted noun (no
    # stated number after it), so `_compound_rate_span` declines the
    # compound-rate reading entirely and the sentence folds as an ordinary
    # Quantity, exactly as it did before this increment
    r = solve(
        "Priya has 12 muffins in her closet. How many muffins does Priya "
        "have?",
        full_registry,
    )
    assert r.answer.value == 12


def test_no_rate_at_all_declines(full_registry):
    # a target quantity in the question but NO Rate fact anywhere for this
    # entity/measure — decline, never a guess (the ask itself recognizes
    # the shape; only the fact is missing)
    r = solve(
        "Priya has 30 muffins to bake. How long will it take Priya to bake "
        "30 muffins?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_intervening_non_span_frame_is_skipped(full_registry):
    # "mows 5 lawns of a park in 25 minutes" — the non-span-preposition
    # frame ("of a park") between the counted dobj and the compound span
    # marker is skipped, not treated as ending the scan
    r = solve(
        "Owen mows 5 lawns of a park in 25 minutes. How many minutes does "
        "it take Owen to mow 15 lawns?",
        full_registry,
    )
    assert r.answer.value == 75
