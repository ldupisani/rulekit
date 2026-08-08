"""Absolute-year age statements and asks project one conservative state."""

from pathlib import Path

import pytest

from rulekit.cli import main as cli_main
from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import AgeAtYear, Quantity
from rulekit.kernel.patterns import match_ask
from rulekit.server.api import ServerState, TraceBody, build_router


GROUP_NOW_TEXT = (
    "The teacher was 20 years old in 1999. "
    "The child was 10 years old in 2010. "
    "How old are they now?"
)

GROUP_COMBINED_TEXT = (
    "The teacher was 20 years old in 1999. "
    "The child was 10 years old in 2010. "
    "What was their combined age in 2020?"
)


@pytest.fixture(scope="module")
def project():
    return load_project(Path("projects/curated"))


def test_common_noun_age_projects_between_absolute_years(project):
    result = solve(
        "The teacher was 20 years old in 1999. "
        "How old was the teacher in 2022?",
        project.registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == 43
    assert result.answer.reason == (
        "teacher's dated year age (20 in 1999) projected to 2022"
    )
    assert [
        (fact.entity, fact.measure, fact.value, fact.year)
        for fact in result.store.by_kind(AgeAtYear)
    ] == [("teacher", "year", 20, 1999)]
    assert not [
        fact
        for fact in result.store.by_kind(Quantity)
        if fact.entity == "teacher" and fact.measure == "year"
    ]


def test_referential_common_noun_group_projects_each_age_to_now(project):
    result = solve(GROUP_NOW_TEXT, project.registry, reference_year=2026)

    assert result.answer.kind == "series"
    assert result.answer.value == [
        {"entity": "teacher", "measure": "year", "value": 47},
        {"entity": "child", "measure": "year", "value": 26},
    ]
    assert result.answer.reason == (
        "dated year ages for ['teacher', 'child'] projected to 2026"
    )
    matched = match_ask(result.question, project.registry)
    assert matched is not None
    assert matched[0].id == "ask/how-old-discourse-group-now"
    assert matched[1]["holders"] == ["teacher", "child"]


def test_referential_group_combines_projected_ages_at_an_explicit_year(project):
    result = solve(GROUP_COMBINED_TEXT, project.registry)

    assert result.answer.kind == "number"
    assert result.answer.value == 61
    assert result.answer.reason == (
        "combined dated year age for ['teacher', 'child'] at 2020"
    )
    matched = match_ask(result.question, project.registry)
    assert matched is not None
    assert matched[0].id == "ask/what-combined-age-at-year"
    assert matched[1]["holders"] == ["teacher", "child"]
    assert matched[1]["aggregate"] == "sum"


def test_prenominal_age_total_marker_is_category_driven(project):
    result = solve(
        GROUP_COMBINED_TEXT.replace("combined age", "total age"),
        project.registry,
    )

    assert result.answer.value == 61


@pytest.mark.parametrize("marker", ["together", "altogether"])
def test_postpositive_total_markers_do_not_modify_age_noun(project, marker):
    result = solve(
        GROUP_COMBINED_TEXT.replace("combined age", f"{marker} age"),
        project.registry,
    )

    assert not result.answer.committed
    matched = match_ask(result.question, project.registry)
    assert matched is None or matched[0].id != "ask/what-combined-age-at-year"


def test_combined_dated_age_is_all_or_nothing(project):
    result = solve(
        "The teacher was 20 years old in 1999. The child has 3 apples. "
        "What was their combined age in 2020?",
        project.registry,
    )

    assert not result.answer.committed
    assert "no dated year age known for 'child'" in result.answer.reason


def test_singular_possessive_does_not_create_a_discourse_group(project):
    result = solve(
        "The teacher was 20 years old in 1999. "
        "What was his combined age in 2020?",
        project.registry,
    )

    assert not result.answer.committed
    matched = match_ask(result.question, project.registry)
    assert matched is None or matched[0].id != "ask/what-combined-age-at-year"


def test_deictic_age_projection_requires_an_explicit_reference_year(project):
    result = solve(GROUP_NOW_TEXT, project.registry)

    assert not result.answer.committed
    assert "explicit reference year" in result.answer.reason


def test_current_moment_age_marker_is_category_driven(project):
    result = solve(
        GROUP_NOW_TEXT.replace("now?", "today?"),
        project.registry,
        reference_year=2026,
    )

    assert result.answer.kind == "series"
    assert [row["value"] for row in result.answer.value] == [47, 26]


def test_group_age_projection_is_all_or_nothing(project):
    result = solve(
        "The teacher was 20 years old in 1999. The child has 3 apples. "
        "How old are they now?",
        project.registry,
        reference_year=2026,
    )

    assert not result.answer.committed
    assert "no dated year age known for 'child'" in result.answer.reason


def test_subject_and_object_case_group_pronouns_stay_separate(project):
    result = solve(
        "The teacher was 20 years old in 1999. "
        "The child was 10 years old in 2010. How old are them now?",
        project.registry,
        reference_year=2026,
    )

    assert not result.answer.committed
    matched = match_ask(result.question, project.registry)
    assert matched is None or matched[0].id != "ask/how-old-discourse-group-now"


def test_designer_trace_accepts_an_explicit_reference_year() -> None:
    state = ServerState(Path("projects/curated"))
    router = build_router(state)
    endpoint = next(
        route.endpoint
        for route in router.routes
        if route.path == "/api/trace" and "POST" in route.methods
    )

    trace = endpoint(TraceBody(text=GROUP_NOW_TEXT, reference_year=2026))

    assert trace["answer"] == {
        "kind": "series",
        "value": [
            {"entity": "teacher", "measure": "year", "value": 47},
            {"entity": "child", "measure": "year", "value": 26},
        ],
        "reason": "dated year ages for ['teacher', 'child'] projected to 2026",
        "clarification": None,
    }


def test_cli_accepts_an_explicit_reference_year(capsys) -> None:
    exit_code = cli_main([
        "--project",
        "projects/curated",
        "solve",
        GROUP_NOW_TEXT,
        "--reference-year",
        "2026",
    ])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "series:" in output
    assert "'teacher'" in output and "47.0" in output
    assert "'child'" in output and "26.0" in output


def test_named_dated_age_does_not_leak_into_undated_age_ask(project):
    result = solve(
        "Cato was 20 years old in 1999. How old is Cato?",
        project.registry,
    )

    assert not result.answer.committed
    assert result.store.by_kind(AgeAtYear)
    assert not [
        fact
        for fact in result.store.by_kind(Quantity)
        if fact.entity == "cato" and fact.measure == "year"
    ]


def test_projection_can_move_backward_but_not_before_age_zero(project):
    earlier = solve(
        "Cato was 20 years old in 1999. How old was Cato in 1990?",
        project.registry,
    )
    impossible = solve(
        "Cato was 5 years old in 2000. How old was Cato in 1990?",
        project.registry,
    )

    assert earlier.answer.value == 11
    assert not impossible.answer.committed
    assert "negative age" in impossible.answer.reason


def test_multiple_dated_age_sources_must_project_consistently(project):
    consistent = solve(
        "Cato was 20 years old in 1999. Cato was 22 years old in 2001. "
        "How old was Cato in 2022?",
        project.registry,
    )
    inconsistent = solve(
        "Cato was 20 years old in 1999. Cato was 25 years old in 2001. "
        "How old was Cato in 2022?",
        project.registry,
    )

    assert consistent.answer.value == 43
    assert not inconsistent.answer.committed
    assert "disagree" in inconsistent.answer.reason


def test_fractional_calendar_coordinates_decline(project):
    fractional_target = solve(
        "Cato was 20 years old in 1999. "
        "How old was Cato in 2022.5?",
        project.registry,
    )
    fractional_source = solve(
        "Cato was 20 years old in 1999.5. "
        "How old was Cato in 2022?",
        project.registry,
    )

    assert not fractional_target.answer.committed
    target_match = match_ask(fractional_target.question, project.registry)
    assert target_match is not None
    assert target_match[0].id != "ask/how-old-at-year"
    assert not fractional_source.answer.committed
    assert not fractional_source.store.by_kind(AgeAtYear)


def test_dated_non_age_quantity_does_not_project(project):
    result = solve(
        "The teacher had 20 apples in 1999. "
        "How old was the teacher in 2022?",
        project.registry,
    )

    assert not result.answer.committed
    assert not result.store.by_kind(AgeAtYear)


def test_dated_age_rule_is_strictly_generatable(project):
    candidate = generate_candidate(
        project,
        seed=20220808,
        rule_id="arithmetic/stated-age-at-year",
    )

    assert candidate.target_status in {"matched", "shadowed"}
    assert candidate.target_rule == "arithmetic/stated-age-at-year"
