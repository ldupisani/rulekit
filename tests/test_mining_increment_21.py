"""Mining candidate wage-span-earnings: wage earnings asks ("how much
does WHO earn/make (in SPAN)?" — a Rate x worked-span product).

Before this increment, 'how much does X earn/make' routed to the general
event-fold ask (single-entity/bare-entity), which only sums literal
earn/make EVENTS — it never reached the rate-span consumer even when a
Rate fact ("$10 an hour") and a worked span ("Rob works 8 hours") were
both known. A new ask (packs/arithmetic/rules/core.yaml, ask/earn-span)
gates the verb slot on the narrow wage_verb category
(packs/difg-mined/categories/wage.yaml: earn/earns/earned/make/makes/made)
and routes to the SAME rate-span consumer used since increments 8-9,
untouched in its unique-rate/bridging/conversion discipline. The 'in
SPAN' clause is optional; when absent, the consumer (a small, general
extension — not specific to earn/make) reads the span off a standalone
quantity fact for the entity in the rate's own per-unit, on the same
unique-fact-or-decline discipline as the existing bridge lookup.

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


def test_earn_span_from_separate_sentence(full_registry):
    # the span is stated in its OWN sentence, not inside the question —
    # the gap the event-fold ask could never close
    r = solve(
        "Rob earns 10 dollars per hour. Rob works 8 hours. "
        "How much does Rob earn?",
        full_registry,
    )
    assert r.answer.value == 80


def test_make_span_in_question(full_registry):
    # 'make' is the other wage_verb; the span may still be named directly
    # in the question, exactly like the pre-existing rate-span ask
    r = solve(
        "Tina makes $18 an hour. How much does Tina make in 40 hours?",
        full_registry,
    )
    assert r.answer.value == 720


def test_conversion_span_still_applies(full_registry):
    # the reused consumer's conversion discipline (span_unit != rate.per)
    # fires unchanged through the new ask
    r = solve(
        "Lena earns $3 a minute. How much does Lena earn in 2 hours?",
        full_registry,
    )
    assert r.answer.value == 360


def test_no_span_at_all_declines(full_registry):
    # a rate with NO worked-span fact anywhere — the consumer's own
    # decline, not a crash
    r = solve("Rob earns 10 dollars per hour. How much does Rob earn?", full_registry)
    assert r.answer.kind == "decline"


def test_ambiguous_span_declines(full_registry):
    # two candidate per-unit quantity facts for the same entity — the
    # unique-fact-or-decline discipline refuses to guess
    r = solve(
        "Rob earns 10 dollars per hour. Rob works 8 hours on Monday. "
        "Rob works 5 hours on Tuesday. How much does Rob earn?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_unrelated_verb_never_matches_wage_gate(full_registry):
    # decline-safety: a non-wage acquire verb ('buy') must not be pulled
    # into the rate-span ask just because a Rate fact happens to exist
    r = solve(
        "Rob earns 10 dollars per hour. Rob buys a book. "
        "How much does Rob buy?",
        full_registry,
    )
    assert r.answer.kind == "decline"
