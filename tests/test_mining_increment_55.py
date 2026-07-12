"""Mining candidate modal-how-long-asks: future-modal (will/would-phrased)
variants of the inverse rate-span duration asks (increment 51's
ask/how-long-take-span and ask/how-many-timeunit-take-span).

Increment 51 shipped "how long does/did it take WHO to VERB N ITEM?" and the
named-unit sibling "how many TIMEUNIT does/did it take ...?", gating the aux
slot to `type: auxiliary` (do/does/did only) and explicitly noting that a
will-phrased "how long will it take" was a distinct, disjoint mining
candidate because 'will'/'would' are tagged 'modal', never 'auxiliary'.

This candidate closes that gap the SAME way increment 49 widened four other
auxiliary-gated factual asks: `aux, type: future_modal` (an existing slot
type — packs/core-english/categories/core.yaml, kernel/patterns.py
_slot_ok) accepts an auxiliary-sense token OR a modal-sense token whose
word is in the `future_modal` category (will/would only). The six capacity/
hypothetical modals (can/could/should/may/might/must) are excluded, so a
genuinely capacity-shaped question can never reach these asks. Both ask ids
route to the SAME rate-span-inverse consumer (answer.py), byte-for-byte
unchanged.

The one adjacency risk (ask/how-many-timeunit-take-span vs.
ask/how-many-capacity, which also gates a will/would-capable `modal` slot)
is resolved structurally: this ask's literal 'it'/'take'/'to' tokens are
required and non-optional, so a question that fully satisfies this ask's
shape either fails ask/how-many-capacity's shape outright (the expletive
'it' cannot satisfy capacity's `who, type: entity` slot — an unresolved
pronoun never does) or, on any hypothetical overlapping reading, loses on
specificity (this ask's 10 consumed units vs. capacity's 6). A genuine
capacity-shaped question ("how many hours will Tom read?" with no 'it
take ... to' skeleton) still only matches ask/how-many-capacity, exactly
as before this change.

Synthetic only."""

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


def test_how_long_will_take_divides_amount_by_rate(full_registry):
    r = solve(
        "Priya bakes 6 muffins per hour. How long will it take Priya to "
        "bake 24 muffins?",
        full_registry,
    )
    assert r.answer.value == 4


def test_how_long_would_take_divides_amount_by_rate(full_registry):
    r = solve(
        "Priya bakes 6 muffins per hour. How long would it take Priya to "
        "bake 24 muffins?",
        full_registry,
    )
    assert r.answer.value == 4


def test_how_many_timeunit_will_take_matching_rate_per_unit(full_registry):
    r = solve(
        "Priya bakes 6 muffins per hour. How many hours will it take "
        "Priya to bake 24 muffins?",
        full_registry,
    )
    assert r.answer.value == 4


def test_how_many_timeunit_would_take_matching_rate_per_unit(full_registry):
    r = solve(
        "Priya bakes 6 muffins per hour. How many hours would it take "
        "Priya to bake 24 muffins?",
        full_registry,
    )
    assert r.answer.value == 4


def test_ordinary_auxiliary_form_still_matches_unchanged(full_registry):
    # future_modal is an ADDITION to the aux slot, not a replacement — the
    # pre-existing do/does/did form must keep matching exactly as before
    r = solve(
        "Priya bakes 6 muffins per hour. How long does it take Priya to "
        "bake 24 muffins?",
        full_registry,
    )
    assert r.answer.value == 4


def test_how_many_timeunit_mismatched_unit_declines(full_registry):
    # will-phrased sibling of increment 51's own mismatch decline-safety
    # test: the asked unit ('minutes') doesn't match the rate's own
    # per-unit ('hour') — no conversion is attempted
    r = solve(
        "Priya bakes 6 muffins per hour. How many minutes will it take "
        "Priya to bake 24 muffins?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_no_rate_known_declines(full_registry):
    r = solve(
        "Priya has 24 muffins. How long will it take Priya to bake 24 "
        "muffins?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_capacity_modal_can_does_not_reach_duration_ask(full_registry):
    # decline-safety: 'can' is a capacity/hypothetical modal, NOT in
    # future_modal — the 'it take ... to' skeleton these asks require is
    # entirely absent here, and the question must fall to
    # ask/how-many-capacity (which declines for lack of a Price fact), not
    # to the widened duration asks
    r = solve(
        "Priya bakes 6 muffins per hour. How many hours can Priya bake?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_genuine_capacity_ask_unaffected_by_the_widening(full_registry):
    # regression / adjacency-risk check: a genuinely capacity-shaped
    # will-phrased question (no 'it take ... to' skeleton) must still only
    # be reachable through ask/how-many-capacity, never rerouted into the
    # duration-inverse asks this candidate widens
    r = solve(
        "Priya bakes 6 muffins per hour. How many hours will Priya bake?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_forward_rate_span_ask_unaffected(full_registry):
    # regression: the pre-existing FORWARD rate-span ask (increments 8/9)
    # still answers exactly as before this change
    r = solve(
        "Priya bakes 6 muffins per hour. How many muffins does Priya bake "
        "in 3 hours?",
        full_registry,
    )
    assert r.answer.value == 18
