"""Conventional total markers satisfy only their own grammatical needs."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate, retest_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import GroupTotal, Quantity


@pytest.fixture(scope="module")
def project():
    return load_project(Path("projects/curated"))


@pytest.mark.parametrize("item,measure,value", [
    ("8 librarians", "librarian", 8),
    ("Eight books", "book", 8),
    ("1 gardener", "gardener", 1),
    ("20 marbles", "marble", 20),
])
def test_in_all_fragment_is_complete_without_an_invented_holder(
    project, item, measure, value
):
    candidate = retest_candidate(
        project,
        rule_id="arithmetic/group-total-trailing-in-all",
        sentence=f"{item} in all.",
        seed=0,
        origin="reading",
    )

    assert candidate.target_status == "matched"
    assert candidate.clean_reading
    assert candidate.deficiencies == ()
    assert [(f["type"], f["fields"]) for f in candidate.facts] == [
        ("GroupTotal", {"measure": measure, "value": value, "verb": "have"})
    ]


@pytest.mark.parametrize("marker", [
    "in all", "in total", "all together", "together", "altogether", "total",
])
def test_supported_trailing_total_markers_have_no_unmet_obligations(project, marker):
    result = solve(f"8 books {marker}.", project.registry)

    assert result.deficiencies() == []
    totals = result.store.by_kind(GroupTotal)
    assert len(totals) == 1
    assert (totals[0].measure, totals[0].value, totals[0].scope) == ("book", 8, None)
    assert not result.store.by_kind(Quantity)


@pytest.mark.parametrize("item", ["books", "marbles"])
@pytest.mark.parametrize("marker", ["in all", "in total", "all together"])
def test_total_marker_keeps_the_existing_sum_constraint_answer(project, item, marker):
    result = solve(
        f"Dena has 4 more {item} than Fia. 12 {item} {marker}. "
        f"How many {item} does Dena have?",
        project.registry,
    )

    assert result.answer.committed
    assert result.value == 8
    assert result.deficiencies() == []


@pytest.mark.parametrize("suffix", [
    "in all gardens", "in all the gardens", "in all of the gardens",
    "in all amount", "in both", "at all",
])
def test_nontotal_quantifier_phrases_do_not_become_group_totals(project, suffix):
    result = solve(f"8 books {suffix}.", project.registry)

    assert not result.store.by_kind(GroupTotal)
    assert not any(
        decision.rule_id == "arithmetic/group-total-trailing-in-all"
        and decision.kind == "pattern-satisfy"
        for reading in result.premises
        for decision in reading.decisions
    )


def test_total_marker_does_not_satisfy_an_unrelated_preposition(project):
    result = solve("8 books in all with.", project.registry)

    assert result.deficiencies() == [
        "'with' (preposition) needs a object and none was found."
    ]


def test_in_all_total_remains_realisable_with_a_clean_reading(project):
    candidate = generate_candidate(
        project,
        rule_id="arithmetic/group-total-trailing-in-all",
        seed=0,
        max_attempts=1,
        locked_bindings={"item": "8 books"},
    )

    assert candidate.sentence == "8 books in all."
    assert candidate.target_status == "matched"
    assert candidate.clean_reading


def test_pinned_generated_total_retests_with_its_original_item_binding(project):
    candidate = retest_candidate(
        project,
        rule_id="arithmetic/group-total-trailing-in-all",
        sentence="8 books in all.",
        seed=0,
        origin="generated",
        requested_bindings={"item": "8 books"},
    )

    assert candidate.target_status == "matched"
    assert candidate.clean_reading
