"""Mining candidate extraposed-duration-rates: the extraposed-infinitive
duration idiom ("it takes/took WHO N TIMEUNIT to VERB M ITEM") as a
PREMISE, not just an ask. Registers `rate` as a pattern-emittable fact
kind (patterns.py `_FACT_CLASSES`, schemas.py `FactEmit.fact`) and adds
`arithmetic/extraposed-duration-rate`, a new pattern rule emitting a
COMPOUND Rate (value = item/span, numerator/denominator preserved for
value-accounting) exactly like learn.py's `_compound_rate_span` SVO
branch, just SVO-inverted. Infrastructure only: the existing
rate-span-inverse consumer (answer.py) already resolves the inverse span
ask the instant a matching Rate exists; this rule only supplies the
missing Rate for the premise side of the idiom. Synthetic only."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Predication, Quantity, Rate

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def full_registry():
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", mined])
    )


def test_extraposed_present_tense_emits_compound_rate(full_registry):
    r = solve("It takes Priya 10 minutes to wash 4 windows.", full_registry)
    rates = [f for f in r.store.facts if isinstance(f, Rate)]
    assert len(rates) == 1
    rate = rates[0]
    assert rate.entity == "priya"
    assert rate.measure == "window"
    assert rate.per == "minute"
    assert rate.value == pytest.approx(0.4)
    assert rate.numerator == pytest.approx(4.0)
    assert rate.denominator == pytest.approx(10.0)


def test_extraposed_past_tense_also_gates(full_registry):
    # 'took' (past) must gate the same as 'takes' (present) — the
    # `duration_verb` category, not a single literal, is what lets a
    # declarative premise inflect for tense.
    r = solve("It took Omar 5 hours to build 20 chairs.", full_registry)
    rates = [f for f in r.store.facts if isinstance(f, Rate)]
    assert len(rates) == 1
    assert rates[0].value == pytest.approx(4.0)


def test_extraposed_rate_chains_through_inverse_span_ask(full_registry):
    # the enabler's whole point: the pre-existing rate-span-inverse
    # consumer (ask/how-long-take-span) commits the moment the premise
    # supplies a matching Rate — no consumer change in this increment.
    r = solve(
        "It takes Priya 10 minutes to wash 4 windows. "
        "How many minutes will it take Priya to wash 64 windows?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == pytest.approx(160.0)


def test_extraposed_rate_chains_through_how_long_ask(full_registry):
    r = solve(
        "It took Omar 5 hours to build 20 chairs. "
        "How long did it take Omar to build 20 chairs?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == pytest.approx(5.0)


def test_extraposed_without_counted_item_declines_no_rate(full_registry):
    # decline-safety: no counted item after the infinitive (a bare
    # activity, "finish the marathon") must NOT emit a Rate — the rule's
    # own `item, type: counted` slot simply fails to match, so today's
    # ordinary fold (a Predication, not a duration holding) is untouched.
    r = solve("It took Omar 5 hours to finish the marathon.", full_registry)
    rates = [f for f in r.store.facts if isinstance(f, Rate)]
    assert rates == []
    assert any(isinstance(f, Predication) for f in r.store.facts)


def test_extraposed_svo_duration_fold_suppressed(full_registry):
    # decline-safety / fold-conflict prevention: once the compound Rate
    # is emitted, the infinitive clause's counted item must NOT ALSO fold
    # as a bare Quantity holding on the entity (pattern_consumed masks
    # the redundant SVO fold) — a compound rate is never a holding.
    r = solve("It takes Priya 10 minutes to wash 4 windows.", full_registry)
    windows = [
        f for f in r.store.facts if isinstance(f, Quantity) and f.measure == "window"
    ]
    assert windows == []
