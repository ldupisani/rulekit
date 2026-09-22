"""Human-valid asks become compact authoring evidence, never runtime data."""

from dataclasses import replace
from pathlib import Path
from shutil import copy2

import pytest

import rulekit.generation.ask_generation as ask_generation
from rulekit.data.project import load_project
from rulekit.generation import (
    choose_exploration_target,
    generate_ask_scenario,
    generate_candidate,
    list_ask_availability,
    resolve_review,
)
from rulekit.generation.reviews import (
    AskScenarioReviewEvidence,
    PremiseReviewEvidence,
    ReviewRecord,
    ReviewDefect,
    PremiseAttachment,
    append_review,
    ask_review_consumer_counts,
    ask_review_evidence,
    ask_review_target_counts,
    premise_review_evidence,
    read_review_history,
    _reviewed_facts_match,
    validated_premise_candidates,
    validated_premise_rule_usage_counts,
)
from rulekit.generation.sample import GenerationError
from rulekit.server.api import ServerState, build_router


CURATED = Path("projects/curated")


@pytest.fixture(scope="module")
def curated():
    return load_project(CURATED)


def _review(candidate, *, fingerprint: str, naturalness=None, query=None):
    scenario = AskScenarioReviewEvidence(
        target_ask=candidate.target_ask,
        scenario_mode=candidate.scenario_mode,
        question=candidate.question,
        text=candidate.text,
        consumer=candidate.consumer,
        query=query or candidate.query,
        premises=[premise["sentence"] for premise in candidate.premises],
        premise_rules=[
            premise["target_rule"] for premise in candidate.premises
        ],
        premise_review_ids=(
            [
                premise.get("validated_review_id")
                for premise in candidate.premises
            ]
            if any(
                premise.get("validated_review_id")
                for premise in candidate.premises
            )
            else []
        ),
        answer=candidate.answer,
        answer_shape=candidate.answer_shape,
        minimal=candidate.minimal,
    )
    return ReviewRecord(
        candidate_id=candidate.id,
        review_kind="ask",
        sentence=candidate.question,
        context_before=scenario.premises,
        ask_scenario=scenario,
        seed=candidate.seed,
        registry_fingerprint=fingerprint,
        verdict="valid",
        requested_bindings=candidate.requested_bindings,
        interpretation_judgment="correct",
        result_judgment="correct_decline",
        naturalness=naturalness,
    )


def test_valid_ask_reviews_collapse_into_one_replayed_coverage_group(
    curated, tmp_path: Path
) -> None:
    candidate = generate_ask_scenario(
        curated,
        ask_id="ask/how-old-is",
        seed=731,
        scenario_mode="ask_only",
        locked_bindings={"verb": "is", "who": "Cato"},
    )
    project = replace(curated, root=tmp_path)
    append_review(
        project,
        _review(
            candidate,
            fingerprint=project.registry.fingerprint,
            naturalness="marginal",
        ),
    )
    preferred = append_review(
        project,
        _review(
            candidate,
            fingerprint=project.registry.fingerprint,
            naturalness="preferred",
        ),
    )

    evidence = ask_review_evidence(project)

    assert evidence["summary"] == {
        "review_count": 2,
        "valid_count": 2,
        "clean_valid_count": 2,
        "action_count": 0,
        "group_count": 1,
        "validated_group_count": 1,
        "regressed_group_count": 0,
        "target_count": 1,
    }
    group = evidence["groups"][0]
    assert group["canonical_review_id"] == preferred["id"]
    assert group["review_count"] == 2
    assert group["replay_status"] == "current"
    assert group["naturalness_counts"] == {
        "preferred": 1,
        "acceptable": 0,
        "marginal": 1,
    }


def test_contextual_ask_replay_rebuilds_its_discourse_group(
    curated, tmp_path: Path
) -> None:
    candidate = generate_ask_scenario(
        curated,
        ask_id="ask/how-many-combined-discourse-group",
        seed=16956212447195,
        scenario_mode="answerable",
    )
    project = replace(curated, root=tmp_path)
    append_review(
        project,
        _review(candidate, fingerprint=project.registry.fingerprint),
    )

    group = ask_review_evidence(project)["groups"][0]

    assert group["target_ask"] == "ask/how-many-combined-discourse-group"
    assert group["replay_status"] == "current"


def test_live_curated_valid_ask_contracts_have_no_regressions(curated) -> None:
    evidence = ask_review_evidence(curated)
    regressions = [
        {
            "target_ask": group["target_ask"],
            "signature": group["signature"],
            "detail": group["replay_detail"],
        }
        for group in evidence["groups"]
        if group["replay_status"] == "regressed"
    ]

    assert regressions == []
    # The location-population grammar replaces one context holding's generic
    # fold with an explicit rule. Do not silently re-approve the human review:
    # prove the exact semantic contract is unchanged, then leave its new
    # provenance visible for human reconfirmation.
    population_review = "rev-bffaf53e4a534b7f"
    for review in read_review_history(curated, limit=10000):
        if review["id"] != population_review:
            continue
        from rulekit.generation.sample import retest_candidate
        from copy import deepcopy

        candidate = retest_candidate(
            curated, rule_id=review["target_rule"], sentence=review["sentence"],
            seed=review["seed"], requested_bindings=review["requested_bindings"],
            context_before=tuple(review["context_before"]),
        ).to_json()
        expected = deepcopy(review["premise_evidence"])
        for fact in expected["facts"]:
            if fact["type"] == "Quantity" and fact["sentence"] == 0:
                assert fact["source"] == "fold"
                fact["source"] = "arithmetic/location-contains-population"
        assert _reviewed_facts_match(candidate["facts"], expected["facts"])
        for field in ("target_status", "target_bindings", "actual_rule_ids"):
            assert candidate[field] == expected[field]
        assert set(candidate["deficiencies"]) <= set(expected["deficiencies"])
        assert not candidate["collisions"]
    premise_regressions = [
        group
        for group in premise_review_evidence(curated)["groups"]
        if group["replay_status"] == "regressed"
        and group["canonical_review_id"]
        not in {
            # Reconciliation batch 57 intentionally invalidated these old
            # positive exemplars. They remain visible until the reviewer
            # rechecks or tombstones them; any unrelated regression fails.
            "rev-57f5398e360b4656",
            "rev-5f3b17c81bc04dab",
            "rev-6f84911dcdef48a8",
            "rev-7b1aa68ba7a448ab",
            population_review,
        }
    ]
    assert premise_regressions == []


def test_old_positive_is_machine_reconfirmed_and_query_drift_regresses(
    curated, tmp_path: Path
) -> None:
    candidate = generate_ask_scenario(
        curated,
        ask_id="ask/how-old-is",
        seed=732,
        scenario_mode="ask_only",
    )
    project = replace(curated, root=tmp_path)
    append_review(project, _review(candidate, fingerprint="old-fingerprint"))
    assert ask_review_evidence(project)["groups"][0]["replay_status"] == (
        "machine_reconfirmed"
    )

    legacy_project = replace(curated, root=tmp_path / "legacy-policy")
    append_review(
        legacy_project,
        _review(
            candidate,
            fingerprint="old-fingerprint",
            query={
                key: value
                for key, value in candidate.query.items()
                if not key.startswith("evidence_")
            },
        ),
    )
    assert ask_review_evidence(legacy_project)["groups"][0][
        "replay_status"
    ] == "machine_reconfirmed"

    drifted_project = replace(curated, root=tmp_path / "drifted")
    append_review(
        drifted_project,
        _review(
            candidate,
            fingerprint=project.registry.fingerprint,
            query={**candidate.query, "entity": "someone-else"},
        ),
    )
    group = ask_review_evidence(drifted_project)["groups"][0]
    assert group["replay_status"] == "regressed"
    assert group["replay_detail"] == "the normalized query changed"
    assert ask_review_evidence(drifted_project)["summary"]["action_count"] == 1


def test_random_ask_generation_prefers_the_least_human_validated_target(
    curated, monkeypatch
) -> None:
    from rulekit.generation import ask_generation

    counts = {
        item.id: 10 for item in list_ask_availability(curated) if item.supported
    }
    counts["ask/how-old-is"] = 0
    monkeypatch.setattr(
        ask_generation,
        "ask_review_target_counts",
        lambda _project: counts,
    )

    candidate = generate_ask_scenario(
        curated,
        seed=733,
        scenario_mode="ask_only",
    )

    assert candidate.target_ask == "ask/how-old-is"


def test_designer_exposes_attention_archive_and_evidence_routes(curated) -> None:
    router = build_router(ServerState(CURATED))
    routes = {(route.path, frozenset(route.methods)) for route in router.routes}
    assert ("/api/generation/review-evidence", frozenset({"GET"})) in routes

    script = Path("src/rulekit/server/static/app.js").read_text()
    assert '"Needs attention"' in script
    assert '"Validated coverage"' in script
    assert '"Evidence archive"' in script
    assert 'evidenceGroup?.replay_status === "regressed"' in script
    markup = Path("src/rulekit/server/static/index.html").read_text()
    assert 'value="validated_premises"' in markup
    assert 'value="least_validated_rule"' in markup


def test_history_filters_action_items_and_archive_is_paginated(
    curated, tmp_path: Path
) -> None:
    candidate = generate_ask_scenario(
        curated,
        ask_id="ask/how-old-is",
        seed=734,
        scenario_mode="ask_only",
    )
    project = replace(curated, root=tmp_path)
    append_review(
        project,
        _review(candidate, fingerprint=project.registry.fingerprint),
    )
    invalid = _review(candidate, fingerprint=project.registry.fingerprint)
    append_review(project, invalid.model_copy(update={"verdict": "invalid"}))

    state = ServerState(CURATED)
    state.project = project
    router = build_router(state)
    endpoint = next(
        route.endpoint
        for route in router.routes
        if route.path == "/api/generation/history"
    )

    attention = endpoint(limit=100, offset=0, view="attention")
    assert attention["total"] == 1
    assert attention["reviews"][0]["verdict"] == "invalid"

    first_page = endpoint(limit=1, offset=0, view="archive")
    second_page = endpoint(limit=1, offset=1, view="archive")
    assert first_page["total"] == 2
    assert len(first_page["reviews"]) == len(second_page["reviews"]) == 1
    assert first_page["reviews"][0]["id"] != second_page["reviews"][0]["id"]
    assert first_page["reviews"][0]["source_ref"]["kind"] == "ask"
    assert first_page["reviews"][0]["source_ref"]["label"] == "ask/how-old-is"


def test_valid_verdict_with_a_defect_stays_actionable_and_is_not_evidence(
    curated, tmp_path: Path
) -> None:
    candidate = generate_ask_scenario(
        curated,
        ask_id="ask/how-old-is",
        seed=735,
        scenario_mode="ask_only",
    )
    project = replace(curated, root=tmp_path)
    review = _review(candidate, fingerprint=project.registry.fingerprint)
    appended = append_review(
        project,
        review.model_copy(
            update={
                "defects": [
                    ReviewDefect(
                        kind="sentence_ungrammatical",
                        attachment=PremiseAttachment(kind="sentence"),
                    )
                ]
            }
        ),
    )

    evidence = ask_review_evidence(project)
    assert evidence["summary"]["valid_count"] == 1
    assert evidence["summary"]["clean_valid_count"] == 0
    assert evidence["summary"]["action_count"] == 1
    assert evidence["groups"][0]["canonical_review_id"] is None
    assert evidence["groups"][0]["replay_status"] == "unvalidated"

    state = ServerState(CURATED)
    state.project = project
    endpoint = next(
        route.endpoint
        for route in build_router(state).routes
        if route.path == "/api/generation/history"
    )
    attention = endpoint(limit=100, offset=0, view="attention")
    assert [row["id"] for row in attention["reviews"]] == [appended["id"]]


def _validated_premise_project(curated, tmp_path: Path, *, defects=None):
    copy2(CURATED / "generation.yaml", tmp_path / "generation.yaml")
    project = replace(curated, root=tmp_path)
    candidate = generate_candidate(
        curated,
        rule_id="arithmetic/stated-age",
        seed=123,
    ).to_json()
    evidence = PremiseReviewEvidence(
        target_status=candidate["target_status"],
        target_bindings=candidate["target_bindings"],
        actual_rule_ids=candidate["actual_rule_ids"],
        facts=candidate["facts"],
        collisions=candidate["collisions"],
        deficiencies=candidate["deficiencies"],
    )
    review = append_review(
        project,
        ReviewRecord(
            candidate_id=candidate["id"],
            review_kind="premise",
            sentence=candidate["sentence"],
            target_rule=candidate["target_rule"],
            premise_evidence=evidence,
            seed=candidate["seed"],
            registry_fingerprint=candidate["registry_fingerprint"],
            verdict="valid",
            requested_bindings=candidate["requested_bindings"],
            defects=defects or [],
            interpretation_judgment="correct",
            result_judgment="correct_facts",
            naturalness="preferred",
        ),
    )
    return project, candidate, review


def _append_valid_premise(project, candidate):
    evidence = PremiseReviewEvidence(
        target_status=candidate["target_status"],
        target_bindings=candidate["target_bindings"],
        actual_rule_ids=candidate["actual_rule_ids"],
        facts=candidate["facts"],
        collisions=candidate["collisions"],
        deficiencies=candidate["deficiencies"],
    )
    return append_review(
        project,
        ReviewRecord(
            candidate_id=candidate["id"],
            review_kind="premise",
            sentence=candidate["sentence"],
            target_rule=candidate["target_rule"],
            premise_evidence=evidence,
            seed=candidate["seed"],
            registry_fingerprint=project.registry.fingerprint,
            verdict="valid",
            requested_bindings=candidate["requested_bindings"],
            interpretation_judgment="correct",
            result_judgment="correct_facts",
            naturalness="preferred",
        ),
    )


def test_defective_valid_premise_is_not_replayed_or_reused(
    curated, tmp_path: Path
) -> None:
    project, _candidate, review = _validated_premise_project(
        curated,
        tmp_path,
        defects=[
            ReviewDefect(
                kind="sentence_ungrammatical",
                attachment=PremiseAttachment(kind="sentence"),
            )
        ],
    )

    assert review["verdict"] == "valid"
    evidence = premise_review_evidence(project)
    assert evidence["summary"]["valid_count"] == 1
    assert evidence["summary"]["clean_valid_count"] == 0
    assert evidence["summary"]["action_count"] == 1
    assert evidence["groups"][0]["canonical_review_id"] is None
    assert validated_premise_candidates(project) == []


def test_valid_premise_is_grouped_and_exactly_replayed(
    curated, tmp_path: Path
) -> None:
    project, candidate, review = _validated_premise_project(curated, tmp_path)

    evidence = premise_review_evidence(project)

    assert evidence["summary"] == {
        "review_count": 1,
        "valid_count": 1,
        "clean_valid_count": 1,
        "action_count": 0,
        "group_count": 1,
        "validated_group_count": 1,
        "regressed_group_count": 0,
        "target_count": 1,
    }
    group = evidence["groups"][0]
    assert group["target_rule"] == "arithmetic/stated-age"
    assert group["canonical_review_id"] == review["id"]
    assert group["replay_status"] == "current"
    replayed = validated_premise_candidates(project)
    assert len(replayed) == 1
    assert replayed[0]["sentence"] == candidate["text"]

    resolve_review(project, review["id"], "confirmed fixed")
    resolved_evidence = premise_review_evidence(project)
    assert resolved_evidence["summary"]["validated_group_count"] == 1


def test_validated_premise_mode_generates_an_answered_ask(
    curated, tmp_path: Path
) -> None:
    project, candidate, review = _validated_premise_project(curated, tmp_path)

    scenario = generate_ask_scenario(
        project,
        ask_id="ask/how-old-is",
        seed=1,
        scenario_mode="validated_premises",
        max_search_attempts=20,
    )

    assert scenario.scenario_mode == "validated_premises"
    assert scenario.target_ask == "ask/how-old-is"
    assert scenario.answer["committed"] is True
    assert scenario.answer["value"] == 2.0
    assert scenario.premises[0]["validated_review_id"] == review["id"]
    assert scenario.premises[0]["sentence"] == candidate["text"]


def test_validated_rate_premise_preserves_modal_verb_and_duration(
    curated, tmp_path: Path
) -> None:
    copy2(CURATED / "generation.yaml", tmp_path / "generation.yaml")
    project = replace(curated, root=tmp_path)
    candidate = generate_candidate(
        curated,
        rule_id="arithmetic/periodic-rate-every-span",
        seed=101,
        locked_bindings={
            "who": "the guardian",
            "aux": "should",
            "verb": "buy",
            "item": "8 pears",
            "freq": "every",
            "span": "90 years",
        },
    ).to_json()
    review = _append_valid_premise(project, candidate)

    # A prescriptive premise cannot silently become a past factual question.
    # The ordinary do-support ask has no compatible surface for `should`, so
    # this evidence/ask pairing is unavailable rather than sampling `did`.
    with pytest.raises(GenerationError, match="after 0 deterministic checks"):
        generate_ask_scenario(
            project,
            ask_id="ask/how-many-rate-span",
            seed=2,
            scenario_mode="validated_premises",
        )

    scenario = generate_ask_scenario(
        project,
        ask_id="ask/how-many-rate-span-modal",
        seed=2,
        scenario_mode="validated_premises",
    )

    assert scenario.query["entity"] == "guardian"
    assert scenario.query["measure"] == "pear"
    assert scenario.query["verb"] == "buy"
    assert scenario.query["span_unit"] == "year"
    assert float(scenario.query["span_value"]) == 90
    assert scenario.question == "How many pears should the guardian buy in 90 years?"
    assert scenario.answer["committed"] is True
    assert scenario.answer["value"] == 8
    assert scenario.premises[0]["validated_review_id"] == review["id"]


def test_validated_frontier_counts_targets_consumers_and_premise_families(
    curated, tmp_path: Path
) -> None:
    project, _candidate, _premise_review = _validated_premise_project(
        curated, tmp_path
    )
    scenario = generate_ask_scenario(
        project,
        ask_id="ask/how-old-is",
        seed=1,
        scenario_mode="validated_premises",
    )
    ask_review = _review(scenario, fingerprint=project.registry.fingerprint)
    append_review(project, ask_review)

    assert ask_review_target_counts(
        project, scenario_mode="ask_only"
    ) == {}
    assert ask_review_target_counts(
        project, scenario_mode="validated_premises"
    ) == {"ask/how-old-is": 1}
    assert ask_review_consumer_counts(
        project, scenario_mode="validated_premises"
    ) == {"single-entity": 1}
    assert validated_premise_rule_usage_counts(project) == {
        "arithmetic/stated-age": 1
    }
    assert ask_review.ask_scenario is not None
    assert ask_review.ask_scenario.premise_review_ids == [
        scenario.premises[0]["validated_review_id"]
    ]


def test_validated_premise_mode_prefers_dimension_specific_age_ask(
    curated, tmp_path: Path
) -> None:
    project, candidate, review = _validated_premise_project(curated, tmp_path)

    scenario = generate_ask_scenario(
        project,
        seed=7629922040354526,
        scenario_mode="validated_premises",
        max_search_attempts=48,
    )

    assert scenario.target_ask in {
        "ask/how-old-is",
        "ask/how-many-years-old-is",
    }
    assert " was " in f" {scenario.question.casefold()} "
    assert "own" not in scenario.question.casefold()
    assert scenario.query["consumer"] == "single-entity"
    assert (
        scenario.query["entity"]
        == scenario.premises[0]["facts"][0]["fields"]["entity"]
    )
    assert scenario.query["measure"] == "year"
    assert scenario.query["verb"] == "be"
    assert scenario.answer["committed"] is True
    assert scenario.premises[0]["validated_review_id"] == review["id"]
    assert scenario.premises[0]["sentence"] == candidate["text"]


def test_validated_premise_mode_ranks_relevant_evidence_before_pool_bound(
    curated, tmp_path: Path, monkeypatch
) -> None:
    project, _candidate, review = _validated_premise_project(curated, tmp_path)
    relevant = validated_premise_candidates(project)[0]
    decoys = [
        {
            **relevant,
            "validated_review_id": f"decoy-{index:02d}",
            "sentence": f"Decoy {index}.",
            "text": f"Decoy {index}.",
            "facts": [
                {
                    "kind": "Relation",
                    "fields": {
                        "subject": f"decoy-{index}",
                        "standard": "other",
                        "measure": "year",
                        "verb": "be",
                        "factor": 1.0,
                        "offset": 2.0,
                    },
                }
            ],
        }
        for index in range(24)
    ]
    monkeypatch.setattr(
        ask_generation,
        "validated_premise_candidates",
        lambda _project: [*decoys, relevant],
    )

    scenario = generate_ask_scenario(
        project,
        ask_id="ask/how-old-is",
        seed=1,
        scenario_mode="validated_premises",
        max_search_attempts=1,
    )

    assert scenario.search_attempts == 1
    assert scenario.premises[0]["validated_review_id"] == review["id"]


def test_premise_generation_can_prioritize_the_least_validated_rule(
    curated, tmp_path: Path
) -> None:
    project, _candidate, _review = _validated_premise_project(curated, tmp_path)

    selection = choose_exploration_target(
        project,
        seed=88,
        objective="least_validated_rule",
    )

    assert selection.rule_id != "arithmetic/stated-age"
    assert selection.objective == "least_validated_rule"


def test_premise_contract_drift_is_a_visible_regression(
    curated, tmp_path: Path
) -> None:
    project, _candidate, review = _validated_premise_project(curated, tmp_path)
    changed = review["premise_evidence"]
    changed["facts"][0]["fields"]["value"] = 999
    # Append a superseding valid row with a deliberately false pinned contract.
    append_review(
        project,
        ReviewRecord.model_validate(
            {
                key: value
                for key, value in {**review, "premise_evidence": changed}.items()
                if key not in {"id", "project", "timestamp"}
            }
        ),
    )

    groups = premise_review_evidence(project)["groups"]
    assert any(group["replay_status"] == "regressed" for group in groups)
