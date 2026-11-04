"""Default interpretations remain answer metadata, distinct from evidence facts."""

from pathlib import Path

import pytest

from rulekit.cli import main as cli_main
from rulekit.data.project import load_project
from rulekit.kernel.answer import Answer, AnswerAssumption, assumption_records
from rulekit.kernel.engine import diagnose, solve
from rulekit.server.api import ServerState, TraceBody, build_router


@pytest.fixture(scope="module")
def project():
    return load_project(Path("projects/curated"))


TIPS = ("Paige washes one car for $12. Last week she washed 8 cars. "
        "All of her customers each gave her a $3 tip. "
        "How much did Paige earn washing cars last week?")


def test_assumptions_are_exposed_without_becoming_premise_facts(project):
    result = solve(TIPS, project.registry)
    assert result.value == 120
    assert not result.assumptions  # This is not an explicit hypothetical clause.
    records = assumption_records(result.answer)
    assert records == [{
        "id": "one-client-per-service",
        "description": "One distinct client per completed service: 8 clients.",
        "sentences": [1, 2],
    }]
    assert diagnose(result)["default_assumptions"] == records
    assert diagnose(result)["assumptions"] == []
    assert not any(getattr(f, "measure", "") == "customer" for f in result.store.facts)


def test_cli_prints_default_assumptions_beside_the_answer(capsys):
    assert cli_main(["--project", "projects/curated", "solve", TIPS]) == 0
    output = capsys.readouterr().out
    assert "number: 120" in output
    assert "assumption: One distinct client per completed service: 8 clients." in output


def test_designer_answer_contains_the_same_structured_metadata(project):
    state = ServerState(Path("projects/curated"))
    route = next(r.endpoint for r in build_router(state).routes
                 if r.path == "/api/trace" and "POST" in r.methods)
    trace = route(TraceBody(text=TIPS))
    assert trace["answer"]["value"] == 120
    assert trace["answer"]["assumptions"] == assumption_records(solve(TIPS, project.registry).answer)


def test_generation_records_assumptions_and_preserves_historical_unknowns():
    from rulekit.generation.ask_generation import _answer_json
    from rulekit.generation.reviews import _reviewed_assumptions_match

    answer = Answer("number", 12, "calculation", assumptions=(
        AnswerAssumption("example-policy", "A declared local default applies.", (0,)),
    ))
    payload, shape = _answer_json(answer)
    assert shape == "number"
    assert payload["assumptions"] == assumption_records(answer)
    assert _reviewed_assumptions_match(answer, {"answer": {"value": 12}})
    assert _reviewed_assumptions_match(answer, {"answer": payload})
    assert not _reviewed_assumptions_match(answer, {"answer": {"assumptions": []}})
    assert not _reviewed_assumptions_match(Answer("number", 12, "same value"), {"answer": payload})


def test_explicit_conditional_premises_remain_separate_from_default_metadata(project):
    text = ("Paige planned to buy a book for $200. A shop accepts payment of $50 per month "
            "with a 10% deposit. If she adds an extra $20 for the deposit, "
            "what will her balance be after 2 months of payments?")
    result = solve(text, project.registry)
    assert result.value == 60, result.answer
    report = diagnose(result)
    assert len(report["assumptions"]) == 1
    assert "adds" in report["assumptions"][0]["text"]
    assert [a["id"] for a in report["default_assumptions"]] == ["closed-finance-charges"]


@pytest.mark.parametrize("year,ids,value", [
    ("", {"non-leap-calendar"}, 59), (" of 2028", set(), 60),
])
def test_calendar_default_is_reported_only_when_the_year_is_unstated(project, year, ids, value):
    result = solve(f"Nora feeds the birds in January and February{year}. "
                   "She feeds them 1/4 cup in the morning and 3/4 cup in the afternoon. "
                   "How many cups of food will she need for all two months?", project.registry)
    assert result.value == value, result.answer
    assert {a.id for a in result.answer.assumptions} == ids


def test_joint_savings_records_the_earning_day_and_year_convention(project):
    result = solve("Nora and Iris save half of their income for a trip. "
                   "Nora earns $8 per day. Iris earns $2 per day. "
                   "How much money will they have saved after a year?", project.registry)
    assert result.value == 1825
    assert [a.id for a in result.answer.assumptions] == ["annual-daily-earnings"]


@pytest.mark.parametrize("explicit", [False, True])
def test_container_shape_defaults_are_distinct_from_explicit_shape_evidence(project, explicit):
    noun = "rectangular tank" if explicit else "tank"
    text = ("Nora is filling a tank. She fills it halfway. She spills half the water in the tank. "
            "Nora triples the amount of water in the tank. "
            f"The {noun} is 2 feet long, 3 feet wide, and 4 feet high. "
            "How many cubic feet of water are in the tank?")
    result = solve(text, project.registry)
    assert result.value == pytest.approx(18), result.answer
    assert {a.id for a in result.answer.assumptions} == (set() if explicit else {"rectangular-container"})
    if not explicit:
        confirmed = solve(text, project.registry, interpretation="rectangular-container")
        assert confirmed.value == pytest.approx(18)
        assert not confirmed.answer.assumptions


def test_a_declined_shape_does_not_leak_a_default_assumption(project):
    result = solve("Nora is filling a round tank. She fills it halfway. "
                   "How many cubic feet of water are in the tank?", project.registry)
    assert not result.answer.committed
    assert not result.answer.assumptions


@pytest.mark.parametrize("qualifier,ids,value", [
    ("", {"mixture-same-dimension-percentage"}, 1),
    ("by volume", set(), 1),
])
def test_mixture_basis_conventions_are_not_reported_as_explicit_evidence(project, qualifier, ids, value):
    text = (f"Nora has 4 liters of seawater. The seawater is 25% salt {qualifier}. "
            "How many liters of salt are in the seawater?")
    result = solve(text, project.registry)
    assert result.value == value, result.answer
    assert {a.id for a in result.answer.assumptions} == ids
