"""Mining candidate duration-inverse-rate-asks: inverse rate-span (duration)
asks ("how long / how many TIMEUNIT does it take WHO to VERB N ITEM?" =
asked amount ÷ rate).

Before this increment, the rate-span asks (increments 8/9/13/21) only ever
went FORWARD — a known span times a known Rate. The INVERSE direction ("how
long does it take Tom to read 20 pages?", given "Tom reads 5 pages per
hour") declined "no ask shape" even though the premises fully determine the
answer: only the ask forms and the division were missing.

Two new ask ids (packs/arithmetic/rules/core.yaml):
  - ask/how-long-take-span: "how long does/did it take WHO to VERB N ITEM?"
    — the span is asked in the rate's own per-unit implicitly.
  - ask/how-many-timeunit-take-span: "how many TIMEUNIT does/did it take
    WHO to VERB N ITEM?" — the time unit is named explicitly and must match
    the committing rate's per-unit, or the ask declines.

Both route to a NEW, additive consumer (rate-span-inverse, answer.py) — the
existing forward 'rate-span' consumer/branch is untouched byte-for-byte.
"it take" is structural skeleton (the extraposed-infinitive idiom); the aux
slot is restricted to the auxiliary sense (do/does/did), so a will-phrased
"how long will it take" structurally cannot match here ('will' is tagged
'modal', not 'auxiliary', since increment 14) — this keeps the class
disjoint from the separate will-tense-asks mining candidate.

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


def test_how_long_divides_amount_by_rate(full_registry):
    r = solve(
        "Sana reads 5 pages per hour. How long does it take Sana to read "
        "20 pages?",
        full_registry,
    )
    assert r.answer.value == 4


def test_how_long_with_did_past_tense(full_registry):
    r = solve(
        "Sana reads 5 pages per hour. How long did it take Sana to read "
        "20 pages?",
        full_registry,
    )
    assert r.answer.value == 4


def test_how_many_timeunit_matching_rate_per_unit(full_registry):
    r = solve(
        "Sana reads 5 pages per hour. How many hours does it take Sana to "
        "read 20 pages?",
        full_registry,
    )
    assert r.answer.value == 4


def test_how_many_timeunit_mismatched_unit_declines(full_registry):
    # the asked unit ('minutes') doesn't match the rate's own per-unit
    # ('hour') — the inverse ask does no conversion, only a direct match
    r = solve(
        "Sana reads 5 pages per hour. How many minutes does it take Sana "
        "to read 20 pages?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_no_rate_known_declines(full_registry):
    r = solve(
        "Sana has 20 pages. How long does it take Sana to read 20 pages?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_ambiguous_rate_declines(full_registry):
    # two candidate rates for the same entity/measure — unique-rate-or-
    # decline discipline (the same one the forward branch uses)
    r = solve(
        "Sana reads 5 pages per hour. Sana reads 8 pages per hour on "
        "weekends. How long does it take Sana to read 20 pages?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_per_individual_rate_declines_no_population_attempt(full_registry):
    # a per-individual rate ("a bird eats 7 berries a day") entangles a
    # population the inverse branch deliberately does not attempt
    r = solve(
        "A bird eats 7 berries a day. There are 3 birds. How long does it "
        "take a bird to eat 7 berries?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_will_phrased_form_does_not_match(full_registry):
    # decline-safety: 'will' is tagged 'modal' (increment 14), never
    # 'auxiliary' — this ask cannot match a will-phrased duration question,
    # keeping the class disjoint from the separate will-tense-asks
    # candidate. The forward ask/how-many-rate-span also can't answer it
    # (no 'in SPAN' clause is stated), so the whole item safely declines.
    r = solve(
        "Sana reads 5 pages per hour. How long will it take Sana to read "
        "20 pages?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_forward_rate_span_ask_unaffected(full_registry):
    # regression: the pre-existing FORWARD rate-span ask (increments 8/9)
    # still answers exactly as before this change
    r = solve(
        "Sana reads 5 pages per hour. How many pages does Sana read in 3 "
        "hours?",
        full_registry,
    )
    assert r.answer.value == 15
