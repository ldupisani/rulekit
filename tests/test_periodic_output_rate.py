"""Synthetic coverage for measured products projected across a cadence."""

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
from rulekit.kernel.model import Quantity, Rate


CURATED = Path("projects/curated")
RULE_ID = "arithmetic/periodic-output-per-unit"


@pytest.fixture(scope="module")
def project():
    return load_project(CURATED)


def test_measured_product_cadence_projects_across_converted_year(project):
    result = solve(
        "Aven writes a 40-page book every week. "
        "How many pages does Aven write in a year?",
        project.registry,
    )

    assert result.answer.value == 2080
    rates = [fact for fact in result.facts() if isinstance(fact, Rate)]
    assert len(rates) == 1
    assert (rates[0].entity, rates[0].measure, rates[0].per) == (
        "aven",
        "page",
        "week",
    )
    assert not [fact for fact in result.facts() if isinstance(fact, Quantity)]

    # The school-word-problem convention is intentionally unavailable to
    # exact elapsed-duration consumers.
    assert ("year", "week") not in project.registry.conversions
    assert project.registry.cadence_conversions[("year", "week")] == 52


def test_output_rate_ask_resolves_subject_pronoun(project):
    result = solve(
        "Dena writes a 25-page book every week. "
        "How many pages does she write in a year?",
        project.registry,
    )

    assert result.answer.value == 1300


@pytest.mark.parametrize(
    "text",
    [
        # Without the source hyphen, 40 cannot become the extent of pages.
        "Aven writes a 40 page book every week. "
        "How many pages does Aven write in a year?",
        # A duration is not a declared output measure of a book.
        "Aven writes a 40-week book every week. "
        "How many weeks does Aven write in a year?",
        # A bare recurring unit must be grammatically singular.
        "Aven writes a 40-page book every weeks. "
        "How many pages does Aven write in a year?",
        # The indefinite article states one measured product per cadence.
        "Aven writes 40-page books every week. "
        "How many pages does Aven write in a year?",
    ],
)
def test_malformed_or_unlicensed_output_cadences_decline(project, text):
    assert solve(text, project.registry).answer.kind == "decline"


def test_output_ask_cannot_consume_a_different_event_rate(project):
    result = solve(
        "Aven writes a 40-page book every week. "
        "How many pages does Aven make in a year?",
        project.registry,
    )

    assert result.answer.kind == "decline"


def test_numeric_hyphen_modifier_does_not_erase_outer_count(project):
    result = solve(
        "Aven has 16 three-page books. How many books does Aven have?",
        project.registry,
    )

    # The inner three describes each song; the outer sixteen remains the
    # actual event quantity. This protects the pre-existing compound shape.
    assert result.answer.value == 16


def test_periodic_output_rule_is_generator_supported(project):
    availability = {item.id: item for item in list_rule_availability(project)}
    assert availability[RULE_ID].supported

    candidate = generate_candidate(project, rule_id=RULE_ID, seed=7)
    assert candidate.target_status == "matched"
    assert "-page book every " in candidate.sentence
    assert candidate.facts[0]["fields"]["measure"] == "page"


def test_output_projection_ask_is_generator_supported(project):
    ask_id = "ask/how-many-output-rate-span-one"
    availability = {item.id: item for item in list_ask_availability(project)}
    assert availability[ask_id].supported

    candidate = generate_ask_scenario(project, ask_id=ask_id, seed=5)
    assert candidate.target_ask == ask_id
    assert candidate.target_bindings["item"] == "pages"
    assert candidate.query["verb"] == "write"
