"""Durable staging-landings for reviewed Mining v2 candidates.

Human approval and the exact machine gate make a candidate eligible for
integration.  A landing record closes that lifecycle after the sequential
integrator has committed the candidate to the batch staging branch.  Keeping
this evidence in the central project prevents a resumed orchestrator from
landing the same exact revision twice.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..data.project import Project
from .campaign_gates import latest_campaign_gate
from .campaign_reviews import (
    CampaignReviewError,
    read_campaign_manifests,
    read_campaign_review_records,
)


class CampaignLanding(BaseModel):
    """One exact candidate revision committed to a batch staging branch."""

    model_config = ConfigDict(extra="forbid")

    format: Literal["rulekit/campaign-landing@1"] = (
        "rulekit/campaign-landing@1"
    )
    candidate_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    candidate_commit: str = Field(pattern=r"^[0-9a-f]{7,64}$")
    registry_fingerprint: str = Field(min_length=8, max_length=128)
    review_id: str = Field(pattern=r"^campaign-review-[0-9a-f]{16}$")
    gate_id: str = Field(pattern=r"^campaign-gate-[0-9a-f]{16}$")
    staging_branch: str = Field(min_length=1, max_length=256)
    staging_commit: str = Field(pattern=r"^[0-9a-f]{7,64}$")
    increment: int = Field(ge=1)
    summary: str = Field(min_length=1, max_length=4000)

    @field_validator("staging_branch")
    @classmethod
    def _staging_branch_is_a_batch_branch(cls, value: str) -> str:
        if not value.startswith("mining/batch-") or any(
            char.isspace() for char in value
        ):
            raise ValueError("staging branch must be a mining/batch-* branch")
        return value


class DurableCampaignLanding(CampaignLanding):
    """A landing after the central project attaches durable metadata."""

    id: str = Field(pattern=r"^campaign-landing-[0-9a-f]{16}$")
    project: str = Field(min_length=1, max_length=256)
    timestamp: str = Field(min_length=20, max_length=64)


def campaign_landing_path(project: Project) -> Path:
    """The fixed central landing ledger; staging worktrees never own it."""

    return project.root / "generation" / "campaign" / "landings.jsonl"


def read_campaign_landings(project: Project) -> list[dict[str, Any]]:
    """Read the complete append-only landing ledger in write order."""

    path = campaign_landing_path(project)
    if not path.exists():
        return []
    records = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            record = DurableCampaignLanding.model_validate_json(line)
        except ValueError as exc:
            raise CampaignReviewError(
                f"invalid campaign landing at line {line_number}: {exc}"
            ) from exc
        records.append(record.model_dump())
    return records


def latest_campaign_landing(
    project: Project,
    candidate_id: str,
    candidate_commit: str,
    registry_fingerprint: str,
) -> dict[str, Any] | None:
    """Return the last landing for one exact candidate revision, if any."""

    exact = [
        row
        for row in read_campaign_landings(project)
        if row["candidate_id"] == candidate_id
        and row["candidate_commit"] == candidate_commit
        and row["registry_fingerprint"] == registry_fingerprint
    ]
    return exact[-1] if exact else None


def append_campaign_landing(
    project: Project,
    landing: CampaignLanding,
) -> dict[str, Any]:
    """Append one landing after revalidating its exact approval and gate."""

    latest_manifests: dict[str, dict[str, Any]] = {}
    for manifest in read_campaign_manifests(project):
        latest_manifests[manifest["candidate_id"]] = manifest
    manifest = latest_manifests.get(landing.candidate_id)
    if manifest is None:
        raise CampaignReviewError(
            f"no campaign candidate {landing.candidate_id!r} can be landed"
        )
    if landing.candidate_commit != manifest["commit"]:
        raise CampaignReviewError(
            "candidate commit changed; reload the campaign review queue"
        )
    if landing.registry_fingerprint != manifest["registry_fingerprint"]:
        raise CampaignReviewError(
            "candidate registry fingerprint changed; reload the campaign review queue"
        )

    exact_reviews = [
        review
        for review in read_campaign_review_records(project)
        if review["candidate_id"] == landing.candidate_id
        and review["candidate_commit"] == landing.candidate_commit
        and review["registry_fingerprint"] == landing.registry_fingerprint
    ]
    latest_review = exact_reviews[-1] if exact_reviews else None
    if latest_review is None or latest_review["verdict"] != "approved":
        raise CampaignReviewError(
            "campaign landing requires the latest exact human decision to be approved"
        )
    if landing.review_id != latest_review["id"]:
        raise CampaignReviewError(
            "campaign landing must pin the latest exact human review id"
        )

    gate = latest_campaign_gate(
        project,
        landing.candidate_id,
        landing.candidate_commit,
        landing.registry_fingerprint,
    )
    if gate is None or not gate["passed"]:
        raise CampaignReviewError(
            "campaign landing requires a passing exact machine gate"
        )
    if landing.gate_id != gate["id"]:
        raise CampaignReviewError(
            "campaign landing must pin the latest exact machine gate id"
        )

    records = read_campaign_landings(project)
    exact = [
        row
        for row in records
        if row["candidate_id"] == landing.candidate_id
        and row["candidate_commit"] == landing.candidate_commit
        and row["registry_fingerprint"] == landing.registry_fingerprint
    ]
    if exact:
        previous = exact[-1]
        previous_payload = {
            key: value
            for key, value in previous.items()
            if key not in {"id", "project", "timestamp"}
        }
        if previous_payload == landing.model_dump():
            return previous
        raise CampaignReviewError(
            "this exact campaign candidate revision is already landed"
        )

    for record in records:
        same_branch = record["staging_branch"] == landing.staging_branch
        if same_branch and record["increment"] == landing.increment:
            raise CampaignReviewError(
                "campaign staging increment is already assigned on this branch"
            )
        if same_branch and record["staging_commit"] == landing.staging_commit:
            raise CampaignReviewError(
                "campaign staging commit is already assigned on this branch"
            )

    durable = DurableCampaignLanding(
        **landing.model_dump(),
        id="campaign-landing-" + uuid.uuid4().hex[:16],
        project=project.doc.name,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    path = campaign_landing_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(durable.model_dump(), sort_keys=True) + "\n")
    return durable.model_dump()
