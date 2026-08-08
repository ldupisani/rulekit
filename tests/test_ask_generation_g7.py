"""G7 asks are generated from declared contracts, never benchmark items."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from rulekit.data.project import load_project
from rulekit.generation import generate_ask_scenario, list_ask_availability
from rulekit.generation.ask_generation import _answer_json
from rulekit.kernel.engine import solve
from rulekit.server.api import AskGenerationBody, ServerState, build_router


CURATED = Path("projects/curated")
SCRATCH = Path("projects/scratch")


@pytest.fixture(scope="module")
def curated():
    return load_project(CURATED)


def test_ask_availability_keeps_independent_and_contextual_contracts_explicit(
    curated,
) -> None:
    availability = {item.id: item for item in list_ask_availability(curated)}

    assert availability["ask/how-old-is"].supported
    assert availability["ask/how-many-entity"].supported
    assert availability["ask/how-many-each-named-list"].supported
    contextual = availability["ask/which-discourse-group-at-day"]
    assert not contextual.supported
    assert contextual.blockers == (
        "ask requires an antecedent discourse group; generate it as a "
        "contextual scenario",
    )
    assert 0 < sum(item.supported for item in availability.values()) < len(
        availability
    )


def test_ask_surface_is_exact_and_deterministic(curated) -> None:
    kwargs = {
        "ask_id": "ask/how-old-is",
        "seed": 731,
        "scenario_mode": "ask_only",
        "locked_bindings": {"verb": "is", "who": "Cato"},
    }

    first = generate_ask_scenario(curated, **kwargs)
    second = generate_ask_scenario(curated, **kwargs)

    assert first == second
    assert first.question == "How old is Cato?"
    assert first.target_ask == "ask/how-old-is"
    assert first.target_bindings == {"verb": "is", "who": "Cato"}
    assert first.query == {
        "consumer": "single-entity",
        "entity": "cato",
        "measure": "year",
        "verb": "be",
    }
    assert first.answer_shape == "decline"
    assert first.premises == ()
    assert first.minimal


def test_factual_auxiliaries_and_declared_plural_surfaces_are_realizable(
    curated,
) -> None:
    candidate = generate_ask_scenario(
        curated,
        ask_id="ask/how-many-entity",
        seed=812,
        scenario_mode="ask_only",
        locked_bindings={
            "item": "apples",
            "aux": "does",
            "who": "Cato",
            "verb": "have",
        },
    )

    assert candidate.question == "How many apples does Cato have?"
    assert candidate.target_bindings["aux"] == "does"
    assert candidate.query["measure"] == "apple"


def test_answerable_scenario_uses_one_generated_removal_minimal_premise(
    curated,
) -> None:
    candidate = generate_ask_scenario(
        curated,
        ask_id="ask/how-old-is",
        seed=81,
        scenario_mode="answerable",
        locked_bindings={"verb": "is", "who": "Cato"},
    )

    assert candidate.question == "How old is Cato?"
    assert candidate.answer_shape == "number"
    assert candidate.answer["committed"] is True
    assert candidate.minimal
    assert len(candidate.premises) == 1
    assert candidate.premises[0]["target_status"] == "matched"
    replay = solve(candidate.text, curated.registry)
    assert replay.answer.kind == "number"
    assert replay.answer.value == candidate.answer["value"]
    assert not solve(candidate.question, curated.registry).answer.committed


def test_missing_evidence_is_deliberate_and_separate_from_answerable_coverage(
    curated,
) -> None:
    candidate = generate_ask_scenario(
        curated,
        ask_id="ask/how-old-is",
        seed=81,
        scenario_mode="missing_evidence",
        locked_bindings={"verb": "is", "who": "Cato"},
    )

    assert candidate.question == "How old is Cato?"
    assert candidate.text == candidate.question
    assert candidate.premises == ()
    assert candidate.answer_shape == "decline"
    assert candidate.answer["committed"] is False
    assert candidate.search_attempts == 0


@pytest.mark.parametrize(
    ("project_root", "text", "shape"),
    [
        (
            CURATED,
            "Cato is 8 years old. How old is Cato?",
            "number",
        ),
        (
            CURATED,
            "Aven has 3 apples. Bira has 5 apples. "
            "How many apples do Aven and Bira each have?",
            "series",
        ),
        (
            CURATED,
            "Tom arrived at the garden yesterday. "
            "Sally will arrive at the garden tomorrow. "
            "Bob arrived at the garden today. Nobody left the garden. "
            "Which of them are at the garden today?",
            "witnesses",
        ),
        (
            SCRATCH,
            "Rex is a dog. Is it true that Rex is a dog?",
            "verdict",
        ),
        (
            SCRATCH,
            "Nadia is an otter. Nadia has a badge. "
            "Is it true that an otter has a badge?",
            "clarification",
        ),
        (
            CURATED,
            "How old is Cato?",
            "decline",
        ),
    ],
)
def test_scenario_serialization_preserves_every_answer_shape(
    project_root: Path,
    text: str,
    shape: str,
) -> None:
    project = load_project(project_root)
    payload, actual_shape = _answer_json(solve(text, project.registry).answer)

    assert actual_shape == shape
    assert payload["kind"] in {
        "number",
        "series",
        "witnesses",
        "verdict",
        "decline",
    }
    assert (payload["clarification"] is not None) == (shape == "clarification")


def test_designer_exposes_separate_ask_routes_and_controls(curated) -> None:
    router = build_router(ServerState(CURATED))
    routes = {(route.path, frozenset(route.methods)) for route in router.routes}
    assert ("/api/generation/asks", frozenset({"GET"})) in routes
    assert ("/api/generation/ask", frozenset({"POST"})) in routes

    endpoint = next(
        route.endpoint
        for route in router.routes
        if route.path == "/api/generation/ask" and "POST" in route.methods
    )
    payload = endpoint(
        AskGenerationBody(
            ask_id="ask/how-old-is",
            seed=997,
            scenario_mode="missing_evidence",
            locked_bindings={"verb": "is", "who": "Cato"},
        )
    )
    assert payload["target_ask"] == "ask/how-old-is"
    assert payload["scenario_mode"] == "missing_evidence"

    html = Path("src/rulekit/server/static/index.html").read_text()
    script = Path("src/rulekit/server/static/app.js").read_text()
    for control_id in (
        "generation-ask",
        "generation-ask-mode",
        "generation-ask-seed",
        "generation-ask-next",
        "generation-ask-candidate",
        "generation-ask-reading",
    ):
        assert f'id="{control_id}"' in html
    assert '"/api/generation/asks"' in script
    assert '"/api/generation/ask"' in script


def test_ask_request_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        AskGenerationBody.model_validate(
            {"ask_id": "ask/how-old-is", "benchmark_answer": 8}
        )
