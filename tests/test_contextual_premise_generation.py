"""Context-dependent readers remain honest, reviewable generation targets."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import (
    ReviewRecord,
    generate_candidate,
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


def test_curated_premise_generation_inventory(curated_availability) -> None:
    rows = curated_availability.values()
    assert len(rows) == 1167
    assert sum(item.supported for item in rows) == 1039
    blocked = {item.id for item in rows if not item.supported}
    assert len(blocked) == 128
    assert all(not item.blockers or item.id in blocked for item in rows)
    assert blocked == SAFETY_RULES | {
        "arithmetic/collective-companions-measurements",
        "arithmetic/collective-companions-measurements-planned",
        "arithmetic/counted-companions-measurements",
        "arithmetic/counted-companions-measurements-planned",
        "arithmetic/group-member-measurements",
        "arithmetic/individual-companions-measurements",
        "arithmetic/individual-companions-measurements-planned",
        "arithmetic/owned-scaled-area-difference",
        "arithmetic/partial-indexed-section",
        "arithmetic/partial-indexed-section-at-clock-reading",
        "arithmetic/partial-indexed-section-unmarked",
        "arithmetic/partial-indexed-section-with-source",
        "arithmetic/skipped-indexed-section-remainder",
        "arithmetic/skipped-indexed-section-remainder-unmarked",
        "arithmetic/skipped-remainder-and-further-sections",
        "arithmetic/skipped-remainder-and-further-sections-unmarked",
        "arithmetic/coordinated-relative-price-item",
        "arithmetic/coordinated-relative-price-item-total",
        "arithmetic/absence-of-other-occupants",
        "arithmetic/account-anaphoric-full-settlement",
        "arithmetic/account-coordinated-payment",
        "arithmetic/account-coordinated-payment-amount",
        "arithmetic/account-coordinated-repayment",
        "arithmetic/account-coordinated-repayment-amount",
        "arithmetic/account-referenced-payment",
        "arithmetic/account-relative-full-settlement",
        "arithmetic/affiliated-recipient-groups",
        "arithmetic/affine-recipient-transfer",
        "arithmetic/collected-qualified-nested-population",
        "arithmetic/coordinated-qualified-relative-stock-associated-fraction",
        "arithmetic/coordinated-qualified-relative-stock-associated-multiplier",
        "arithmetic/cut-measured-region-continuation",
        "arithmetic/distributed-relative-use",
        "arithmetic/employment-bonus-context",
        "arithmetic/event-capacity-matching-membership",
        "arithmetic/exhaustive-section-remaining-list",
        "arithmetic/existential-inventory-bare",
        "arithmetic/existential-inventory-leading-location",
        "arithmetic/existential-inventory-trailing-location",
        "arithmetic/explicit-allocation-recipients",
        "arithmetic/fractional-resource-elided-use-continuation",
        "arithmetic/fractional-resource-named-use-continuation",
        "arithmetic/fractional-resource-remainder-use-continuation",
        "arithmetic/fractional-resource-residual-use-continuation",
        "arithmetic/fractional-resource-use-continuation",
        "arithmetic/group-attendance-intention",
        "arithmetic/income-increase-with-expense-copula",
        "arithmetic/income-increase-with-expense-share",
        "arithmetic/indexed-completion-amount-label",
        "arithmetic/material-container-service-capacity",
        "arithmetic/measured-content-resulting-total-gapped",
        "arithmetic/measured-outcome-with-source-inventory",
        "arithmetic/measured-resource-removal-length-continuation",
        "arithmetic/measured-resource-removal-length-continuation-counted-purpose",
        "arithmetic/measured-resource-removal-mass-continuation",
        "arithmetic/measured-resource-removal-mass-continuation-counted-purpose",
        "arithmetic/measured-resource-removal-volume-continuation",
        "arithmetic/measured-resource-removal-volume-continuation-counted-purpose",
        "arithmetic/member-rated-capacity-work",
        "arithmetic/named-activity-account",
        "arithmetic/named-allocation-group",
        "arithmetic/named-group-collection-shopping-intention",
        "arithmetic/named-group-item-shopping-intention",
        "arithmetic/named-group-new-collection-shopping-intention",
        "arithmetic/named-group-new-item-shopping-intention",
        "arithmetic/named-group-shopping-intention",
        "arithmetic/named-individual-completion-deadline",
        "arithmetic/named-individual-portions",
        "arithmetic/named-joint-earnings",
        "arithmetic/named-month-activity-schedule",
        "arithmetic/named-portion-consumption",
        "arithmetic/named-sales-purpose-context",
        "arithmetic/named-shared-completion-context",
        "arithmetic/named-shared-completion-participation",
        "arithmetic/named-shared-quantity",
        "arithmetic/named-unspecified-allocation-group",
        "arithmetic/one-document-per-listed-recipient",
        "arithmetic/path-gap-and-exit-numeric-numeric",
        "arithmetic/path-gap-and-exit-numeric-numeric-reference01",
        "arithmetic/path-gap-and-exit-numeric-numeric-reference10",
        "arithmetic/path-gap-and-exit-numeric-numeric-reference11",
        "arithmetic/path-gap-and-exit-numeric-word",
        "arithmetic/path-gap-and-exit-numeric-word-reference01",
        "arithmetic/path-gap-and-exit-numeric-word-reference10",
        "arithmetic/path-gap-and-exit-numeric-word-reference11",
        "arithmetic/path-gap-and-exit-word-numeric",
        "arithmetic/path-gap-and-exit-word-numeric-reference01",
        "arithmetic/path-gap-and-exit-word-numeric-reference10",
        "arithmetic/path-gap-and-exit-word-numeric-reference11",
        "arithmetic/path-immediate-exit-numeric",
        "arithmetic/path-immediate-exit-numeric-reference",
        "arithmetic/path-leg-distance-numeric",
        "arithmetic/path-leg-distance-numeric-reference",
        "arithmetic/path-unknown-leg-numeric",
        "arithmetic/path-unknown-leg-numeric-reference",
        "arithmetic/periodic-purpose-expense-counted-period-leading",
        "arithmetic/periodic-purpose-expense-counted-period-trailing",
        "arithmetic/population-average-rate-rest",
        "arithmetic/population-rate-assessment-finite-qualified-attribute",
        "arithmetic/population-rate-assessment-progressive-qualified-attribute",
        "arithmetic/population-rate-attribution",
        "arithmetic/population-rate-inquiry-qualified-attribute",
        "arithmetic/prior-habitual-income-share",
        "arithmetic/prior-income-spending-share",
        "arithmetic/process-part-duration-numeric-index",
        "arithmetic/process-relative-part-duration-numeric-index",
        "arithmetic/qualitative-location-flow-context",
        "arithmetic/relative-item-multiple-of-combined-counts",
        "arithmetic/relative-recipient-transfer",
        "arithmetic/scheduled-unit-count",
        "arithmetic/stock-section-counted-list",
        "arithmetic/threshold-share",
        "arithmetic/threshold-share-reported",
        "arithmetic/threshold-share-unindexed",
        "arithmetic/two-part-personal-name",
        "arithmetic/with-inventory-bare",
        "arithmetic/with-inventory-located",
        "arithmetic/year-qualified-month-schedule",
        "arithmetic/named-month-material-to-recipient",
        "arithmetic/year-qualified-material-to-recipient",
    }


def test_contextual_generation_declares_its_required_evidence(project, curated_availability) -> None:
    assert all(
        curated_availability[rule_id].generation == "contextual"
        and curated_availability[rule_id].supported
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
    assert curated_availability[
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


def test_generation_api_separates_safety_consumers_from_targets(curated_availability) -> None:
    router = build_router(ServerState(CURATED))
    endpoint = next(
        route.endpoint
        for route in router.routes
        if route.path == "/api/generation/rules" and "GET" in route.methods
    )

    payload = endpoint()

    assert payload["supported"] == sum(rule.supported for rule in curated_availability.values())
    assert payload["total"] == len(curated_availability) - len(SAFETY_RULES)
    assert payload["safety_total"] == len(SAFETY_RULES)
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
