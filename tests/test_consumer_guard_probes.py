"""Direct probes for the guards NO text can reach — the guard-gap closure.

Session 3 left 41 of answer.py's 90 guards without a probe. 18 turned out to
be reachable from text after all and became golden-master rows
(tests/test_consumer_golden_master.py); the 23 here could not be phrased, and
each section states the structural reason. The pattern is
tests/test_consumer_molar_mass.py's: call the extracted consumer directly
through `ConsumerContext`, trip the branch, assert the decline — possible at
all only because the consumers are now functions.

Every entry here is mirrored in the golden master's `_COVERED_BY_UNIT_TEST`,
so the coverage ledger counts these guards as reached without pretending a
golden row exists. All input strings are SYNTHETIC (constitution rule 3).

WHY THE VERDICT CONSUMERS' "question states" GUARDS ARE HERE: the full-read
contract they re-check is enforced STRUCTURALLY by the matcher — a FINAL span
must run to the sentence end and may never swallow a `span_blocks` word
(patterns._try_match_at), and every verdict ask anchors `at_start` — so a
question that matches while leaving a meaningful unit unread cannot occur
from text. Probing them means handing the consumer a real match whose
`consumed` tuple was truncated, which is exactly the state the guard defends
against: a future matcher change (or a new ask shape without a final span)
that starts producing partial reads.
"""

import dataclasses
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.consumers import CONSUMERS, ConsumerContext
from rulekit.kernel.engine import analyze, solve
from rulekit.kernel.evaluate import ArithmeticLog
from rulekit.kernel.facts import FactStore
from rulekit.kernel.model import (
    AgeAtYear,
    ContainerCapacityInquiry,
    ContainerCapacityObservation,
    Goal,
    MeasuredContentChange,
    PartitionQuantity,
    Predication,
    Provenance,
    Quantity,
    Rate,
    SpatialPlacement,
)
from rulekit.kernel.patterns import SKIPPABLE_SENSES, match_ask

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def gsm8k():
    return load_project(ROOT / "projects" / "gsm8k").registry


@pytest.fixture(scope="module")
def scratch():
    return load_project(ROOT / "projects" / "scratch").registry


@pytest.fixture(scope="module")
def curated():
    return load_project(ROOT / "projects" / "curated").registry


def call(
    name,
    reg,
    query,
    question=None,
    store=None,
    match=None,
    ask=None,
    reference_year=None,
    premises=(),
):
    """Invoke a consumer directly. Fields default to None so a consumer that
    starts reading state its guard never needed fails loudly here rather than
    silently exercising a different path (the molar-mass file's discipline)."""
    return CONSUMERS[name](ConsumerContext(
        query=query, question=question, store=store, reg=reg,
        log=ArithmeticLog(), match=match, ask=ask,
        reference_year=reference_year,
        premises=tuple(premises),
    ))


def _capacity_store(*facts):
    return FactStore(facts=list(facts))


def test_calendar_rate_needs_source_evidence(curated):
    # A direct caller can provide a Rate without its source reading. Calendar
    # composition must not invent a complete source clause for that fact.
    rate = Rate(Provenance(source="synthetic", sentence=0), "nora", "book", "day", 10)
    got = call(
        "calendar-resource-total",
        curated,
        {"operation": "week"},
        store=FactStore(facts=[rate]),
    )
    assert got.kind == "decline"
    assert got.reason == "each ordinary rate must have a complete, unqualified source clause"


def _capacity_context(reg, *facts, allow_confirmed_fit=False):
    query = {"container": "jar", "measure": "coin"}
    if allow_confirmed_fit:
        query["allow_confirmed_fit"] = "true"
    return call(
        "container-capacity-observation",
        reg,
        query,
        store=_capacity_store(*facts),
    )


# Capacity asks reach only well-formed inquiry/observation facts through text.
# Direct stores probe the consumer's defensive cardinality, mode, arithmetic,
# and evidence-strength restatements without inventing public grammar for
# malformed facts.


def test_capacity_needs_one_inquiry_context(curated):
    got = _capacity_context(curated)
    assert got.kind == "decline"
    assert "one compatible inquiry context; found 0" in got.reason


def test_capacity_needs_one_fill_observation(curated):
    provenance = Provenance(source="synthetic", sentence=0)
    got = _capacity_context(
        curated,
        ContainerCapacityInquiry(provenance, "bira", "jar", "coin"),
    )
    assert got.kind == "decline"
    assert "one compatible fill observation; found 0" in got.reason


def test_capacity_needs_a_complete_available_total(curated):
    provenance = Provenance(source="synthetic", sentence=0)
    got = _capacity_context(
        curated,
        ContainerCapacityInquiry(provenance, "bira", "jar", "coin"),
        ContainerCapacityObservation(
            provenance, "coin", "all_available_fit", 0, "jar"
        ),
    )
    assert got.kind == "decline"
    assert "no complete available total" in got.reason


def _complete_capacity_store(mode, value=0):
    provenance = Provenance(source="synthetic", sentence=0)
    return (
        ContainerCapacityInquiry(provenance, "bira", "jar", "coin"),
        ContainerCapacityObservation(provenance, "coin", mode, value, "jar"),
        Quantity(provenance, "bira", "coin", 10),
    )


def test_all_fit_is_not_exact_capacity_evidence(curated):
    got = _capacity_context(
        curated, *_complete_capacity_store("all_available_fit")
    )
    assert got.kind == "decline"
    assert "confirmed amount, not exact capacity" in got.reason


def test_capacity_remainder_must_be_within_the_available_total(curated):
    got = _capacity_context(
        curated, *_complete_capacity_store("remainder_after_fill", 11)
    )
    assert got.kind == "decline"
    assert "remainder 11 is outside available total 10" in got.reason


def test_capacity_rejects_an_unknown_observation_mode(curated):
    got = _capacity_context(curated, *_complete_capacity_store("estimated"))
    assert got.kind == "decline"
    assert "unsupported capacity observation 'estimated'" in got.reason


def test_capacity_arithmetic_failure_declines(curated):
    got = _capacity_context(
        curated, *_complete_capacity_store("remainder_after_fill", float("nan"))
    )
    assert got.kind == "decline"
    assert "capacity arithmetic failed" in got.reason


# --- typed/category-gated slots: a non-numeric value or unknown op word ----
# never binds at the ask, so these branches are defensive re-checks.


def test_affine_convert_needs_a_numeric_quantity(gsm8k):
    got = call("affine-convert", gsm8k,
               {"value": "lots", "from": "celsius", "to": "fahrenheit"})
    assert got.kind == "decline"
    assert "a conversion needs a numeric quantity" in got.reason


def test_unit_convert_needs_a_numeric_quantity(gsm8k):
    got = call("unit-convert", gsm8k,
               {"value": "lots", "from": "pound", "to": "kilogram"})
    assert got.kind == "decline"
    assert "a conversion needs a numeric quantity" in got.reason


def test_rate_cost_needs_a_quantity_and_a_rate(gsm8k):
    got = call("rate-cost", gsm8k,
               {"value": "lots", "rate": "2", "from": "mile", "to": "mile"})
    assert got.kind == "decline"
    assert "a rate cost needs a quantity and a rate" in got.reason


def _progress_query(**updates):
    query = {
        "entity": "cato",
        "measure": "page",
        "verb": "read",
        "fraction": "0.5",
        "target_time": "tomorrow",
        "product_category": "content_progress_product",
        "capacity_verb": "have",
    }
    query.update(updates)
    return query


def _progress_store(*, capacity=None, completed=None):
    provenance = Provenance(source="synthetic", sentence=0)
    facts = [
        Predication(
            provenance=provenance,
            subject="cato",
            verb="read",
            dobj="book",
        )
    ]
    if capacity is not None:
        facts.append(Quantity(
            provenance=provenance,
            entity="book",
            measure="page",
            value=capacity,
            verb="have",
        ))
    if completed is not None:
        facts.append(Quantity(
            provenance=provenance,
            entity="cato",
            measure="page",
            value=completed,
            verb="read",
            occurrence=0,
        ))
    return FactStore(facts=facts)


def test_progress_remainder_needs_a_readable_fraction(curated):
    got = call(
        "content-progress-remainder-fraction",
        curated,
        _progress_query(fraction="several"),
        store=FactStore(),
    )
    assert got.kind == "decline"
    assert "fraction is unreadable" in got.reason


def test_progress_remainder_rejects_fraction_beyond_whole(curated):
    got = call(
        "content-progress-remainder-fraction",
        curated,
        _progress_query(fraction="1.5"),
        store=FactStore(),
    )
    assert got.kind == "decline"
    assert "outside one whole" in got.reason


def test_progress_remainder_needs_a_future_target(curated):
    got = call(
        "content-progress-remainder-fraction",
        curated,
        _progress_query(target_time="today"),
        store=FactStore(),
    )
    assert got.kind == "decline"
    assert "needs one declared future marker" in got.reason


def test_progress_remainder_rejects_an_ambiguous_measure(gsm8k):
    provenance = Provenance(source="synthetic", sentence=0)
    store = FactStore(facts=[
        Quantity(provenance, "box", "dollar", 3),
        Quantity(provenance, "box", "pound", 4),
    ])
    got = call(
        "content-progress-remainder-fraction",
        gsm8k,
        _progress_query(measure="money"),
        store=store,
    )
    assert got.kind == "decline"
    assert "measure 'money' is ambiguous" in got.reason


def test_progress_remainder_needs_one_linked_product(curated):
    got = call(
        "content-progress-remainder-fraction",
        curated,
        _progress_query(),
        store=FactStore(),
    )
    assert got.kind == "decline"
    assert "0 measured products" in got.reason


def test_progress_remainder_needs_one_capacity(curated):
    got = call(
        "content-progress-remainder-fraction",
        curated,
        _progress_query(),
        store=_progress_store(),
    )
    assert got.kind == "decline"
    assert "0 capacities known" in got.reason


def test_progress_remainder_needs_completed_progress(curated):
    got = call(
        "content-progress-remainder-fraction",
        curated,
        _progress_query(),
        store=_progress_store(capacity=30),
    )
    assert got.kind == "decline"
    assert "completed 'read' progress is not uniquely determined" in got.reason


def test_progress_remainder_rejects_progress_beyond_capacity(curated):
    got = call(
        "content-progress-remainder-fraction",
        curated,
        _progress_query(),
        store=_progress_store(capacity=10, completed=12),
    )
    assert got.kind == "decline"
    assert "completed progress 12" in got.reason


def _event_period_query(**updates):
    query = {
        "entity": "cato",
        "measure": "page",
        "verb": "read",
        "periods": ["march", "april"],
    }
    query.update(updates)
    return query


def test_event_period_total_needs_two_distinct_periods(curated):
    got = call(
        "event-period-total",
        curated,
        _event_period_query(periods=["march"]),
        store=FactStore(),
    )
    assert got.kind == "decline"
    assert "needs two or more distinct named periods" in got.reason


def test_event_period_total_rejects_an_ambiguous_measure(gsm8k):
    provenance = Provenance(source="synthetic", sentence=0)
    store = FactStore(facts=[
        Quantity(provenance, "cato", "dollar", 3, verb="read", time="march"),
        Quantity(provenance, "cato", "pound", 4, verb="read", time="march"),
    ])
    got = call(
        "event-period-total",
        gsm8k,
        _event_period_query(measure="money"),
        store=store,
    )
    assert got.kind == "decline"
    assert "measure 'money' is ambiguous" in got.reason


def test_event_period_total_rejects_state_evidence(curated):
    provenance = Provenance(source="synthetic", sentence=0)
    store = FactStore(facts=[
        Quantity(provenance, "cato", "page", 3, verb="read", time="march"),
    ])
    got = call(
        "event-period-total",
        curated,
        _event_period_query(),
        store=store,
    )
    assert got.kind == "decline"
    assert "requires event evidence, not snapshots" in got.reason


def test_event_period_total_requires_each_requested_period(curated):
    provenance = Provenance(source="synthetic", sentence=0)
    store = FactStore(facts=[
        Quantity(
            provenance,
            "cato",
            "page",
            3,
            verb="read",
            time="march",
            occurrence=0,
        ),
    ])
    got = call(
        "event-period-total",
        curated,
        _event_period_query(),
        store=store,
    )
    assert got.kind == "decline"
    assert "no direct event evidence for requested period(s): april" in got.reason


def test_arithmetic_unsupported_operation(gsm8k):
    got = call("arithmetic", gsm8k, {"op": "frobnicate", "x": "1", "y": "2"})
    assert got.kind == "decline"
    assert "unsupported operation 'frobnicate'" in got.reason


def test_number_theory_unsupported_operation(gsm8k):
    got = call("number-theory", gsm8k, {"op": "frobnicate", "x": "4", "y": "2"})
    assert got.kind == "decline"
    assert "unsupported operation 'frobnicate'" in got.reason


def test_coordinate_unsupported_operation(gsm8k):
    got = call("coordinate", gsm8k,
               {"op": "frobnicate", "p1": "1,2", "p2": "3,4"})
    assert got.kind == "decline"
    assert "unsupported operation 'frobnicate'" in got.reason


def test_trigonometry_unsupported_operation(gsm8k):
    got = call("trigonometry", gsm8k, {"op": "frobnicate", "x": "45"})
    assert got.kind == "decline"
    assert "unsupported operation 'frobnicate'" in got.reason


def test_measure_cost_unsupported_operation(gsm8k):
    got = call("measure-cost", gsm8k,
               {"op": "diagonal", "d1": "2", "d2": "3", "rate": "4"})
    assert got.kind == "decline"
    assert "unsupported measure operation 'diagonal'" in got.reason


def test_measure_cost_unreadable_tax(gsm8k):
    # the ask binds tax as a counted slot; only a direct call can hand the
    # consumer a tax it cannot read — the guard exists so a bound-but-broken
    # tax declines rather than silently answering the UNTAXED total
    got = call("measure-cost", gsm8k,
               {"op": "area", "d1": "2", "d2": "3", "rate": "4", "tax": "high"})
    assert got.kind == "decline"
    assert "unreadable tax rate 'high'" in got.reason


def test_physics_no_formula_for_the_quantity(gsm8k):
    # the ask gates the quantity word on the formula categories, so a word
    # with no formula never binds from text
    got = call("physics", gsm8k, {"quantity": "flavor"})
    assert got.kind == "decline"
    assert "no formula for the 'flavor' of a thing" in got.reason


def test_age_projected_without_an_offset(gsm8k):
    # both age-projected asks bind the offset as a REQUIRED counted slot
    got = call("age-projected", gsm8k, {"entity": "deja", "measure": "year"})
    assert got.kind == "decline"
    assert "projected age ask has no stated year offset" in got.reason


def test_age_at_year_needs_all_required_query_fields(curated):
    got = call("age-at-year", curated, {"entity": "", "measure": "year"})
    assert got.kind == "decline"
    assert "needs an entity, measure, and target year" in got.reason


def test_age_at_year_needs_a_readable_target_year(curated):
    got = call(
        "age-at-year",
        curated,
        {"entity": "cato", "measure": "year", "target_year": "blorp"},
    )
    assert got.kind == "decline"
    assert "as a calendar year" in got.reason


def test_age_at_year_rejects_an_invalid_source_coordinate(curated):
    store = FactStore(facts=[
        AgeAtYear(
            provenance=Provenance(source="synthetic", sentence=0),
            entity="cato",
            measure="year",
            value=20,
            year=1999.5,
        )
    ])
    got = call(
        "age-at-year",
        curated,
        {"entity": "cato", "measure": "year", "target_year": "2022"},
        store=store,
    )
    assert got.kind == "decline"
    assert "invalid dated age source" in got.reason


def test_age_at_year_group_needs_distinct_entities(curated):
    got = call(
        "age-at-year",
        curated,
        {
            "holders": ["cato", "cato"],
            "measure": "year",
            "target_marker": "now",
        },
        reference_year=2026,
    )
    assert got.kind == "decline"
    assert "at least two distinct entities" in got.reason


def test_age_at_year_rejects_a_noncurrent_deictic_marker(curated):
    got = call(
        "age-at-year",
        curated,
        {
            "holders": ["cato", "dena"],
            "measure": "year",
            "target_marker": "tomorrow",
        },
        reference_year=2026,
    )
    assert got.kind == "decline"
    assert "is not a current-year age marker" in got.reason


def test_age_at_year_group_rejects_ambiguous_holder_identity(curated):
    store = FactStore(facts=[
        AgeAtYear(
            provenance=Provenance(source="synthetic-a", sentence=0),
            entity="child",
            measure="year",
            value=10,
            year=2010,
            owner="alex",
        ),
        AgeAtYear(
            provenance=Provenance(source="synthetic-b", sentence=1),
            entity="child",
            measure="year",
            value=12,
            year=2010,
            owner="blair",
        ),
    ])
    got = call(
        "age-at-year",
        curated,
        {
            "holders": ["child", "teacher"],
            "measure": "year",
            "target_marker": "now",
        },
        store=store,
        reference_year=2026,
    )
    assert got.kind == "decline"
    assert "identity is ambiguous for 'child'" in got.reason


def test_age_at_year_rejects_an_unknown_group_aggregate(curated):
    got = call(
        "age-at-year",
        curated,
        {
            "holders": ["child", "teacher"],
            "measure": "year",
            "target_year": "2020",
            "aggregate": "median",
        },
    )
    assert got.kind == "decline"
    assert "unsupported dated age aggregate 'median'" in got.reason


# --- guards that read the QUESTION's number list ---------------------------
# The asks only match a question that carries the numbers, so an empty list
# cannot arrive from text; a real numberless Reading stands in.


def test_list_statistic_with_no_numbers(gsm8k):
    res = solve("Is Ana a student?", gsm8k, tracing=False)
    got = call("list-statistic", gsm8k, {"stat": "average"}, question=res.question)
    assert got.kind == "decline"
    assert "no numbers to take the 'average' of" in got.reason


def test_list_statistic_unsupported_statistic(gsm8k):
    res = solve("What is the average of 10, 20, and 30?", gsm8k, tracing=False)
    got = call("list-statistic", gsm8k, {"stat": "spread"}, question=res.question)
    assert got.kind == "decline"
    assert "unsupported statistic 'spread'" in got.reason


def test_vector_with_no_components(gsm8k):
    res = solve("Is Ana a student?", gsm8k, tracing=False)
    got = call("vector", gsm8k, {"op": "magnitude"}, question=res.question)
    assert got.kind == "decline"
    assert "no components to take the 'magnitude' of" in got.reason


def test_vector_unsupported_operation(gsm8k):
    res = solve("What is the dot product of (1, 0, 2) and (3, 7, 4)?",
                gsm8k, tracing=False)
    got = call("vector", gsm8k, {"op": "frobnicate"}, question=res.question)
    assert got.kind == "decline"
    assert "unsupported operation 'frobnicate'" in got.reason


# --- the interchangeable-measure ambiguity ---------------------------------
# `currency` is the only interchangeable category, and no ask reaching these
# two consumers can bind its factless member ('money' — deficit asks want
# "how MANY more", unique-entity asks a counted noun). The store is real; the
# query word is the one the asks cannot deliver.


@pytest.fixture(scope="module")
def mixed_currency_store(gsm8k):
    return solve("Tom has 3 dollars. Tom has 2 pounds.", gsm8k, tracing=False).store


def test_deficit_ambiguous_measure(gsm8k, mixed_currency_store):
    got = call("deficit", gsm8k, {"entity": "tom", "measure": "money"},
               store=mixed_currency_store)
    assert got.kind == "decline"
    assert "measure 'money' is ambiguous across the facts" in got.reason


def test_deficit_contribution_path_requires_one_safe_current_total(gsm8k):
    provenance = Provenance(source="synthetic", sentence=0)
    store = FactStore(
        facts=[
            Goal(provenance, "tom", "dollar", 20, target="shoe"),
            Quantity(provenance, "tom", "dollar", 5, verb="have"),
            Quantity(
                provenance,
                "tom",
                "dollar",
                2,
                verb="frobnicate",
                occurrence=1,
            ),
        ]
    )

    got = call(
        "deficit",
        gsm8k,
        {
            "entity": "tom",
            "measure": "dollar",
            "target": "shoe",
            "include_contributions": "true",
        },
        store=store,
    )

    assert got.kind == "decline"
    assert "current holdings for 'tom'/'dollar' do not form one safe total" in (
        got.reason
    )


def test_unique_entity_ambiguous_measure(gsm8k, mixed_currency_store):
    got = call("unique-entity", gsm8k, {"measure": "money"},
               store=mixed_currency_store)
    assert got.kind == "decline"
    assert "measure 'money' is ambiguous across the facts" in got.reason


# --- the verdict consumers' full-read re-check -----------------------------
# See the module docstring: the matcher enforces the contract structurally,
# so the guard is probed by truncating a REAL match's consumed tuple.


def _partially_read(reg, text, expected_consumer):
    res = solve(text, reg, tracing=False)
    assert res.question is not None, text
    matched = match_ask(res.question, reg)
    assert matched is not None and matched[1].get("consumer") == expected_consumer
    ask, query, match = matched
    dropped = next(
        u for u in res.question.units
        if u.uid in match.consumed and u.sense() not in SKIPPABLE_SENSES
    )
    truncated = dataclasses.replace(
        match, consumed=tuple(c for c in match.consumed if c != dropped.uid)
    )
    return query, res, truncated, ask, dropped


VERDICT_QUESTIONS = [
    ("existential-verdict", "Is it true that A dog eats apples?"),
    ("logic-disjunction-verdict", "Is it true that Rex is a dog or a cat?"),
    ("logic-verdict", "Is it true that Ana is a Rovers player?"),
    ("passive-agent-verdict",
     "Is it true that Oxford Circus is designed by a British musician?"),
    ("universal-verdict", "Is it true that All dogs are mammals?"),
    ("verbal-obj-class-verdict", "Is it true that Rex does not play for a farmer?"),
]


@pytest.mark.parametrize("consumer_name, text", VERDICT_QUESTIONS,
                         ids=[c for c, _ in VERDICT_QUESTIONS])
def test_a_partially_read_verdict_question_declines(scratch, consumer_name, text):
    query, res, truncated, ask, dropped = _partially_read(scratch, text, consumer_name)
    got = call(consumer_name, scratch, query, question=res.question,
               store=res.store, match=truncated, ask=ask)
    assert got.kind == "decline"
    assert "question states" in got.reason
    assert dropped.surface in got.reason


# --- location-witnesses: group membership and day grain are resolution-time
# contracts, while full question consumption is matcher-enforced. Direct calls
# prove the defensive re-checks without inventing an ask surface that cannot
# route there.

LOCATION_TEXT = (
    "Aven arrived at the garden yesterday. "
    "Bira arrived at the garden today. "
    "Which of them are at the garden today?"
)


def _location_context(curated):
    result = solve(LOCATION_TEXT, curated, tracing=False)
    matched = match_ask(result.question, curated)
    assert matched is not None
    ask, query, match = matched
    assert query["consumer"] == "location-witnesses"
    return result, ask, query, match


def test_location_witnesses_needs_an_exact_group(curated):
    result, ask, query, match = _location_context(curated)
    got = call(
        "location-witnesses",
        curated,
        {**query, "candidates": []},
        question=result.question,
        store=result.store,
        match=match,
        ask=ask,
    )
    assert got.kind == "decline"
    assert "needs one exact group" in got.reason


def test_location_witnesses_needs_a_declared_day(curated):
    result, ask, query, match = _location_context(curated)
    got = call(
        "location-witnesses",
        curated,
        {**query, "when": "now"},
        question=result.question,
        store=result.store,
        match=match,
        ask=ask,
    )
    assert got.kind == "decline"
    assert "needs one declared day and place" in got.reason


def test_a_partially_read_location_question_declines(curated):
    query, result, truncated, ask, dropped = _partially_read(
        curated,
        LOCATION_TEXT,
        "location-witnesses",
    )
    got = call(
        "location-witnesses",
        curated,
        query,
        question=result.question,
        store=result.store,
        match=truncated,
        ask=ask,
    )
    assert got.kind == "decline"
    assert "question states" in got.reason
    assert dropped.surface in got.reason


# --- reference-lookup: both asks bind attribute (category-gated) and entity
# (name slot) as REQUIRED slots, and the year arrives via "{y.value}" off a
# number-typed slot — so an empty attribute/entity or a non-numeric year
# cannot be phrased. Direct probes, the affine-convert pattern.

def test_reference_lookup_empty_slots_decline(gsm8k):
    got = call("reference-lookup", gsm8k, {"attribute": "", "entity": ""})
    assert got.kind == "decline"
    assert "needs an attribute and an entity" in got.reason


def test_reference_lookup_unreadable_year_declines(gsm8k):
    got = call("reference-lookup", gsm8k,
               {"attribute": "population", "entity": "france", "year": "blorp"})
    assert got.kind == "decline"
    assert "as a year" in got.reason


# --- reference-aggregate: same structure as reference-lookup above — the op
# is a resolves LITERAL ('total'/'average'), attribute and group are required
# slots, and the year arrives via "{y.value}" off a number-typed slot.

def test_reference_aggregate_empty_slots_decline(gsm8k):
    got = call("reference-aggregate", gsm8k, {"op": "total", "attribute": "", "group": ""})
    assert got.kind == "decline"
    assert "needs an op, an attribute and a group" in got.reason


def test_reference_aggregate_unreadable_year_declines(gsm8k):
    got = call("reference-aggregate", gsm8k,
               {"op": "total", "attribute": "population", "group": "europe", "year": "blorp"})
    assert got.kind == "decline"
    assert "as a year" in got.reason


# --- partition-percentage: ordinary text supplies one exact holder and the
# staged premise constrains every computed part to the finite whole. These two
# branches defend the consumer against malformed or future fact producers.


def test_partition_percentage_needs_one_total_holder(curated):
    provenance = Provenance(source="synthetic", sentence=0)
    store = FactStore(facts=[
        Quantity(
            provenance=provenance,
            entity="academy",
            measure="student",
            value=100,
            verb="have",
        ),
        Quantity(
            provenance=provenance,
            entity="college",
            measure="student",
            value=100,
            verb="have",
        ),
        PartitionQuantity(
            provenance=provenance,
            collection="student",
            attribute="science course",
            value=25,
            verb="enroll",
        ),
    ])
    got = call(
        "partition-percentage",
        curated,
        {"collection": "student", "attribute": "science course"},
        store=store,
    )
    assert got.kind == "decline"
    assert "partition total needs exactly one holder" in got.reason


def test_partition_percentage_refuses_a_part_larger_than_the_total(curated):
    provenance = Provenance(source="synthetic", sentence=0)
    store = FactStore(facts=[
        Quantity(
            provenance=provenance,
            entity="academy",
            measure="student",
            value=100,
            verb="have",
        ),
        PartitionQuantity(
            provenance=provenance,
            collection="student",
            attribute="science course",
            value=120,
            verb="enroll",
        ),
    ])
    got = call(
        "partition-percentage",
        curated,
        {"collection": "student", "attribute": "science course"},
        store=store,
    )
    assert got.kind == "decline"
    assert "partition value 120" in got.reason


# --- aggregate measurement: the public grammar supplies a mass dimension,
# narration coordinates, positive multipliers, and one selected stream. These
# direct stores probe the consumer's defensive restatement of those contracts.


def _measurement_change(
    operation,
    value,
    *,
    container="box",
    content="water",
    dimension=None,
    measure=None,
    occurrence=0,
    sentence=0,
):
    return MeasuredContentChange(
        provenance=Provenance(source="synthetic", sentence=sentence),
        container=container,
        content=content,
        operation=operation,
        value=value,
        dimension=dimension,
        measure=measure,
        occurrence=occurrence,
    )


def _measurement_anchor(**updates):
    fields = {
        "operation": "set_total",
        "value": 4.0,
        "container": "box",
        "content": "water",
        "dimension": "weight",
        "measure": "kilogram",
        "occurrence": 0,
        "sentence": 0,
    }
    fields.update(updates)
    return _measurement_change(**fields)


def _measurement_placement(**updates):
    fields = {
        "entity": "box",
        "reference": "scale",
        "relation": "on",
        "occurrence": 0,
    }
    fields.update(updates)
    return SpatialPlacement(
        provenance=Provenance(source="synthetic", sentence=0), **fields
    )


def _measurement_call(gsm8k, facts=(), query=None, premises=()):
    return call(
        "measurement-reading",
        gsm8k,
        query
        or {"instrument": "scale", "dimension": "weight", "relation": "on"},
        store=FactStore(facts=list(facts)),
        premises=premises,
    )


@pytest.mark.parametrize(
    ("query", "reason"),
    (
        ({"dimension": "weight", "relation": "on"}, "needs a dimension and a container or instrument"),
        (
            {"instrument": "scale", "dimension": "apple", "relation": "on"},
            "names no declared measurement dimension",
        ),
    ),
)
def test_measurement_query_defensive_contracts(gsm8k, query, reason):
    got = _measurement_call(gsm8k, query=query)
    assert got.kind == "decline"
    assert reason in got.reason


def test_measurement_rejects_a_stated_value_outside_its_stream(gsm8k):
    reading = analyze("Nia found 3 coins.", gsm8k, sentence_index=0)
    got = _measurement_call(gsm8k, premises=(reading,))
    assert got.kind == "decline"
    assert "stated value" in got.reason


def test_measurement_needs_one_placed_total_anchor(gsm8k):
    got = _measurement_call(gsm8k)
    assert got.kind == "decline"
    assert "the reading needs one" in got.reason


@pytest.mark.parametrize("unit,reason", [
    ("liter", "requested unit has an incompatible dimension"),
    ("pound", "no known conversion from"),
])
def test_container_measurement_ask_requires_a_compatible_convertible_unit(gsm8k, unit, reason):
    # The mined project declares more conversions than curated. Explicitly
    # withhold this edge to test the missing-conversion guard, rather than
    # depending on either project's changing vocabulary/conversion inventory.
    from dataclasses import replace

    registry = replace(gsm8k, conversions={
        pair: factor for pair, factor in gsm8k.conversions.items()
        if pair != ("kilogram", "pound")
    })
    got = _measurement_call(
        registry,
        (_measurement_anchor(), _measurement_placement()),
        query={"container": "box", "dimension": "weight", "target_measure": unit},
    )
    assert got.kind == "decline"
    assert reason in got.reason


def test_measurement_update_needs_a_narration_coordinate(gsm8k):
    update = _measurement_change(
        "multiply_total",
        2.0,
        container="$active:measured-container$",
        content="clay",
        dimension="weight",
        occurrence=None,
        sentence=1,
    )
    got = _measurement_call(
        gsm8k, (_measurement_anchor(), _measurement_placement(), update)
    )
    assert got.kind == "decline"
    assert "no narration order" in got.reason


def test_measurement_elision_needs_one_prior_stream(gsm8k):
    other = _measurement_anchor(container="bucket", content="milk")
    update = _measurement_change(
        "multiply_total",
        2.0,
        container="$active:measured-container$",
        content="clay",
        dimension="weight",
        occurrence=1,
        sentence=1,
    )
    got = _measurement_call(
        gsm8k,
        (_measurement_anchor(), other, _measurement_placement(), update),
    )
    assert got.kind == "decline"
    assert "one unique prior stream" in got.reason


def test_measurement_refuses_changes_outside_the_selected_stream(gsm8k):
    other = _measurement_change(
        "add_quantity",
        2.0,
        container="bucket",
        content="clay",
        measure="kilogram",
        occurrence=1,
        sentence=1,
    )
    got = _measurement_call(
        gsm8k, (_measurement_anchor(), _measurement_placement(), other)
    )
    assert got.kind == "decline"
    assert "outside the selected stream" in got.reason


def test_measurement_effects_need_a_strict_order(gsm8k):
    update = _measurement_change(
        "add_quantity",
        2.0,
        content="clay",
        measure="kilogram",
        occurrence=0,
    )
    got = _measurement_call(
        gsm8k, (_measurement_anchor(), _measurement_placement(), update)
    )
    assert got.kind == "decline"
    assert "no strict order" in got.reason


@pytest.mark.parametrize("value", (-1.0, float("nan")))
def test_measurement_anchor_must_be_finite_and_nonnegative(gsm8k, value):
    got = _measurement_call(
        gsm8k, (_measurement_anchor(value=value), _measurement_placement())
    )
    assert got.kind == "decline"
    assert "anchor is invalid" in got.reason


def test_measurement_update_must_be_finite_and_nonnegative(gsm8k):
    update = _measurement_change(
        "add_quantity",
        -1.0,
        content="clay",
        measure="kilogram",
        occurrence=1,
        sentence=1,
    )
    got = _measurement_call(
        gsm8k, (_measurement_anchor(), _measurement_placement(), update)
    )
    assert got.kind == "decline"
    assert "update is invalid" in got.reason


def test_measurement_multiplier_dimension_must_match(gsm8k):
    update = _measurement_change(
        "multiply_total",
        2.0,
        content="clay",
        dimension="distance",
        occurrence=1,
        sentence=1,
    )
    got = _measurement_call(
        gsm8k, (_measurement_anchor(), _measurement_placement(), update)
    )
    assert got.kind == "decline"
    assert "scaled dimension" in got.reason


def test_measurement_multiplier_must_be_positive(gsm8k):
    update = _measurement_change(
        "multiply_total",
        0.0,
        content="clay",
        dimension="weight",
        occurrence=1,
        sentence=1,
    )
    got = _measurement_call(
        gsm8k, (_measurement_anchor(), _measurement_placement(), update)
    )
    assert got.kind == "decline"
    assert "multiplier must be positive" in got.reason


def test_measurement_added_unit_must_match_the_dimension(gsm8k):
    update = _measurement_change(
        "add_quantity",
        2.0,
        content="milk",
        measure="liter",
        occurrence=1,
        sentence=1,
    )
    got = _measurement_call(
        gsm8k, (_measurement_anchor(), _measurement_placement(), update)
    )
    assert got.kind == "decline"
    assert "added measure" in got.reason


def test_measurement_added_unit_needs_a_conversion(gsm8k):
    update = _measurement_change(
        "add_quantity",
        2.0,
        content="clay",
        measure="weight",
        occurrence=1,
        sentence=1,
    )
    got = _measurement_call(
        gsm8k, (_measurement_anchor(), _measurement_placement(), update)
    )
    assert got.kind == "decline"
    assert "no known conversion" in got.reason


def test_measurement_rejects_an_unknown_aggregate_operation(gsm8k):
    update = _measurement_change(
        "divide_total",
        2.0,
        content="clay",
        occurrence=1,
        sentence=1,
    )
    got = _measurement_call(
        gsm8k, (_measurement_anchor(), _measurement_placement(), update)
    )
    assert got.kind == "decline"
    assert "unsupported aggregate operation" in got.reason


def _measurement_tare(**updates):
    fields = {
        "entity": "box",
        "measure": "kilogram",
        "value": 0.5,
        "verb": "weigh",
        "occurrence": 2,
    }
    fields.update(updates)
    return Quantity(
        provenance=Provenance(source="synthetic", sentence=2), **fields
    )


def _measurement_content_call(gsm8k, facts=(), query=None):
    return call(
        "measurement-content-amount",
        gsm8k,
        query or {"content": "water", "container": "box"},
        store=FactStore(facts=list(facts)),
    )


def test_measurement_content_needs_content_and_container(gsm8k):
    got = _measurement_content_call(gsm8k, query={"content": "water"})
    assert got.kind == "decline"
    assert "needs one content and container" in got.reason


def test_measurement_content_needs_one_matching_anchor(gsm8k):
    got = _measurement_content_call(gsm8k)
    assert got.kind == "decline"
    assert "needs one resulting-total anchor" in got.reason


def test_measurement_content_needs_one_prior_placement(gsm8k):
    got = _measurement_content_call(gsm8k, (_measurement_anchor(),))
    assert got.kind == "decline"
    assert "needs one prior container/instrument placement" in got.reason


def test_measurement_content_needs_one_compatible_tare(gsm8k):
    got = _measurement_content_call(
        gsm8k, (_measurement_anchor(), _measurement_placement())
    )
    assert got.kind == "decline"
    assert "needs one compatible intrinsic container mass" in got.reason


def test_measurement_content_tare_must_leave_a_positive_amount(gsm8k):
    got = _measurement_content_call(
        gsm8k,
        (
            _measurement_anchor(),
            _measurement_placement(),
            _measurement_tare(value=4.0),
        ),
    )
    assert got.kind == "decline"
    assert "tare leaves no positive content amount" in got.reason


def test_measurement_content_needs_a_recoverable_change_for_later_content(gsm8k):
    got = _measurement_content_call(
        gsm8k,
        (_measurement_anchor(), _measurement_placement()),
        query={"content": "clay", "container": "box"},
    )
    assert got.kind == "decline"
    assert "has no recoverable measured addition" in got.reason


def test_measurement_content_addition_must_increase_the_total(gsm8k):
    reduction = _measurement_change(
        "multiply_total",
        0.5,
        content="clay",
        dimension="weight",
        occurrence=1,
        sentence=1,
    )
    got = _measurement_content_call(
        gsm8k,
        (_measurement_anchor(), _measurement_placement(), reduction),
        query={"content": "clay", "container": "box"},
    )
    assert got.kind == "decline"
    assert "addition leaves no positive content amount" in got.reason


def test_measurement_content_conversion_is_scoped_to_the_substance(gsm8k):
    addition = _measurement_change(
        "multiply_total",
        2.0,
        content="clay",
        dimension="weight",
        occurrence=1,
        sentence=1,
    )
    got = _measurement_content_call(
        gsm8k,
        (_measurement_anchor(), _measurement_placement(), addition),
        query={
            "content": "clay",
            "container": "box",
            "target_measure": "liter",
        },
    )
    assert got.kind == "decline"
    assert "no known 'clay' conversion" in got.reason


def test_capacity_budget_value_requires_its_concrete_unit(curated):
    # Ordinary capacity asks now bind the unit alongside the value. A direct
    # caller can still omit it; this must not borrow the price denomination.
    from rulekit.kernel.model import Price
    store = FactStore(facts=[Price(Provenance('invented', 0), item='pen', value=2)])
    got = call('capacity', curated,
               {'entity': 'dena', 'item': 'pen', 'budget_value': '8'}, store=store)
    assert got.kind == 'decline'
    assert got.reason == 'the budget needs a concrete currency unit'
