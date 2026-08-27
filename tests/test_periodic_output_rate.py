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
RECIPIENT_RULE_ID = "arithmetic/periodic-output-per-recipient-frequency"


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
    for question in (
        "How many pages does she write in a year?",
        "How many pages does she write a year?",
    ):
        result = solve(
            "Dena writes a 25-page book every week. " + question,
            project.registry,
        )

        assert result.answer.value == 1300


@pytest.mark.parametrize(
    "recipient_surface",
    ["3 friends", "3 different friends"],
)
def test_measured_output_per_counted_recipient_and_frequency_projects_year(
    project, recipient_surface
):
    result = solve(
        f"Tova writes a 5-page letter to {recipient_surface} twice a week. "
        "How many pages does she write in a year?",
        project.registry,
    )

    assert result.answer.value == 1560
    rates = [fact for fact in result.facts() if isinstance(fact, Rate)]
    assert len(rates) == 1
    assert (
        rates[0].entity,
        rates[0].measure,
        rates[0].per,
        rates[0].value,
        rates[0].verb,
    ) == ("tova", "page", "week", 30, "write")


@pytest.mark.parametrize(
    "premise",
    [
        # A book has not opted into the one-product-per-recipient convention.
        "Tova writes a 5-page book to 3 friends twice a week.",
        # No recipient count means there is no recipient multiplier to apply.
        "Tova writes a 5-page letter to friends twice a week.",
    ],
)
def test_recipient_frequency_output_requires_complete_opt_in_frame(
    project, premise
):
    result = solve(
        premise + " How many pages does Tova write in a year?",
        project.registry,
    )

    assert result.answer.kind == "decline"


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
    assert "-page " in candidate.sentence
    assert " every " in candidate.sentence
    assert candidate.facts[0]["fields"]["measure"] == "page"


def test_recipient_frequency_output_rule_is_generator_supported(project):
    availability = {item.id: item for item in list_rule_availability(project)}
    assert availability[RECIPIENT_RULE_ID].supported

    candidate = generate_candidate(project, rule_id=RECIPIENT_RULE_ID, seed=7)
    assert candidate.target_status == "matched"
    assert "-page letter to " in candidate.sentence
    assert candidate.facts[0]["fields"]["measure"] == "page"


def test_output_projection_ask_is_generator_supported(project):
    ask_id = "ask/how-many-output-rate-span-one"
    availability = {item.id: item for item in list_ask_availability(project)}
    assert availability[ask_id].supported

    candidate = generate_ask_scenario(project, ask_id=ask_id, seed=5)
    assert candidate.target_ask == ask_id
    assert candidate.target_bindings["item"] == "pages"
    assert candidate.query["verb"] == "write"
