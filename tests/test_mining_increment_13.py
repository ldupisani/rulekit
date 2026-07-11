"""Mining candidate rate-chain: chained rates (rate x rate spans —
pages/hour x hours/day x days). Extends the rate-span consumer
(kernel/answer.py, `consumer == "rate-span"`): when the asked span's unit
does not match the committing rate's `per` unit, and no reg.conversions
entry chains them, a SECOND Rate fact for the same entity that bridges the
units (e.g. Rate(entity='machine', measure='hour', per='day', value=4)
bridging a 'day' span to an 'hour'-per rate) is multiplied through. A
text-stated bridge takes priority over a generic reg.conversions entry for
the same units (a day is 24 hours in general, but the text may state the
entity only runs some of them) — but only when the bridge is UNIQUE;
otherwise (or when no bridge exists at all) behavior falls through
untouched to the original single-rate path. Synthetic only."""

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


def test_chained_rate_span(full_registry):
    # 30 pages/hour x 4 hours/day x 3 days = 360
    r = solve(
        "A machine makes 30 coins an hour. The machine runs 4 hours a day. "
        "How many coins does the machine make in 3 days?",
        full_registry,
    )
    assert r.answer.value == 360


def test_stated_bridge_overrides_generic_conversion(full_registry):
    # day -> hour has a generic 24x conversion in packs/difg-mined, but
    # THIS text states the machine only runs 4 hours a day — the stated
    # bridge must win, not the physical unit conversion (which would give
    # the wrong-but-plausible 30 * 24 * 3 = 2160).
    r = solve(
        "A machine makes 30 coins an hour. The machine runs 4 hours a day. "
        "How many coins does the machine make in 3 days?",
        full_registry,
    )
    assert r.answer.value == 360
    assert r.answer.value != 30 * 24 * 3


def test_single_rate_exact_unit_span_unchanged(full_registry):
    # no bridge involved at all (span_unit == rate.per) — untouched path
    r = solve("Tom finds 3 coins a day. How many coins does Tom find in 5 days?", full_registry)
    assert r.answer.value == 15


def test_single_rate_generic_conversion_still_applies(full_registry):
    # no bridge Rate fact exists for this entity — falls through to the
    # original reg.conversions path, byte-for-byte
    r = solve(
        "Lisa walks 10 meters a minute. How many meters does Lisa walk in 2 hours?",
        full_registry,
    )
    assert r.answer.value == 1200


def test_no_bridge_and_no_conversion_still_declines(full_registry):
    r = solve(
        "Tom finds 3 coins a day. How many coins does Tom find in 5 gallons?",
        full_registry,
    )
    assert r.answer.kind == "decline"
    assert "conversion" in r.answer.reason


def test_ambiguous_bridge_declines(full_registry):
    # two candidate bridge rates for the same entity/units — must not
    # silently pick one; decline-safety over a coverage guess
    r = solve(
        "A machine makes 30 coins an hour. The machine runs 4 hours a day. "
        "The machine works 5 hours a day. "
        "How many coins does the machine make in 3 days?",
        full_registry,
    )
    assert r.answer.kind == "decline"
