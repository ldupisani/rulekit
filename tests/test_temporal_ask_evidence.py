"""Temporal asks must answer only from evidence at their perspective."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import analyze, solve
from rulekit.kernel.model import Quantity, Relation
from rulekit.kernel.patterns import match_ask


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def project():
    return load_project(ROOT / "projects" / "curated")


def test_past_age_ask_rejects_current_age_derived_from_future_offset(project) -> None:
    result = solve(
        "In 7 more years Bira would be 90 years old. "
        "How many years old was Bira?",
        project.registry,
    )

    assert result.answer.committed is False


@pytest.mark.parametrize(
    "question",
    ["How many years old is Bira?", "How old are Bira?"],
)
def test_present_age_forms_accept_present_evidence_despite_lenient_agreement(
    project, question
) -> None:
    result = solve(
        f"In 7 more years Bira would be 90 years old. {question}",
        project.registry,
    )

    assert result.answer.value == 83


@pytest.mark.parametrize(
    ("premise", "question", "expected"),
    [
        ("Bira was 20 years old.", "How old was Bira?", 20),
        ("Bira is 20 years old.", "How old is Bira?", 20),
        ("Bira was 20 years old.", "How old is Bira?", None),
        ("Bira is 20 years old.", "How old was Bira?", None),
    ],
)
def test_direct_age_evidence_must_match_question_perspective(
    project, premise, question, expected
) -> None:
    result = solve(f"{premise} {question}", project.registry)

    if expected is None:
        assert result.answer.committed is False
    else:
        assert result.answer.value == expected


def test_age_relation_chain_preserves_matching_past_perspective(project) -> None:
    result = solve(
        "Bira was 10 years old. Cato was twice as old as Bira. "
        "How old was Cato?",
        project.registry,
    )

    assert result.answer.value == 20
    derived = [
        fact
        for fact in result.store.by_kind(Quantity)
        if fact.entity == "cato" and fact.measure == "year"
    ]
    assert len(derived) == 1
    assert derived[0].provenance.temporal_perspective == "was"


@pytest.mark.parametrize(
    "text",
    [
        "Bira was 10 years old. Cato is twice as old as Bira. "
        "How old is Cato?",
        "Bira is 10 years old. Cato was twice as old as Bira. "
        "How old was Cato?",
    ],
)
def test_age_relation_chain_rejects_cross_perspective_anchor(project, text) -> None:
    result = solve(text, project.registry)

    assert result.answer.committed is False
    assert not any(
        fact.entity == "cato" and fact.measure == "year"
        for fact in result.store.by_kind(Quantity)
    )


def test_projected_age_requires_present_base_evidence(project) -> None:
    current = solve(
        "Bira is 10 years old. How old will Bira be after 4 years?",
        project.registry,
    )
    historical = solve(
        "Bira was 10 years old. How old will Bira be after 4 years?",
        project.registry,
    )

    assert current.answer.value == 14
    assert historical.answer.committed is False


def test_age_asks_declare_the_shared_temporal_evidence_contract(project) -> None:
    for surface in (
        "How old is Bira?",
        "How old was Bira?",
        "How many years old is Bira?",
        "How much older was Cato than Bira?",
        "How old will Bira be after 4 years?",
    ):
        matched = match_ask(analyze(surface, project.registry), project.registry)
        assert matched is not None
        query = matched[1]
        assert query["evidence_measure_category"] == "age_measure"
        assert query["evidence_temporal_perspective"]


def test_every_non_coordinate_literal_year_ask_declares_temporal_evidence(
    project,
) -> None:
    """Keep future age asks from accidentally reintroducing timeless lookup."""

    for ask in project.registry.asks:
        if ask.resolves.get("measure") != "year":
            continue
        if ask.resolves.get("consumer") == "age-at-year":
            # This family has a stronger coordinate contract: its consumer
            # accepts only AgeAtYear and an explicit target year/marker.
            continue
        assert ask.resolves.get("evidence_measure_category") == "age_measure", ask.id
        assert ask.resolves.get("evidence_temporal_perspective"), ask.id


def test_every_literal_year_quantity_or_relation_emission_declares_perspective(
    project,
) -> None:
    """Direct and relation-derived ages cannot enter the timeless pool."""

    for rule in project.registry.rules:
        for emit in rule.emits:
            if emit.fact not in {"quantity", "relation"}:
                continue
            if emit.fields.get("measure") != "year":
                continue
            assert emit.temporal_perspective, rule.id


def test_age_relation_rules_declare_temporal_provenance(project) -> None:
    present = solve(
        "Bira is 10 years old. Cato is 6 years older than Bira. "
        "How old is Cato?",
        project.registry,
    )
    relations = present.store.by_kind(Relation)

    assert present.answer.value == 16
    assert relations
    assert all(r.provenance.temporal_perspective == "is" for r in relations)
