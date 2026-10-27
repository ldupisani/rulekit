"""Age offsets, totals, and calendar coordinates account for their numbers."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate, retest_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import GroupTotal, Quantity


@pytest.fixture(scope="module")
def project():
    return load_project(Path("projects/curated"))


@pytest.fixture(scope="module")
def registry(project):
    return project.registry


def quantity_gaps(result):
    return [gap for gap in result.deficiencies() if "needs a quantifies" in gap]


@pytest.mark.parametrize("offset,age,expected", [
    ("4 more years", "24 years", 20),
    ("four more years", "twenty-four years", 20),
    ("1 more year", "21 years", 20),
    ("one more year", "twenty-one years", 20),
])
@pytest.mark.parametrize("modal", ["will", "would"])
@pytest.mark.parametrize("boundary", [" ", ", "])
def test_intensified_age_offset_accounts_for_unmerged_number(
    registry, offset, age, expected, modal, boundary
):
    result = solve(
        f"In {offset}{boundary}Dena {modal} be {age} old. How old is Dena?",
        registry,
    )

    assert result.answer.committed
    assert result.value == expected
    assert quantity_gaps(result) == []
    ages = [
        fact for fact in result.store.by_kind(Quantity)
        if fact.entity == "dena" and fact.measure == "year"
    ]
    assert len(ages) == 1
    assert ages[0].provenance.source == (
        "arithmetic/temporal-offset-age-future-intensified"
    )
    assert ages[0].provenance.temporal_perspective == "present"


@pytest.mark.parametrize("premise,expected", [
    ("In 4 years Dena will be 24 years old.", 20),
    ("In one year, Dena would be 21 years old.", 20),
    ("Four years ago, Dena was 16 years old.", 20),
    ("One year ago Dena was 19 years old.", 20),
])
def test_plain_future_and_past_offsets_keep_quantity_accounting(
    registry, premise, expected
):
    result = solve(f"{premise} How old is Dena?", registry)

    assert result.answer.committed
    assert result.value == expected
    assert quantity_gaps(result) == []


@pytest.mark.parametrize("premise,expected", [
    ("In 4 years Cato will be twice as old as Dena.", 20),
    ("In 4 years Cato will be twice as old as Dena is now.", 12),
    ("In 4 years Cato would be twice as old as Dena today.", 12),
    ("Four years ago Cato was twice as old as Dena.", 12),
])
def test_temporal_age_ratios_keep_offset_accounting(registry, premise, expected):
    result = solve(
        f"{premise} Dena is 8 years old. How old is Cato?", registry
    )

    assert result.answer.committed
    assert result.value == expected
    assert quantity_gaps(result) == []


@pytest.mark.parametrize("total", [
    "The sum of their ages is 36.",
    "The sum of their ages is thirty-six.",
    "They have a combined age of 36.",
    "They have a total age of thirty-six.",
    "They have a combined age of 36 years.",
])
def test_age_totals_account_for_postposed_value(registry, total):
    result = solve(
        f"Dena is 4 years older than Fia. {total} How old is Dena?", registry
    )

    assert result.answer.committed
    assert result.value == 20
    assert quantity_gaps(result) == []
    totals = result.store.by_kind(GroupTotal)
    assert len(totals) == 1
    assert totals[0].value == 36
    assert totals[0].measure == "year"


@pytest.mark.parametrize("holder", ["Dena", "the teacher"])
def test_dated_age_question_accounts_for_its_calendar_coordinate(registry, holder):
    result = solve(
        f"{holder} was 16 years old in 2000. How old was {holder} in 2004?",
        registry,
    )

    assert result.answer.committed
    assert result.value == 20
    assert quantity_gaps(result) == []


def test_combined_dated_age_question_accounts_for_its_calendar_coordinate(registry):
    result = solve(
        "The teacher was 16 years old in 2000. "
        "The child was 8 years old in 2002. "
        "What was their combined age in 2004?",
        registry,
    )

    assert result.answer.committed
    assert result.value == 30
    assert quantity_gaps(result) == []


@pytest.mark.parametrize("question", [
    "How old will Dena be in four years?",
    "How old would Dena be after 4 years?",
    "How old will Dena be 4 years from now?",
])
def test_projected_age_question_keeps_offset_accounting(registry, question):
    result = solve(f"Dena is 20 years old. {question}", registry)

    assert result.answer.committed
    assert result.value == 24
    assert quantity_gaps(result) == []


@pytest.mark.parametrize("offset", [
    "4 more apples",
    "4 more year",
    "1 more years",
    "4 apples more years",
    "4 more 5 years",
])
def test_invalid_intensified_offset_cannot_discharge_number(registry, offset):
    result = solve(
        f"In {offset} Dena would be 24 years old. How old is Dena?", registry
    )

    assert not result.answer.committed
    assert not any(
        fact.provenance.source == "arithmetic/temporal-offset-age-future-intensified"
        for fact in result.facts()
    )


def test_resolved_future_offset_does_not_establish_an_unspecified_past_age(registry):
    result = solve(
        "In 4 more years Dena would be 24 years old. How old was Dena?",
        registry,
    )

    assert not result.answer.committed
    assert quantity_gaps(result) == []


def test_valid_offset_does_not_hide_an_unrelated_unattached_number(registry):
    result = solve(
        "In 4 more years Dena would be 24 years old for 9. How old is Dena?",
        registry,
    )

    assert not result.answer.committed
    assert quantity_gaps(result) == [
        "'9' (value) needs a quantifies and none was found."
    ]


def test_age_accounting_does_not_change_ordinary_more_comparisons(registry):
    result = solve(
        "Dena has 4 more books than Fia. Fia has 8 books. "
        "How many books does Dena have?",
        registry,
    )

    assert result.answer.committed
    assert result.value == 12
    assert quantity_gaps(result) == []


def test_workbench_retest_clears_the_saved_offset_defect(project):
    candidate = retest_candidate(
        project,
        rule_id="arithmetic/temporal-offset-age-future-intensified",
        sentence="In 4 more years Dena would be 24 years old.",
        seed=0,
        origin="reading",
    )

    assert candidate.target_status == "matched"
    assert candidate.clean_reading
    assert candidate.deficiencies == ()


def test_intensified_age_rule_still_generates_a_supported_offset(project):
    candidate = generate_candidate(
        project,
        rule_id="arithmetic/temporal-offset-age-future-intensified",
        seed=0,
        max_attempts=1,
        locked_bindings={
            "n": "4", "mod": "more", "yr": "years", "who": "Dena",
            "aux": "would",
        },
    )

    assert candidate.target_status == "matched"
    assert candidate.clean_reading
    assert not candidate.deficiencies
