"""GSM8K Mining v2 promotion reviews are durable and fingerprint-pinned."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from rulekit.generation import (
    CampaignAnswerEvidence,
    CampaignCandidateManifest,
    CampaignClassEvidence,
    CampaignConstitutionEvidence,
    CampaignGenerationContract,
    CampaignImplementationContract,
    CampaignReviewDecision,
    CampaignReviewError,
    CampaignRetestRequest,
    CampaignSpecimen,
    CampaignSpecimenReview,
    append_campaign_review,
    campaign_manifest_root,
    campaign_review_path,
    campaign_review_queue,
    publish_campaign_manifest,
    read_campaign_manifests,
    read_campaign_review_records,
)
from rulekit.generation.reviews import SourceLocation
from rulekit.server.api import ServerState, build_router


def _project(tmp_path: Path, fingerprint: str = "registry-abcdef0123456789"):
    return SimpleNamespace(
        root=tmp_path,
        doc=SimpleNamespace(name="invented-campaign"),
        registry=SimpleNamespace(fingerprint=fingerprint),
    )


def _specimens() -> list[CampaignSpecimen]:
    return [
        CampaignSpecimen(
            id="strict-positive",
            kind="strict_positive",
            title="Ordinary positive",
            sentence="The keeper had 4 lanterns.",
            target_rule="invented/holding",
            source_ref=SourceLocation(
                path="/candidate/packs/invented/rules.yaml",
                line=12,
                column=3,
                kind="rule",
                label="invented/holding",
            ),
            retest=CampaignRetestRequest(
                rule_id="invented/holding",
                seed=42,
                requested_bindings={"holder": "keeper"},
                attempts=1,
            ),
            expectation="The premise matches and retains the keeper and lantern count.",
            actual_rule_ids=["invented/holding"],
        ),
        CampaignSpecimen(
            id="answerable-scenario",
            kind="answerable",
            title="Complete question",
            sentence="The keeper had 4 lanterns. How many lanterns did the keeper have?",
            target_rule="ask/invented-holder",
            expectation="The complete scenario answers 4.",
            actual_rule_ids=["invented/holding"],
            answer=CampaignAnswerEvidence(
                kind="number",
                value=4,
                reason="one exact holder quantity",
            ),
        ),
    ]


def _manifest(
    *,
    commit: str = "abcdef1",
    fingerprint: str = "registry-abcdef0123456789",
    mechanism: str = "One declared holding premise and exact-holder ask.",
) -> CampaignCandidateManifest:
    return CampaignCandidateManifest(
        candidate_id="holder-question",
        class_name="Exact holder quantity questions",
        branch="mining/cand-holder-question",
        commit=commit,
        registry_fingerprint=fingerprint,
        mechanism=mechanism,
        class_evidence=CampaignClassEvidence(
            pool_frequency=4,
            expected_solved=2,
            walked_item_ids=["dev-invented-1", "dev-invented-2"],
            premise_mechanism="A declared holding premise emits one quantity.",
            ask_mechanism="An exact-holder ask selects that quantity.",
            structural_summary=[
                "Two independently inspected DEV items share the holder/quantity class."
            ],
        ),
        generation_contract=CampaignGenerationContract(
            premise_rules=["invented/holding"],
            ask_rules=["ask/invented-holder"],
            required_specimen_kinds=["strict_positive", "answerable"],
        ),
        implementation_contract=CampaignImplementationContract(
            files_expected=[
                "packs/invented/rules.yaml",
                "tests/test_mining_holder_question.py",
            ],
            synthetic_tests=["tests/test_mining_holder_question.py"],
            class_justification="The same holder/quantity relation covers multiple items.",
        ),
        constitution_review=CampaignConstitutionEvidence(
            verdict="pass",
            notes="Synthetic fixture passed the constitution review.",
        ),
        risks=["A holder must not answer from another entity's quantity."],
        specimens=_specimens(),
    )


def _decision(
    manifest: CampaignCandidateManifest,
    *,
    verdict: str = "approved",
    specimen_verdicts: tuple[str, ...] = ("valid", "valid"),
) -> CampaignReviewDecision:
    return CampaignReviewDecision(
        candidate_id=manifest.candidate_id,
        candidate_commit=manifest.commit,
        registry_fingerprint=manifest.registry_fingerprint,
        verdict=verdict,
        specimens=[
            CampaignSpecimenReview(
                specimen_id=specimen.id,
                verdict=specimen_verdict,
            )
            for specimen, specimen_verdict in zip(
                manifest.specimens,
                specimen_verdicts,
                strict=True,
            )
        ],
        note="Reviewed in the Designer.",
    )


def test_campaign_manifest_uses_one_fixed_immutable_path(tmp_path: Path) -> None:
    project = _project(tmp_path)
    manifest = _manifest()

    first = publish_campaign_manifest(project, manifest)
    repeated = publish_campaign_manifest(project, manifest)

    assert repeated == first
    assert read_campaign_manifests(project) == [first]
    assert campaign_manifest_root(project) == (
        tmp_path / "generation" / "campaign" / "candidates"
    )
    assert (
        campaign_manifest_root(project)
        / manifest.candidate_id
        / f"{manifest.commit}.json"
    ).exists()
    with pytest.raises(CampaignReviewError, match="immutable"):
        publish_campaign_manifest(
            project,
            _manifest(mechanism="Different content cannot replace the same commit."),
        )
    with pytest.raises(ValidationError):
        CampaignCandidateManifest.model_validate(
            {**manifest.model_dump(), "path": "/tmp/not-allowed.json"}
        )


def test_campaign_publication_requires_constitution_pass(tmp_path: Path) -> None:
    project = _project(tmp_path)
    manifest = _manifest().model_copy(update={"constitution_review": None})

    with pytest.raises(CampaignReviewError, match="constitution review"):
        publish_campaign_manifest(project, manifest)


def test_manifest_generation_contract_requires_its_declared_specimen_kind() -> None:
    manifest = _manifest()
    payload = manifest.model_dump()
    payload["generation_contract"]["required_specimen_kinds"].append("decline")

    with pytest.raises(ValidationError, match="lacks required specimen kinds"):
        CampaignCandidateManifest.model_validate(payload)


def test_approval_requires_every_specimen_to_be_valid(tmp_path: Path) -> None:
    project = _project(tmp_path)
    manifest = _manifest()
    publish_campaign_manifest(project, manifest)

    incomplete = _decision(manifest).model_copy(
        update={"specimens": [_decision(manifest).specimens[0]]}
    )
    with pytest.raises(CampaignReviewError, match="requires every specimen"):
        append_campaign_review(project, incomplete)

    with pytest.raises(CampaignReviewError, match="marked valid"):
        append_campaign_review(
            project,
            _decision(
                manifest,
                specimen_verdicts=("valid", "unclear"),
            ),
        )

    approved = append_campaign_review(project, _decision(manifest))

    assert campaign_review_path(project) == (
        tmp_path / "generation" / "campaign" / "reviews.jsonl"
    )
    assert read_campaign_review_records(project) == [approved]
    queue = campaign_review_queue(project)
    assert queue[0]["status"] == "approved"
    assert queue[0]["latest_review"] == approved
    assert queue[0]["runtime_available"] is True


def test_repeated_identical_decision_is_idempotent(tmp_path: Path) -> None:
    project = _project(tmp_path)
    manifest = _manifest()
    publish_campaign_manifest(project, manifest)
    decision = _decision(manifest)

    first = append_campaign_review(project, decision)
    repeated = append_campaign_review(project, decision)

    assert repeated == first
    assert read_campaign_review_records(project) == [first]

    revised = append_campaign_review(
        project,
        decision.model_copy(update={"note": "A materially revised rationale."}),
    )
    assert revised["id"] != first["id"]
    assert read_campaign_review_records(project) == [first, revised]


def test_decisions_encode_the_requested_boundary(tmp_path: Path) -> None:
    project = _project(tmp_path)
    manifest = _manifest()
    publish_campaign_manifest(project, manifest)

    with pytest.raises(CampaignReviewError, match="at least one invalid"):
        append_campaign_review(
            project,
            _decision(manifest, verdict="changes_requested"),
        )
    with pytest.raises(CampaignReviewError, match="at least one unclear"):
        append_campaign_review(
            project,
            _decision(manifest, verdict="unclear"),
        )

    changed = append_campaign_review(
        project,
        _decision(
            manifest,
            verdict="changes_requested",
            specimen_verdicts=("valid", "invalid"),
        ),
    )
    assert changed["verdict"] == "changes_requested"


def test_new_candidate_revision_makes_prior_approval_stale(tmp_path: Path) -> None:
    project = _project(tmp_path)
    first = _manifest()
    publish_campaign_manifest(project, first)
    append_campaign_review(project, _decision(first))

    revised = _manifest(
        commit="bcdefa2",
        fingerprint="registry-bcdefa2345678901",
    )
    publish_campaign_manifest(project, revised)

    queue = campaign_review_queue(project)
    assert queue[0]["manifest"]["commit"] == revised.commit
    assert queue[0]["status"] == "awaiting_review"
    assert queue[0]["latest_review"] is None
    assert queue[0]["stale_review_count"] == 1
    assert queue[0]["runtime_available"] is False
    with pytest.raises(CampaignReviewError, match="commit changed"):
        append_campaign_review(project, _decision(first))


def test_designer_exposes_the_campaign_promotion_queue() -> None:
    root = Path("src/rulekit/server/static")
    html = (root / "index.html").read_text()
    js = (root / "app.js").read_text()
    css = (root / "style.css").read_text()

    assert 'id="view-campaign"' in html
    assert 'id="campaign"' in html
    assert '"GET", "/api/campaign/reviews"' in js
    assert "Record promotion decision" in js
    assert "Decision recorded" in js
    assert "decisionMatchesPrevious" in js
    assert "isolated runner required" in js
    assert "campaign-mode" in css
    assert "Run exact gate" in js
    assert "Machine promotion gate" in js

    router = build_router(ServerState(Path("projects/curated")))
    paths = {route.path for route in router.routes}
    assert "/api/campaign/reviews" in paths
    assert "/api/campaign/reviews/candidate" in paths
    assert "/api/campaign/reviews/{candidate_id}" in paths
    assert "/api/campaign/gates/{candidate_id}" in paths
