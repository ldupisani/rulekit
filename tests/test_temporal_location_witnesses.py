"""Finite-domain temporal location witnesses and conservative persistence."""

from pathlib import Path

import pytest
from fastapi.encoders import jsonable_encoder

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.kernel.engine import analyze, solve
from rulekit.kernel.model import (
    LocationConstraint,
    LocationConstraintViolation,
    LocationEvent,
    LocationTransitionAbsence,
)
from rulekit.server.api import ServerState, TraceBody, build_router


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"


@pytest.fixture(scope="module")
def registry():
    return load_project(CURATED).registry


NARRATIVE = (
    "Tom arrived at the garden yesterday. "
    "Sally will arrive at the garden tomorrow. "
    "Bob arrived at the garden today. "
)


@pytest.mark.parametrize(
    "question",
    [
        "If nobody can leave the garden, which of them are at the garden today?",
        "If nobody can leave the garden. Which of them are at the garden today?",
    ],
)
def test_question_scoped_impossibility_supports_conservative_persistence(
    registry, question: str
) -> None:
    result = solve(NARRATIVE + question, registry)

    assert result.answer.kind == "witnesses"
    assert result.answer.value == [
        {"entity": "tom", "status": "supported"},
        {"entity": "sally", "status": "unknown"},
        {"entity": "bob", "status": "supported"},
    ]
    assert [(reading.text, reading.assumption) for reading in result.assumptions] == [
        ("nobody can leave the garden.", True)
    ]
    constraint = result.store.by_kind(LocationConstraint)[0]
    assert constraint.place == "garden"
    assert constraint.provenance.assumption is True
    assert {
        (event.entity, event.place, event.effect)
        for event in result.store.by_kind(LocationEvent)
    } == {
        ("tom", "garden", "initiates"),
        ("sally", "garden", "initiates"),
        ("bob", "garden", "initiates"),
    }
    assert [step.rule for step in result.answer.proof.steps] == [
        "inference/location-persistence",
        "inference/location-at-event",
    ]


def test_missing_termination_constraint_does_not_turn_silence_into_persistence(
    registry,
) -> None:
    result = solve(
        NARRATIVE + "Which of them are at the garden today?",
        registry,
    )

    assert result.answer.value == [
        {"entity": "tom", "status": "unknown"},
        {"entity": "sally", "status": "unknown"},
        {"entity": "bob", "status": "supported"},
    ]


def test_explicit_no_departure_supports_narrative_interval_persistence(
    registry,
) -> None:
    result = solve(
        NARRATIVE
        + "Nobody left the garden. "
        + "Which of them are at the garden today?",
        registry,
    )

    assert result.answer.value == [
        {"entity": "tom", "status": "supported"},
        {"entity": "sally", "status": "unknown"},
        {"entity": "bob", "status": "supported"},
    ]
    absence = result.store.by_kind(LocationTransitionAbsence)[0]
    assert (
        absence.place,
        absence.transition,
        absence.scope,
        absence.subject_class,
    ) == ("garden", "terminates", "narrative-through-reference", "person")
    assert absence.provenance.assumption is False
    assert [step.rule for step in result.answer.proof.steps] == [
        "inference/location-no-departure-persistence",
        "inference/location-at-event",
    ]


def test_observed_departure_conflicts_with_no_departure_interval(registry) -> None:
    result = solve(
        "Tom arrived at the garden yesterday. "
        "Tom left the garden today. "
        "Sally will arrive at the garden tomorrow. "
        "Nobody left the garden. "
        "Which of them are at the garden today?",
        registry,
    )

    assert result.answer.kind == "decline"
    assert "observed departure conflicts" in result.answer.reason


def test_future_departure_does_not_conflict_with_past_no_departure(registry) -> None:
    result = solve(
        "Tom arrived at the garden yesterday. "
        "Tom will leave the garden tomorrow. "
        "Bob arrived at the garden today. "
        "Nobody left the garden. "
        "Which of them are at the garden today?",
        registry,
    )

    assert result.answer.value == [
        {"entity": "tom", "status": "supported"},
        {"entity": "bob", "status": "supported"},
    ]


@pytest.mark.parametrize(
    "sentence",
    [
        "Nobody leaves the garden.",
        "Nobody left a garden.",
        "Nobody left the pencil.",
    ],
)
def test_no_departure_rule_keeps_its_exact_boundary(registry, sentence: str) -> None:
    result = solve(NARRATIVE + sentence, registry)

    assert result.store.by_kind(LocationTransitionAbsence) == []


def test_remainder_left_keeps_its_adjective_reading(registry) -> None:
    reading = analyze("How many apples are left?", registry)
    left = next(unit for unit in reading.units if unit.surface.lower() == "left")

    assert left.sense() == "adjective"


def test_direct_location_observation_is_a_supported_witness(registry) -> None:
    result = solve(
        "Tom was at the garden today. Sally will arrive at the garden tomorrow. "
        "Which of them are at the garden today?",
        registry,
    )

    assert result.answer.value == [
        {"entity": "tom", "status": "supported"},
        {"entity": "sally", "status": "unknown"},
    ]
    assert any(
        event.entity == "tom" and event.effect == "holds"
        for event in result.store.by_kind(LocationEvent)
    )


def test_direct_negative_location_observation_is_a_contradicted_witness(
    registry,
) -> None:
    result = solve(
        "Tom was not at the garden today. "
        "Sally will arrive at the garden tomorrow. "
        "Which of them are at the garden today?",
        registry,
    )

    assert result.answer.value == [
        {"entity": "tom", "status": "contradicted"},
        {"entity": "sally", "status": "unknown"},
    ]
    assert any(
        event.entity == "tom" and event.effect == "not-holds"
        for event in result.store.by_kind(LocationEvent)
    )
    assert [step.rule for step in result.answer.proof.steps] == [
        "inference/location-not-at-event"
    ]


def test_conflicting_direct_location_observations_decline(registry) -> None:
    result = solve(
        "Tom arrived at the garden today. "
        "Tom was not at the garden today. "
        "Sally will arrive at the garden tomorrow. "
        "Which of them are at the garden today?",
        registry,
    )

    assert result.answer.kind == "decline"
    assert "conflicting direct location evidence" in result.answer.reason


def test_prohibition_modal_does_not_become_physical_impossibility(registry) -> None:
    result = solve(
        NARRATIVE
        + "If nobody may leave the garden, which of them are at the garden today?",
        registry,
    )

    assert result.answer.kind == "decline"
    assert result.store.by_kind(LocationConstraint) == []


def test_detached_assumption_must_be_immediately_before_the_question(
    registry,
) -> None:
    result = solve(
        "Tom arrived at the garden yesterday. "
        "If nobody can leave the garden. "
        "Sally will arrive at the garden tomorrow. "
        "Bob arrived at the garden today. "
        "Which of them are at the garden today?",
        registry,
    )

    assert result.answer.kind == "decline"
    assert result.store.by_kind(LocationConstraint) == []
    assert result.assumptions == []


def test_observed_departure_conflicts_with_impossible_termination(registry) -> None:
    result = solve(
        NARRATIVE
        + "Tom leaves the garden today. "
        + "If nobody can leave the garden, which of them are at the garden today?",
        registry,
    )

    assert result.answer.kind == "decline"
    assert "location constraint conflict" in result.answer.reason
    assert len(result.store.by_kind(LocationConstraintViolation)) == 1


def test_instant_marker_does_not_enter_the_day_grained_ask(registry) -> None:
    result = solve(
        NARRATIVE + "Which of them are at the garden now?",
        registry,
    )

    assert result.answer.kind == "decline"
    assert result.answer.reason == "no ask shape recognizes this question"


def test_location_impossibility_rule_is_strictly_generatable() -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id="logic-arithmetic/universal-location-exit-impossibility",
        seed=0,
        locked_bindings={
            "subject": "nobody",
            "modal": "can",
            "verb": "leave",
            "place": "garden",
        },
    )

    assert candidate.sentence == "Nobody can leave the garden."
    assert candidate.target_status == "matched"
    assert all(row.status == "passed" for row in candidate.premises)


def test_no_departure_rule_is_strictly_generatable() -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id="logic-arithmetic/universal-location-exit-absence",
        seed=0,
        locked_bindings={
            "subject": "nobody",
            "verb": "left",
            "place": "garden",
        },
    )

    assert candidate.sentence == "Nobody left the garden."
    assert candidate.target_status == "matched"
    assert all(row.status == "passed" for row in candidate.premises)


def test_designer_trace_serializes_group_reference_targets() -> None:
    router = build_router(ServerState(CURATED))
    endpoint = next(
        route.endpoint
        for route in router.routes
        if route.path == "/api/trace" and "POST" in route.methods
    )
    trace = endpoint(
        TraceBody(
            text=NARRATIVE
            + "Nobody left the garden. "
            + "Which of them are at the garden today?"
        )
    )

    encoded = jsonable_encoder(trace)
    them = next(
        unit
        for unit in encoded["sentences"][-1]["units"]
        if unit["surface"].lower() == "them"
    )
    refers = next(ob for ob in them["obligations"] if ob["need"] == "refers")

    assert refers["target"] == ["Tom", "Sally", "Bob"]
    assert encoded["answer"]["kind"] == "witnesses"
