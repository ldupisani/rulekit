"""Measured content progress across explicitly distinct periods.

All surfaces are invented analogues.  The target class keeps a product's
extent separate from completed progress, resolves one locally anchored
anaphoric multiplier, and totals only the requested participant's matching
events.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import (
    generate_ask_scenario,
    generate_candidate,
    list_ask_availability,
    list_rule_availability,
)
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Membership, Predication, Quantity


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
PRODUCT_RULE = "arithmetic/content-progress-measured-product"
PROGRESS_RULE = "arithmetic/realized-progress-anaphoric-multiplier"
DEICTIC_PROGRESS_RULE = (
    "arithmetic/realized-progress-deictic-anaphoric-multiplier"
)
DEICTIC_EXPLICIT_STANDARD_PROGRESS_RULE = (
    "arithmetic/realized-progress-deictic-explicit-standard-multiplier"
)
ASK_ID = "ask/how-many-content-progress-perfect-singular"
REMAINDER_ASK_ID = "ask/how-many-content-progress-fraction-of-remainder"
REMAINDER_OF_ASK_ID = (
    "ask/how-many-content-progress-fraction-of-remainder-with-of"
)
REMAINDER_CONDITIONAL_FIRST_ASK_ID = (
    "ask/if-content-progress-fraction-of-remainder-how-many"
)


@pytest.fixture(scope="module")
def project():
    return load_project(CURATED)


def test_measured_progress_total_keeps_product_extent_out_of_answer(project) -> None:
    result = solve(
        "Aven is reading an 80-page book. "
        "Last week Aven was able to read 12 pages, and today Aven read "
        "twice as many pages. How many pages has Aven read?",
        project.registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == 36

    quantities = list(result.store.by_kind(Quantity))
    assert {
        (q.entity, q.measure, q.value, q.verb, q.time, q.is_state)
        for q in quantities
    } == {
        ("book", "page", 80.0, "have", None, True),
        ("aven", "page", 12.0, "read", "last week", False),
        ("aven", "page", 24.0, "read", "today", False),
    }
    assert list(result.store.by_kind(Predication))
    assert not list(result.store.by_kind(Membership))


def test_subject_pronouns_resolve_across_progress_and_ask(project) -> None:
    result = solve(
        "Dena is reading a 90-page book. "
        "Last week she was able to read 15 pages, and today she read three "
        "times as many pages. How many pages has she read?",
        project.registry,
    )

    assert result.answer.value == 60


def test_named_progress_events_do_not_require_product_context(project) -> None:
    result = solve(
        "Last week Bira was able to read 9 pages, and today Bira read twice "
        "as many pages. How many pages has Bira read?",
        project.registry,
    )

    assert result.answer.value == 27


def test_present_perfect_ask_totals_an_ordinary_read_event(project) -> None:
    result = solve(
        "Cato read 14 pages. How many pages has Cato read?",
        project.registry,
    )

    assert result.answer.value == 14


def test_planned_half_of_remaining_product_progress(project) -> None:
    result = solve(
        "Aven is reading an 80-page book. "
        "Last week Aven was able to read 12 pages, and today Aven read twice "
        "as many pages. How many pages should Aven read tomorrow if Aven "
        "wants to read half the remaining pages?",
        project.registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == 22
    # The question computes a plan; it does not mint another completed event.
    assert [
        quantity.value
        for quantity in result.store.by_kind(Quantity)
        if quantity.entity == "aven"
        and quantity.measure == "page"
        and quantity.verb == "read"
    ] == [12.0, 24.0]


def test_explicit_partitive_fraction_of_remaining_progress(project) -> None:
    result = solve(
        "Bira is reading a 90-page book. "
        "Last week Bira was able to read 10 pages, and today Bira read twice "
        "as many pages. How many pages should Bira read tomorrow if Bira "
        "wants to read one fourth of the remaining pages?",
        project.registry,
    )

    assert result.answer.value == 15


def test_conditional_first_fraction_of_remaining_progress(project) -> None:
    result = solve(
        "Dena is reading an 80-page book. "
        "Last week she was able to read 12 pages, and today she read twice "
        "as many pages. If she wants to read half of the remaining pages "
        "tomorrow, how many pages should she read?",
        project.registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == 22
    assert result.question is not None
    assert result.question.text.startswith("If she wants")
    # The leading desire clause specifies the query; it is not an assertion.
    assert not result.assumptions


def test_bare_past_day_progress_supports_conditional_first_plan(project) -> None:
    result = solve(
        "Dena is reading an 80-page book. Yesterday she was able to read 12 "
        "pages, and today she read twice as many pages. If she wants to read "
        "half of the remaining pages tomorrow, how many pages should she "
        "read?",
        project.registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == 22
    assert {
        (quantity.value, quantity.time)
        for quantity in result.store.by_kind(Quantity)
        if quantity.entity == "dena"
        and quantity.measure == "page"
        and quantity.verb == "read"
    } == {(12.0, "yesterday"), (24.0, "today")}


def test_conditional_first_productive_remainder_fraction(project) -> None:
    result = solve(
        "Cato is reading a 90-page book. "
        "Last week Cato was able to read 10 pages, and today Cato read twice "
        "as many pages. If Cato wants to read one fourth of the remaining "
        "pages tomorrow, how many pages should Cato read?",
        project.registry,
    )

    assert result.answer.value == 15


def test_explicit_past_period_standard_resolves_progress(project) -> None:
    result = solve(
        "Bira is reading a 90-page book. Yesterday, Bira was able to read 10 "
        "pages and today, Bira read twice as many pages as yesterday. If "
        "Bira wants to read one fourth of the remaining pages tomorrow, how "
        "many pages should Bira read?",
        project.registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == 15
    assert {
        (quantity.value, quantity.time)
        for quantity in result.store.by_kind(Quantity)
        if quantity.entity == "bira"
        and quantity.measure == "page"
        and quantity.verb == "read"
    } == {(10.0, "yesterday"), (20.0, "today")}


@pytest.mark.parametrize(
    "text",
    [
        # No measured product means there is no declared capacity to subtract.
        "Last week Aven was able to read 12 pages, and today Aven read twice "
        "as many pages. How many pages should Aven read tomorrow if Aven "
        "wants to read half the remaining pages?",
        # The plan and its purpose clause must retain the same participant.
        "Aven is reading an 80-page book. Last week Aven was able to read 12 "
        "pages, and today Aven read twice as many pages. How many pages "
        "should Aven read tomorrow if Bira wants to read half the remaining "
        "pages?",
        # This construction is explicitly future-facing, never a present plan.
        "Aven is reading an 80-page book. Last week Aven was able to read 12 "
        "pages, and today Aven read twice as many pages. How many pages "
        "should Aven read today if Aven wants to read half the remaining "
        "pages?",
        # Completed progress cannot exceed the product's capacity.
        "Aven is reading a 10-page book. Last week Aven was able to read 12 "
        "pages, and today Aven read twice as many pages. How many pages "
        "should Aven read tomorrow if Aven wants to read half the remaining "
        "pages?",
    ],
)
def test_unlicensed_remaining_progress_plans_decline(project, text: str) -> None:
    assert solve(text, project.registry).answer.kind == "decline"


@pytest.mark.parametrize(
    "text",
    [
        # Bare capacity is not evidence that the event happened.
        "Last week Aven could read 12 pages, and today Aven read twice as "
        "many pages. How many pages has Aven read?",
        # The proportional event must retain the same participant.
        "Last week Aven was able to read 12 pages, and today Bira read "
        "twice as many pages. How many pages has Aven read?",
        # A named standard changes the relation and is not locally anchored.
        "Last week Aven was able to read 12 pages, and today Aven read "
        "twice as many pages as Bira. How many pages has Aven read?",
        # Predeterminer multipliers do not license the adverbial as-many form.
        "Last week Aven was able to read 12 pages, and today Aven read "
        "double as many pages. How many pages has Aven read?",
        # Past perfect needs a reference time that this ask does not state.
        "Aven read 12 pages. How many pages had Aven read?",
    ],
)
def test_unlicensed_progress_neighbours_decline(project, text: str) -> None:
    assert solve(text, project.registry).answer.kind == "decline"


def test_progress_generation_contracts_are_explicit(project) -> None:
    rules = {item.id: item for item in list_rule_availability(project)}
    asks = {item.id: item for item in list_ask_availability(project)}

    assert rules[PRODUCT_RULE].supported
    assert rules[PROGRESS_RULE].supported
    assert rules[DEICTIC_PROGRESS_RULE].supported
    assert rules[DEICTIC_EXPLICIT_STANDARD_PROGRESS_RULE].supported
    assert asks[ASK_ID].supported
    assert not asks[REMAINDER_ASK_ID].supported
    assert not asks[REMAINDER_OF_ASK_ID].supported
    assert not asks[REMAINDER_CONDITIONAL_FIRST_ASK_ID].supported
    assert asks[REMAINDER_ASK_ID].blockers == (
        "ask requires generated premise evidence; standalone realization is disabled",
    )
    assert asks[REMAINDER_OF_ASK_ID].blockers == (
        "ask requires generated premise evidence; standalone realization is disabled",
    )
    assert asks[REMAINDER_CONDITIONAL_FIRST_ASK_ID].blockers == (
        "ask requires generated premise evidence; standalone realization is disabled",
    )

    product = generate_candidate(project, rule_id=PRODUCT_RULE, seed=7)
    progress = generate_candidate(project, rule_id=PROGRESS_RULE, seed=7)
    deictic_progress = generate_candidate(
        project, rule_id=DEICTIC_PROGRESS_RULE, seed=7
    )
    explicit_standard_progress = generate_candidate(
        project,
        rule_id=DEICTIC_EXPLICIT_STANDARD_PROGRESS_RULE,
        seed=7,
    )
    ask = generate_ask_scenario(project, ask_id=ASK_ID, seed=7)

    assert product.target_status == "matched"
    assert progress.target_status == "matched"
    assert deictic_progress.target_status == "matched"
    assert deictic_progress.sentence.startswith("Yesterday ")
    assert explicit_standard_progress.target_status == "matched"
    assert explicit_standard_progress.sentence.endswith("as yesterday.")
    assert " and today " in progress.sentence.lower()
    assert ask.target_ask == ASK_ID
    assert ask.query["verb"] == "read"
