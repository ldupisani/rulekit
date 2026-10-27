"""Saved issue lifecycle and fresh evidence are independent, append-only claims."""

from dataclasses import replace
from pathlib import Path
from shutil import copy2

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from rulekit.generation import (
    generate_candidate,
    promote_sentence_review_candidate,
    retest_candidate,
)
from rulekit.generation.reviews import (
    AskScenarioReviewEvidence,
    PremiseReviewEvidence,
    ReviewRecord,
    append_review,
    ask_review_evidence,
    delete_review,
    premise_review_evidence,
    read_review_history,
    review_attention_reasons,
    review_needs_attention,
    review_path,
    update_review,
)
from rulekit.generation.review_workflow import UpdatedEvidenceBody
from rulekit.server.api import (
    ReviewResolutionBody,
    ServerState,
    build_router,
    TraceBody,
    trace_project,
)


@pytest.fixture
def workbench(tmp_path):
    state = ServerState(Path("projects/curated"))
    state.project = replace(state.project, root=tmp_path)
    copy2("projects/curated/generation.yaml", tmp_path / "generation.yaml")
    router = build_router(state)

    def call(suffix, *args, method="POST", **kwargs):
        endpoint = next(
            r.endpoint
            for r in router.routes
            if r.path == "/api/generation/" + suffix and method in r.methods
        )
        return endpoint(*args, **kwargs)

    return state, call


def source(state, *, deficient=True, sentence=False, context=False):
    if sentence:
        candidate = promote_sentence_review_candidate(
            state.project, sentence="Luma has 4 apples."
        ).to_json()
    else:
        candidate = generate_candidate(
            state.project, rule_id="arithmetic/stated-age", seed=123
        ).to_json()
    if context:
        candidate["context_before"] = ["Luma has 4 apples."]
        candidate["context_after"] = ["Navo has 3 apples."]
    evidence = (
        None
        if sentence
        else PremiseReviewEvidence(
            **{
                k: candidate[k]
                for k in (
                    "target_status",
                    "target_bindings",
                    "actual_rule_ids",
                    "facts",
                    "collisions",
                    "deficiencies",
                )
            }
        )
    )
    if deficient and evidence:
        evidence.deficiencies.append("A recorded reader obligation was unmet.")
    record = ReviewRecord(
        candidate_id=candidate["id"],
        origin=candidate["origin"],
        review_kind="sentence" if sentence else "premise",
        sentence=candidate["sentence"],
        seed=candidate["seed"],
        registry_fingerprint=candidate["registry_fingerprint"],
        target_rule=candidate["target_rule"],
        premise_evidence=evidence,
        context_before=candidate.get("context_before", []),
        context_after=candidate.get("context_after", []),
        verdict="valid",
        interpretation_judgment="correct",
        result_judgment="correct_facts",
        note="Original human judgment",
        requested_bindings=candidate["requested_bindings"],
    )
    return append_review(state.project, record)


def confirmation(retest, **changes):
    return UpdatedEvidenceBody(
        **{
            "retest_token": retest["retest_token"],
            "verdict": "valid",
            "interpretation_judgment": "correct",
            "result_judgment": "correct_facts",
            "note": "Reviewed the current reading.",
            **changes,
        }
    )


def test_attention_reasons_explain_valid_rows_and_current_regressions(workbench):
    state, call = workbench
    old = source(state)
    attention = call("history", method="GET", view="attention")
    row = attention["reviews"][0]
    assert row["id"] == old["id"] and row["verdict"] == "valid"
    assert row["attention_reasons"] == [
        {
            "code": "reader_deficiency",
            "source": "recorded",
            "detail": "A recorded reader obligation was unmet.",
        }
    ]
    assert review_needs_attention(old) == bool(review_attention_reasons(old))
    # A clean positive whose stored facts disagree with current replay must
    # explain its current regression as well, without changing its verdict.
    other = source(state, deficient=False)
    other["premise_evidence"]["facts"][0]["fields"] = {"value": 9999}
    other = append_review(
        state.project,
        ReviewRecord.model_validate(
            {k: v for k, v in other.items() if k in ReviewRecord.model_fields}
        ),
    )
    row = next(
        r
        for r in call("history", method="GET", view="attention")["reviews"]
        if r["id"] == other["id"]
    )
    assert any(
        reason["code"] == "regressed" and reason["source"] == "current_replay"
        for reason in row["attention_reasons"]
    )


def test_retest_is_read_only_and_keeps_context_seed_and_fresh_judgments(workbench):
    state, call = workbench
    old = source(state, context=True)
    before = review_path(state.project).read_bytes()
    result = call("review/{review_id}/retest", old["id"])
    assert review_path(state.project).read_bytes() == before
    assert result["current"]["sentence"] == old["sentence"]
    assert result["current"]["seed"] == old["seed"]
    assert list(result["current"]["context_before"]) == old["context_before"]
    assert list(result["current"]["context_after"]) == old["context_after"]
    assert result["draft"]["updates_review_id"] == old["id"]
    assert result["draft"]["verdict"] == "unclear"
    assert result["draft"]["interpretation_judgment"] == "not_reviewed"
    assert result["draft"]["defects"] == []


def test_fresh_evidence_does_not_close_issue_and_resolution_does_not_create_coverage(
    workbench,
):
    state, call = workbench
    old = source(state)
    before = review_path(state.project).read_bytes()
    assert (
        premise_review_evidence(state.project)["summary"]["validated_group_count"] == 0
    )
    # Resolution alone leaves the old deficient snapshot outside coverage.
    resolved = call(
        "review/{review_id}/resolve",
        old["id"],
        ReviewResolutionBody(note="Old issue closed."),
    )["review"]
    assert (
        premise_review_evidence(state.project)["summary"]["validated_group_count"] == 0
    )
    assert call("history", method="GET", view="attention")["total"] == 0
    # A resolved artefact can be rechecked and receive an independent update.
    retest = call("review/{review_id}/retest", resolved["id"])
    assert retest["validation_blockers"] == []
    fresh = call("review/{review_id}/evidence", resolved["id"], confirmation(retest))[
        "review"
    ]
    assert fresh["updates_review_id"] == resolved["id"]
    assert fresh["premise_evidence"]["deficiencies"] == []
    assert (
        premise_review_evidence(state.project)["summary"]["validated_group_count"] == 1
    )
    assert review_path(state.project).read_bytes().startswith(before)
    history = read_review_history(state.project)
    assert {r["review_status"] for r in history} == {"open", "resolved"}
    original = next(r for r in history if r["review_status"] == "resolved")
    assert original["note"] == old["note"]
    assert original["premise_evidence"] == old["premise_evidence"]

    second = source(state)
    retest = call("review/{review_id}/retest", second["id"])
    call("review/{review_id}/evidence", second["id"], confirmation(retest))
    assert second["id"] in {
        r["id"] for r in call("history", method="GET", view="attention")["reviews"]
    }


def test_resolving_clean_evidence_keeps_existing_validation(workbench):
    state, call = workbench
    old = source(state, deficient=False)
    assert (
        premise_review_evidence(state.project)["summary"]["validated_group_count"] == 1
    )
    call("review/{review_id}/resolve", old["id"], ReviewResolutionBody(note="Checked."))
    assert (
        premise_review_evidence(state.project)["summary"]["validated_group_count"] == 1
    )


def test_updated_coverage_does_not_hide_a_regressed_source_issue(workbench):
    state, call = workbench
    old = source(state, deficient=False)
    values = {k: v for k, v in old.items() if k in ReviewRecord.model_fields}
    values["naturalness"] = "preferred"
    values["premise_evidence"]["facts"][0]["fields"] = {"value": 9999}
    old = append_review(state.project, ReviewRecord.model_validate(values))
    retest = call("review/{review_id}/retest", old["id"])
    fresh = call("review/{review_id}/evidence", old["id"], confirmation(retest))[
        "review"
    ]
    assert fresh["updates_review_id"] == old["id"]
    assert (
        premise_review_evidence(state.project)["summary"]["validated_group_count"] == 1
    )
    attention = call("history", method="GET", view="attention")
    issue = next(row for row in attention["reviews"] if row["id"] == old["id"])
    assert any(reason["code"] == "regressed" for reason in issue["attention_reasons"])
    call(
        "review/{review_id}/resolve",
        old["id"],
        ReviewResolutionBody(note="Replaced by reviewed current evidence."),
    )
    assert old["id"] not in {
        row["id"] for row in call("history", method="GET", view="attention")["reviews"]
    }


def test_confirmations_reject_changed_registry_superseded_sources_and_tampering(
    workbench,
):
    state, call = workbench
    old = source(state)
    retest = call("review/{review_id}/retest", old["id"])
    with pytest.raises(HTTPException) as exc:
        call(
            "review/{review_id}/evidence",
            old["id"],
            confirmation(retest, retest_token="0" * 64),
        )
    assert exc.value.status_code == 409
    original_registry = state.project.registry
    state.project = replace(
        state.project,
        registry=replace(original_registry, fingerprint="changed-registry"),
    )
    with pytest.raises(HTTPException) as exc:
        call("review/{review_id}/evidence", old["id"], confirmation(retest))
    assert exc.value.status_code == 409
    state.project = replace(state.project, registry=original_registry)
    update_review(state.project, old["id"], "unclear", "A corrected human judgment")
    with pytest.raises(HTTPException) as exc:
        call("review/{review_id}/evidence", old["id"], confirmation(retest))
    assert exc.value.status_code == 404
    with pytest.raises(ValidationError):
        UpdatedEvidenceBody.model_validate(
            {**confirmation(retest).model_dump(), "facts": []}
        )


def test_explicit_judgments_required_and_machine_blockers_prevent_valid_updates(
    workbench,
):
    state, call = workbench
    old = source(state)
    # Keep the exact saved sentence but select an absent target.
    record = {k: v for k, v in old.items() if k in ReviewRecord.model_fields}
    record["target_rule"] = "invented/missing-target"
    missing = append_review(state.project, ReviewRecord.model_validate(record))
    retest = call("review/{review_id}/retest", missing["id"])
    assert retest["validation_blockers"]
    for body in (
        confirmation(retest),
        confirmation(retest, verdict="unclear", interpretation_judgment="not_reviewed"),
    ):
        with pytest.raises(HTTPException) as exc:
            call("review/{review_id}/evidence", missing["id"], body)
        assert exc.value.status_code == 409
    fresh = call(
        "review/{review_id}/evidence",
        missing["id"],
        confirmation(retest, verdict="invalid", result_judgment="incorrect"),
    )["review"]
    assert fresh["verdict"] == "invalid"
    assert (
        premise_review_evidence(state.project)["summary"]["validated_group_count"] == 0
    )


def test_resolution_rejects_excluded_duplicate_and_empty_actions(workbench):
    state, call = workbench
    old = source(state)
    with pytest.raises(HTTPException) as exc:
        call("review/{review_id}/resolve", old["id"], ReviewResolutionBody(note="  "))
    assert exc.value.status_code == 422
    marker = call(
        "review/{review_id}/resolve", old["id"], ReviewResolutionBody(note="Done")
    )["review"]
    with pytest.raises(HTTPException) as exc:
        call(
            "review/{review_id}/resolve",
            marker["id"],
            ReviewResolutionBody(note="Again"),
        )
    assert exc.value.status_code == 409
    delete_review(state.project, marker["id"])
    with pytest.raises(HTTPException) as exc:
        call("review/{review_id}/retest", marker["id"])
    assert exc.value.status_code == 404


def test_targetless_updates_never_claim_premise_coverage(workbench):
    state, call = workbench
    old = source(state, sentence=True)
    retest = call("review/{review_id}/retest", old["id"])
    fresh = call("review/{review_id}/evidence", old["id"], confirmation(retest))[
        "review"
    ]
    assert fresh["target_rule"] is None and fresh["review_kind"] == "sentence"
    assert premise_review_evidence(state.project)["summary"]["group_count"] == 0


def test_ask_retest_keeps_exact_scenario_and_reference_year(workbench):
    state, call = workbench
    text = (
        "The teacher was 7 years old in 2024. "
        "The child was 3 years old in 2025. How old are they now?"
    )
    traced = trace_project(state.project, TraceBody(text=text, reference_year=2028))
    assert traced["ask"]
    premises = traced["sentences"][:2]
    scenario = AskScenarioReviewEvidence(
        target_ask=traced["ask"]["id"],
        scenario_mode="answerable",
        question="How old are they now?",
        text=text,
        query=traced["ask"]["query"],
        premises=[p["text"] for p in premises],
        premise_rules=[p["machine_matches"][0]["rule_id"] for p in premises],
        consumer=traced["ask"]["query"].get("consumer"),
        reference_year=2028,
        answer=traced["answer"],
        answer_shape=traced["answer"]["kind"],
        minimal=True,
    )
    # A once-preferred snapshot with stale query values must not outrank the
    # freshly reviewed current query just because the new rating is unset.
    scenario.query = dict(scenario.query)
    scenario.query[next(iter(scenario.query))] = "outdated-reviewed-value"
    old = append_review(
        state.project,
        ReviewRecord(
            candidate_id="ask-invented",
            review_kind="ask",
            sentence=scenario.question,
            ask_scenario=scenario,
            seed=19,
            registry_fingerprint=state.registry.fingerprint,
            verdict="valid",
            naturalness="preferred",
        ),
    )
    retest = call("review/{review_id}/retest", old["id"])
    assert retest["current"]["text"] == text
    assert [row["value"] for row in retest["current"]["answer"]["value"]] == [11, 6]
    assert not retest["validation_blockers"]
    assert retest["draft"]["ask_scenario"]["minimal"] is False
    fresh = call(
        "review/{review_id}/evidence",
        old["id"],
        confirmation(retest, result_judgment="correct_answer"),
    )["review"]
    assert fresh["ask_scenario"]["reference_year"] == 2028
    assert fresh["ask_scenario"]["premise_review_ids"] == []
    assert ask_review_evidence(state.project)["summary"]["validated_group_count"] == 1


def test_ui_exposes_separate_retest_record_and_resolve_actions():
    script = Path("src/rulekit/server/static/app.js").read_text()
    assert "Attention reasons" in script
    assert "Retest saved example" in script
    assert "Record updated evidence" in script
    assert "Mark resolved" in script
    assert "Current evidence" in script and "Recorded evidence" in script
    assert "reference_year: candidate.reference_year ?? null" in script


@pytest.mark.parametrize("sentence,rule", [
    ("Two thirds of them are large.", "arithmetic/partition-attribute-fraction"),
    ("The sum of their ages was 28.", "arithmetic/group-total-sum-of-age"),
])
def test_context_only_premise_gaps_remain_visible_and_block_validated_coverage(
    workbench, sentence, rule
):
    state, call = workbench
    candidate = retest_candidate(
        state.project, sentence=sentence, rule_id=rule, seed=0, origin="reading",
    ).to_json()
    old = append_review(state.project, ReviewRecord(
        candidate_id=candidate["id"], origin="reading", sentence=sentence,
        target_rule=rule, seed=0, registry_fingerprint=state.registry.fingerprint,
        verdict="valid",
        premise_evidence=PremiseReviewEvidence(**{
            key: candidate[key] for key in (
                "target_status", "target_bindings", "actual_rule_ids",
                "facts", "collisions", "deficiencies",
            )
        }),
    ))
    before = review_path(state.project).read_bytes()
    retest = call("review/{review_id}/retest", old["id"])

    assert review_path(state.project).read_bytes() == before
    assert retest["current"]["grammar_deficiencies"] == ()
    context = retest["current"]["context_requirements"]
    assert len(context) == 1 and context[0]["need"] == "refers"
    assert retest["validation_blockers"] == list(candidate["deficiencies"])
    assert retest["draft"]["premise_evidence"]["deficiencies"] == list(candidate["deficiencies"])
    with pytest.raises(HTTPException) as exc:
        call("review/{review_id}/evidence", old["id"], confirmation(retest))
    assert exc.value.status_code == 409
    assert premise_review_evidence(state.project)["summary"]["validated_group_count"] == 0


@pytest.mark.parametrize("premises,expected", [
    ([], None),
    (["Dena owns 4 marbles.", "Fia owns 6 marbles."], 10),
])
def test_ask_context_diagnostics_follow_the_exact_saved_scenario(workbench, premises, expected):
    state, call = workbench
    question = "What is the total amount of marbles they own?"
    old = append_review(state.project, ReviewRecord(
        candidate_id="ask-context-invented", review_kind="ask", sentence=question,
        ask_scenario=AskScenarioReviewEvidence(
            target_ask="ask/what-total-combined", scenario_mode="ask_only",
            question=question, text=" ".join([*premises, question]),
            premises=premises, premise_rules=[""] * len(premises),
            minimal=False, answer_shape="decline",
        ),
        seed=0, registry_fingerprint=state.registry.fingerprint, verdict="valid",
    ))
    retest = call("review/{review_id}/retest", old["id"])

    assert retest["current"]["grammar_deficiencies"] == []
    context = retest["current"]["context_requirements"]
    assert len(context) == (1 if expected is None else 0)
    if context:
        assert context[0]["surface"] == "they" and context[0]["need"] == "refers"
        assert "needs a refers" in retest["current"]["deficiencies"][0]
    else:
        assert retest["current"]["deficiencies"] == []
    assert retest["current"]["answer"]["value"] == expected
    # Ask-only judgment boundaries still concern the query/result contract.
    assert retest["validation_blockers"] == []
