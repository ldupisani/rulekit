"""Mining increment 128: entity-less and in-place
totality asks over a distributive container premise.

`_combined_holder_totals`'s entity enumeration (answer.py) used to oversum
whenever `saturate.py`'s synth/container-contents bridged a per-unit rate
fact ("each X is N Y") into two or more holders' totals: the RATE fact's
own raw entity ("X") kept counting as a THIRD independent holder alongside
the two bridged totals it was actually consumed to derive, inflating the
combined sum. This fix marks the (entity, measure) key of any Quantity a
bridging synth consumed to derive another holder's total
(`ArithmeticLog.consumed_rate_keys`, populated only at the synth's own
emission site) and drops it from holder enumeration — the same
USE-vs-EXISTENCE distinction already applied to value accounting for
Rate/Price/GroupTotal, applied here to holder enumeration instead.

Also exercises the newly re-landed `ask/how-long-is-total-dimension`
("How long is the total X?"), which binds `measure: time_measure`
directly and was blocked on this exact oversum.

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


def test_dimension_totality_ask_excludes_rate_defining_holder(full_registry):
    # "Each clip is 5 minutes" bridges into TWO holders (30, 20); the rate
    # fact's own entity ('clip') must not be summed in as a spurious third
    # holder (30 + 20 + 5 = 55, the documented oversum) — gold is 50.
    r = solve(
        "The first section has 6 clips. The second section has 4 clips. "
        "Each clip is 5 minutes. How long is the total video?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 50


def test_preexisting_combined_ask_also_excludes_rate_defining_holder(full_registry):
    # the SAME fix, reached through a pre-existing entity-less ask
    # (ask/how-many-there-combined) rather than the new dimension ask —
    # proves the fix lives in the shared holder-enumeration helper, not in
    # the new ask's own wiring.
    r = solve(
        "The first section has 6 clips. The second section has 4 clips. "
        "Each clip is 5 minutes. How many minutes are there in total?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 50


def test_single_bridged_holder_still_declines(full_registry):
    # decline-safety: only ONE section, so after the rate-defining 'clip'
    # entity is excluded, exactly one holder remains — a combined ask
    # asserts plurality, so this must still decline exactly as before this
    # fix, never silently answer with a single holder's total.
    r = solve(
        "The first section has 6 clips. Each clip is 5 minutes. "
        "How long is the total video?",
        full_registry,
    )
    assert r.answer.kind == "decline"
