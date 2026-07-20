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
from rulekit.kernel.engine import solve
from rulekit.kernel.evaluate import ArithmeticLog
from rulekit.kernel.patterns import SKIPPABLE_SENSES, match_ask

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def gsm8k():
    return load_project(ROOT / "projects" / "gsm8k").registry


@pytest.fixture(scope="module")
def scratch():
    return load_project(ROOT / "projects" / "scratch").registry


def call(name, reg, query, question=None, store=None, match=None, ask=None):
    """Invoke a consumer directly. Fields default to None so a consumer that
    starts reading state its guard never needed fails loudly here rather than
    silently exercising a different path (the molar-mass file's discipline)."""
    return CONSUMERS[name](ConsumerContext(
        query=query, question=question, store=store, reg=reg,
        log=ArithmeticLog(), match=match, ask=ask,
    ))


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
