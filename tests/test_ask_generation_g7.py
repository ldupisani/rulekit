"""G7 asks are generated from declared contracts, never benchmark items."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from rulekit.data.project import load_project
from rulekit.data.schemas import AskGenerationDef
from rulekit.generation import (
    GenerationError,
    generate_ask_scenario,
    list_ask_availability,
)
from rulekit.generation.ask_generation import _answer_json
from rulekit.kernel.engine import solve
from rulekit.server.api import AskGenerationBody, ServerState, build_router


CURATED = Path("projects/curated")
GSM8K = Path("projects/gsm8k")
SCRATCH = Path("projects/scratch")


@pytest.fixture(scope="module")
def curated():
    return load_project(CURATED)


@pytest.fixture(scope="module")
def gsm8k():
    return load_project(GSM8K)


def test_ask_availability_keeps_independent_and_contextual_contracts_explicit(
    curated,
) -> None:
    availability = {item.id: item for item in list_ask_availability(curated)}

    assert availability["ask/how-old-is"].supported
    assert availability["ask/how-many-entity"].supported
    assert availability["ask/how-many-each-named-list"].supported
    contextual = availability["ask/which-discourse-group-at-day"]
    assert not contextual.supported
    assert contextual.supported_modes == (
        "answerable",
        "validated_premises",
    )
    assert any("antecedent discourse group" in blocker for blocker in contextual.blockers)
    # The reusable physics pack adds the independently generatable
    # ask/physics-quantity surface to curated.
    assert sum(item.supported for item in availability.values()) == 144
    assert availability["ask/how-many-of-collection-are-label"].supported
    assert availability["ask/how-many-of-collection-are-label"].supported_modes == (
        "ask_only",
        "answerable",
        "validated_premises",
        "missing_evidence",
    )
    assert availability[
        "ask/final-instrument-measurement-reading"
    ].supported
    assert availability["ask/measured-content-in-container"].blockers == (
        "ask requires generated premise evidence; standalone realization is disabled",
    )
    assert availability[
        "ask/measured-content-in-container"
    ].supported_modes == (
        "answerable",
        "validated_premises",
        "missing_evidence",
    )
    assert availability["ask/measured-content-in-container-unit"].blockers == (
        "ask requires generated premise evidence; standalone realization is disabled",
    )
    assert len(availability) == 165
    assert {
        item.id for item in availability.values() if not item.supported
    } == {
        "ask/how-much-credit-need-pay",
        "ask/how-much-need-pay",
        "ask/how-much-need-repay",
        "ask/chem-cost-of-moles",
        "ask/chem-molar-mass",
        "ask/chem-moles-from-grams",
        "ask/chem-weight-of-moles",
        "ask/how-many-all-combined-discourse-group",
        "ask/how-many-combined-discourse-group",
        "ask/how-many-combined-in-all-discourse-group",
        "ask/how-many-content-progress-fraction-of-remainder",
        "ask/how-many-content-progress-fraction-of-remainder-with-of",
        "ask/if-content-progress-fraction-of-remainder-how-many",
        "ask/how-many-individually-discourse-group",
        "ask/how-many-individually-discourse-group-postverbal",
        "ask/how-old-discourse-group-now",
        "ask/how-much-noun-entity-uninverted",
        "ask/measured-content-in-container",
        "ask/measured-content-in-container-unit",
        "ask/what-combined-age-at-year",
        "ask/which-discourse-group-at-day",
    }
    unfilled_deadlines = {
        "ask/how-much-credit-need-pay", "ask/how-much-need-pay", "ask/how-much-need-repay",
    }
    assert all(
        "answerable" in item.supported_modes
        for item in availability.values()
        if not item.supported and not item.id.startswith("ask/chem-")
        and item.id not in unfilled_deadlines
    )
    for ask_id in unfilled_deadlines:
        assert availability[ask_id].supported_modes == ()
        assert availability[ask_id].blockers == ("no project-backed ask filler exists for deadline",)
    assert all(
        item.supported_modes == ()
        and item.blockers == ("no project-backed ask filler exists for f",)
        for item in availability.values()
        if item.id.startswith("ask/chem-")
    )


def test_core_complement_label_ask_is_independently_generatable(curated) -> None:
    candidate = generate_ask_scenario(
        curated,
        ask_id="ask/how-many-of-collection-are-label",
        seed=8242026,
        scenario_mode="ask_only",
    )

    assert candidate.target_ask == "ask/how-many-of-collection-are-label"
    assert candidate.target_bindings["label"] in {"boys", "girls"}


def test_discourse_group_ask_generation_uses_real_antecedent_evidence(curated) -> None:
    candidate = generate_ask_scenario(
        curated,
        ask_id="ask/how-many-combined-discourse-group",
        seed=8242026,
        scenario_mode="answerable",
        locked_bindings={
            "item": "apples",
            "aux": "do",
            "who": "they",
            "verb": "have",
            "agg": "combined",
        },
        max_search_attempts=160,
    )

    assert candidate.target_ask == "ask/how-many-combined-discourse-group"
    assert len(candidate.query["holders"]) >= 2
    assert candidate.answer["committed"]
    assert candidate.premises


@pytest.mark.parametrize(
    ("ask_id", "locks"),
    [
        (
            "ask/measured-content-in-container",
            {
                "content": "sugar",
                "copula": "is",
                "container": "the bucket",
            },
        ),
        (
            "ask/how-many-content-progress-fraction-of-remainder",
            {
                "item": "pages",
                "aux": "should",
                "who": "Aven",
                "verb": "read",
                "target_time": "tomorrow",
                "want": "wants",
                "goal_item": "remaining pages",
            },
        ),
    ],
)
def test_evidence_required_asks_generate_answerable_context(
    curated, ask_id: str, locks: dict[str, str]
) -> None:
    candidate = generate_ask_scenario(
        curated,
        ask_id=ask_id,
        seed=8242026,
        scenario_mode="answerable",
        locked_bindings=locks,
        max_search_attempts=192,
    )

    assert candidate.target_ask == ask_id
    assert candidate.answer["committed"]
    assert candidate.premises


def test_uninverted_ask_is_generated_inside_a_conditional_clause(curated) -> None:
    candidate = generate_ask_scenario(
        curated,
        ask_id="ask/how-much-noun-entity-uninverted",
        seed=8242026,
        scenario_mode="answerable",
        locked_bindings={
            "item": "money",
            "who": "Aven",
            "aux": "will",
            "verb": "have",
        },
        max_search_attempts=128,
    )

    assert candidate.target_ask == "ask/how-much-noun-entity-uninverted"
    assert candidate.text.startswith("If ")
    assert ", how much money Aven will have?" in candidate.text
    assert candidate.answer["committed"]


@pytest.mark.parametrize(
    "ask_id",
    [
        "ask/how-many-all-combined-discourse-group",
        "ask/how-many-combined-in-all-discourse-group",
        "ask/how-many-individually-discourse-group",
        "ask/how-many-individually-discourse-group-postverbal",
        "ask/how-many-content-progress-fraction-of-remainder-with-of",
        "ask/if-content-progress-fraction-of-remainder-how-many",
        "ask/measured-content-in-container-unit",
        "ask/how-old-discourse-group-now",
        "ask/what-combined-age-at-year",
        "ask/which-discourse-group-at-day",
    ],
)
def test_contextual_ask_families_round_trip_through_ordinary_documents(
    curated, ask_id: str
) -> None:
    candidate = generate_ask_scenario(
        curated,
        ask_id=ask_id,
        seed=8242026,
        scenario_mode="answerable",
        reference_year=2026,
        max_search_attempts=192,
    )

    assert candidate.target_ask == ask_id
    assert candidate.reference_year == 2026
    assert candidate.answer["committed"]
    assert len(candidate.premises) >= 2
    if ask_id == "ask/which-discourse-group-at-day":
        assert all(
            row["status"] != "unknown" for row in candidate.answer["value"]
        )


def test_qualified_measurement_dimension_ask_round_trips(curated) -> None:
    candidate = generate_ask_scenario(
        curated,
        ask_id="ask/final-instrument-measurement-reading",
        seed=8242026,
        scenario_mode="ask_only",
        locked_bindings={
            "dimension": "the final weight",
            "observed": "measured",
            "prep": "on",
            "instrument": "the scale",
        },
    )

    assert candidate.question == "What is the final weight measured on the scale?"
    assert candidate.target_ask == "ask/final-instrument-measurement-reading"
    assert candidate.query == {
        "consumer": "measurement-reading",
        "dimension": "weight",
        "instrument": "scale",
        "relation": "on",
    }


@pytest.mark.parametrize(
    "ask_id",
    [
        "ask/calendar-day-of-year",
        "ask/calendar-span-between",
        "ask/chem-cost-of-moles",
        "ask/chem-molar-mass",
        "ask/chem-moles-from-grams",
        "ask/chem-weight-of-moles",
        "ask/coord-distance-between",
        "ask/coord-distance-from",
        "ask/coord-slope-between",
    ],
)
def test_project_declared_structural_ask_values_round_trip(
    gsm8k, ask_id: str
) -> None:
    availability = {item.id: item for item in list_ask_availability(gsm8k)}
    assert availability[ask_id].supported

    candidate = generate_ask_scenario(
        gsm8k,
        ask_id=ask_id,
        seed=8242026,
        scenario_mode="ask_only",
    )

    assert candidate.target_ask == ask_id
    assert candidate.question.endswith("?")
    assert candidate.target_bindings.keys() >= {
        slot
        for slot in ("d1", "f", "p1")
        if slot in candidate.requested_bindings
    }
    if ask_id == "ask/calendar-span-between":
        assert candidate.target_bindings["unit"].endswith("s")
    if ask_id == "ask/calendar-day-of-year":
        assert candidate.question.startswith("What is the day of the year")
    if ask_id.startswith("ask/coord-"):
        assert candidate.question.startswith("What is the ")
    if ask_id in {
        "ask/chem-cost-of-moles",
        "ask/chem-weight-of-moles",
    }:
        assert " moles of " in candidate.question
        assert candidate.query["amount"]
    if ask_id == "ask/chem-moles-from-grams":
        assert " grams of " in candidate.question
        assert candidate.query["amount"]


@pytest.mark.parametrize(
    "ask_id",
    [
        "ask/earn-span",
        "ask/how-many-capacity",
        "ask/how-many-entity-common-noun-start-state",
        "ask/how-many-in-place-start-state",
        "ask/how-many-more-goal-need",
        "ask/how-much-each-item-cost",
        "ask/how-much-item-cost",
        "ask/how-much-pay-for-quantity",
    ],
)
def test_general_english_ask_frontier_round_trips(curated, ask_id: str) -> None:
    candidate = generate_ask_scenario(
        curated,
        ask_id=ask_id,
        seed=8112026,
        scenario_mode="ask_only",
    )

    assert candidate.target_ask == ask_id
    assert candidate.question.endswith("?")
    assert candidate.answer_shape == "decline"


def test_auxiliary_ask_verbs_are_generated_in_the_bare_form(curated) -> None:
    candidates = [
        generate_ask_scenario(
            curated,
            ask_id=ask_id,
            seed=seed,
            scenario_mode="ask_only",
        )
        for ask_id, seed in [
            ("ask/earn-span", 12),
            ("ask/how-many-capacity", 13),
            ("ask/how-many-more-goal-need", 14),
            ("ask/how-much-item-cost", 15),
            ("ask/how-much-pay-for-quantity", 16),
        ]
    ]

    for candidate in candidates:
        assert candidate.target_bindings.get("verb") in {
            "buy",
            "cost",
            "earn",
                "make",
                "need",
                "require",
                "spend",
        }


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
        "evidence_measure_category": "age_measure",
        "evidence_temporal_perspective": "is",
        "evidence_entity_reference": {
            "head": "cato", "owner": None, "label": None,
            "qualifiers": [], "resolved": True,
        },
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


def test_answerable_scenario_locks_normalized_counted_measure_identity(
    curated,
) -> None:
    candidate = generate_ask_scenario(
        curated,
        ask_id="ask/how-many-entity",
        seed=812,
        scenario_mode="answerable",
        locked_bindings={
            "item": "apples",
            "aux": "does",
            "who": "Cato",
            "verb": "have",
        },
    )

    assert candidate.question == "How many apples does Cato have?"
    assert candidate.answer["committed"] is True
    assert candidate.minimal
    assert candidate.premises
    assert any(
        fact["type"] == "Quantity"
        and fact["fields"]["entity"] == "cato"
        and fact["fields"]["measure"] == "apple"
        for premise in candidate.premises
        for fact in premise["facts"]
    )


def test_random_answerable_mode_skips_unsupported_scenario_contracts(
    curated,
) -> None:
    candidate = generate_ask_scenario(
        curated,
        seed=2,
        scenario_mode="answerable",
    )

    # This seed first selects the independently realizable capacity ask, for
    # which the bounded premise search has no answerable construction. Random
    # mode advances deterministically to another answerable ask; an explicit
    # capacity selection does not. Grammar refinements may change which later
    # ask wins without changing that contract.
    assert candidate.target_ask != "ask/how-many-capacity"
    assert candidate.answer["committed"] is True
    assert candidate.premises

    with pytest.raises(GenerationError, match="no complete one-to-three-premise"):
        generate_ask_scenario(
            curated,
            ask_id="ask/how-many-capacity",
            seed=2,
            scenario_mode="answerable",
            max_search_attempts=1,
        )


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
            reference_year=2026,
            locked_bindings={"verb": "is", "who": "Cato"},
        )
    )
    assert payload["target_ask"] == "ask/how-old-is"
    assert payload["scenario_mode"] == "missing_evidence"
    assert payload["reference_year"] == 2026

    html = Path("src/rulekit/server/static/index.html").read_text()
    script = Path("src/rulekit/server/static/app.js").read_text()
    for control_id in (
        "generation-ask",
        "generation-ask-mode",
        "generation-ask-seed",
        "generation-ask-next",
        "generation-ask-candidate",
        "generation-ask-reading",
        "generation-ask-verdicts",
        "generation-ask-defects",
        "generation-ask-note",
        "generation-ask-save-review",
    ):
        assert f'id="{control_id}"' in html
    assert '"/api/generation/asks"' in script
    assert '"/api/generation/ask"' in script
    assert 'review_kind: "ask"' in script
    assert "ask_scenario:" in script
    assert "premise_review_ids:" in script
    assert "Validate as reusable premise evidence" in script
    assert 'review_kind: "premise"' in script
    assert "supported_modes" in script
    assert "reference_year: new Date().getFullYear()" in script


def test_ask_request_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        AskGenerationBody.model_validate(
            {"ask_id": "ask/how-old-is", "benchmark_answer": 8}
        )


def test_contextual_ask_generation_contract_requires_an_explicit_strategy() -> None:
    aligned = AskGenerationDef(
        validated_slot_bindings={
            "span": {"identity_field": "per", "value_field": "denominator"}
        },
        validated_source_bindings={"aux": "premise_aux"},
    )
    assert aligned.validated_slot_bindings["span"].identity_field == "per"
    assert aligned.validated_source_bindings == {"aux": "premise_aux"}

    with pytest.raises(ValidationError, match="must be declared together"):
        AskGenerationDef(context_required=True)
    with pytest.raises(ValidationError, match="must be declared together"):
        AskGenerationDef(context_strategy="evidence")
    with pytest.raises(ValidationError, match="at least one evidence rule"):
        AskGenerationDef(
            context_required=True,
            context_strategy="evidence",
        )

    contract = AskGenerationDef(
        context_required=True,
        context_strategy="evidence",
        evidence_rules=[
            {
                "rule": "invented/support",
                "bindings": {"who": "holders.0"},
            }
        ],
    )
    assert contract.evidence_rules[0].bindings == {"who": "holders.0"}
