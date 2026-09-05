"""Context-dependent readers remain honest, reviewable generation targets."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import (
    ReviewRecord,
    generate_candidate,
    list_rule_availability,
    retest_candidate,
)
from rulekit.server.api import ServerState, build_router


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
CONTEXTUAL_RULES = {
    "arithmetic/sequential-percent-remainder-partition-anaphoric",
    "arithmetic/sequential-percent-remainder-partition-initial-share",
    "arithmetic/sequential-percent-remainder-partition-remaining-share",
    "arithmetic/sequential-percent-remainder-partition-prefix",
    "arithmetic/sequential-percent-remainder-partition-completion",
}
SAFETY_RULES = {
    "arithmetic/capacity-progress-anaphoric-multiplier-safety",
    "arithmetic/dangling-comparative-safety",
    "arithmetic/partition-membership-of-mass-measure-safety",
    "arithmetic/realized-progress-anaphoric-multiplier-safety",
    "arithmetic/realized-progress-deictic-anaphoric-multiplier-safety",
    "arithmetic/ratio-split-of-to-possession-safety",
    "logic-arithmetic/universal-all-have-incompatible-item-safety",
    "logic-arithmetic/universal-all-have-quantity-pp-incompatible-item-safety",
}


@pytest.fixture(scope="module")
def project():
    return load_project(CURATED)


def test_only_declared_non_generative_rules_remain_outside_generation(project) -> None:
    availability = {
        item.id: item for item in list_rule_availability(project)
    }

    assert len(availability) == 173
    assert {item.id for item in availability.values() if not item.supported} == (
        SAFETY_RULES | {"arithmetic/measured-content-resulting-total-gapped"}
    )
    assert all(
        availability[rule_id].generation == "contextual"
        and availability[rule_id].supported
        for rule_id in CONTEXTUAL_RULES
    )
    declared = {
        rule.id: rule.generation_context
        for rule in project.registry.rules
        if rule.id in CONTEXTUAL_RULES
    }
    assert all(context is not None for context in declared.values())
    assert all(
        context.required_fact_counts == {"partition_quantity": 3}
        for context in declared.values()
        if context is not None
    )
    assert availability[
        "arithmetic/affine-frame-relation-as-standard"
    ].supported


@pytest.mark.parametrize("rule_id", sorted(CONTEXTUAL_RULES))
def test_contextual_target_round_trips_inside_complete_discourse(
    rule_id: str, project
) -> None:
    candidate = generate_candidate(project, rule_id=rule_id, seed=8701)

    assert candidate.target_status == "matched"
    assert candidate.context_before or candidate.context_after
    assert candidate.target_sentence_index == len(candidate.context_before)
    assert candidate.to_json()["text"] == " ".join(
        (*candidate.context_before, candidate.sentence, *candidate.context_after)
    )
    assert "the the rest" not in candidate.to_json()["text"].casefold()
    assert "enrolling" not in candidate.sentence.casefold()
    assert any(fact["type"] == "PartitionQuantity" for fact in candidate.facts)


def test_contextual_retest_preserves_the_pinned_discourse(project) -> None:
    before = generate_candidate(
        project,
        rule_id=(
            "arithmetic/sequential-percent-remainder-partition-remaining-share"
        ),
        seed=8702,
    )
    after = retest_candidate(
        project,
        rule_id=before.target_rule or "",
        sentence=before.sentence,
        seed=before.seed,
        requested_bindings=before.requested_bindings,
        attempts=before.attempts,
        context_before=before.context_before,
        context_after=before.context_after,
    )

    assert after.target_status == "matched"
    assert after.to_json()["text"] == before.to_json()["text"]
    assert after.id == before.id


def test_generation_api_separates_safety_consumers_from_targets() -> None:
    router = build_router(ServerState(CURATED))
    endpoint = next(
        route.endpoint
        for route in router.routes
        if route.path == "/api/generation/rules" and "GET" in route.methods
    )

    payload = endpoint()

    assert payload["supported"] == 164
    assert payload["total"] == 165
    assert payload["safety_total"] == 8
    assert {rule["id"] for rule in payload["safety_rules"]} == SAFETY_RULES
    assert not ({rule["id"] for rule in payload["rules"]} & SAFETY_RULES)


@pytest.mark.parametrize("rule_id", sorted(SAFETY_RULES))
def test_negative_boundary_mode_round_trips_safety_without_facts(
    rule_id: str, project
) -> None:
    candidate = generate_candidate(
        project,
        rule_id=rule_id,
        seed=8801,
        generation_mode="safety_boundary",
    )

    assert candidate.target_status == "matched"
    assert candidate.facts == ()
    assert rule_id in candidate.to_json()["safety_rule_ids"]
    assert candidate.to_json()["actual_rule_ids"] == []


def test_review_record_can_preserve_contextual_evidence(project) -> None:
    candidate = generate_candidate(
        project,
        rule_id="arithmetic/sequential-percent-remainder-partition-prefix",
        seed=8703,
    )
    review = ReviewRecord(
        candidate_id=candidate.id,
        sentence=candidate.sentence,
        context_before=list(candidate.context_before),
        context_after=list(candidate.context_after),
        target_rule=candidate.target_rule,
        seed=candidate.seed,
        registry_fingerprint=candidate.registry_fingerprint,
        verdict="valid",
        requested_bindings=candidate.requested_bindings,
    )

    assert review.context_before == list(candidate.context_before)
    assert review.context_after == list(candidate.context_after)


def test_designer_highlights_context_and_reads_the_complete_text() -> None:
    javascript = (ROOT / "src/rulekit/server/static/app.js").read_text()

    assert 'rule.generation === "contextual"' in javascript
    assert '"generation-target-sentence contextual"' in javascript
    assert "state.candidate.text || state.candidate.sentence" in javascript
    assert "safety consumers available as negative boundaries" in javascript
    assert 'mode === "safety_boundary"' in javascript
