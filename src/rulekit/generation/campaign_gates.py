"""Machine-readable replay and durable promotion-gate evidence.

The gate compares canonical Designer trace projections and stores only central,
append-only results. Candidate code is executed by the isolated server layer;
this module owns schemas, normalization, diffs, and the fixed durable path.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..data.project import Project
from .campaign_reviews import (
    CampaignAnswerEvidence,
    CampaignAskEvidence,
    CampaignMatchEvidence,
    CampaignReviewError,
    CampaignTraceEvidence,
)
from .reviews import FactEvidence


TRACE_SECTIONS = (
    "matches",
    "facts",
    "collisions",
    "deficiencies",
    "ask",
    "answer",
    "proof",
)


def _without_source_refs(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _without_source_refs(item)
            for key, item in value.items()
            if key != "source_ref"
        }
    if isinstance(value, list):
        return [_without_source_refs(item) for item in value]
    return value


def campaign_trace_evidence(payload: dict[str, Any]) -> CampaignTraceEvidence:
    """Project one trace response onto the exact M4 comparison contract."""

    if payload.get("error"):
        raise CampaignReviewError(f"trace replay failed: {payload['error']}")
    matches = [
        CampaignMatchEvidence(
            sentence=int(sentence["index"]),
            **match,
        )
        for sentence in payload.get("sentences", [])
        for match in sentence.get("machine_matches", [])
    ]
    facts = [
        FactEvidence.model_validate(
            {
                key: fact[key]
                for key in ("type", "fields", "source", "sentence")
            }
        )
        for fact in payload.get("facts", [])
    ]
    answer = payload.get("answer") or {}
    clarification = _without_source_refs(answer.get("clarification"))
    answer_kind = str(answer.get("kind") or "decline")
    shape = "clarification" if clarification is not None else answer_kind
    ask = payload.get("ask")
    semantic = payload.get("semantic") or {}
    return CampaignTraceEvidence(
        matches=matches,
        facts=facts,
        collisions=sorted(
            (_without_source_refs(item) for item in payload.get("collisions", [])),
            key=lambda item: json.dumps(item, sort_keys=True),
        ),
        deficiencies=sorted(str(item) for item in payload.get("deficiencies", [])),
        ask=(
            CampaignAskEvidence(
                id=str(ask["id"]),
                query=_without_source_refs(ask.get("query")),
            )
            if ask is not None
            else None
        ),
        answer=CampaignAnswerEvidence(
            kind=answer_kind,
            shape=shape,
            value=_without_source_refs(answer.get("value")),
            reason=str(answer.get("reason") or ""),
            committed=bool(answer.get("committed", False)),
            clarification=clarification,
        ),
        proof=_without_source_refs(semantic.get("proof")),
    )


class CampaignEvidenceSectionDiff(BaseModel):
    """One exact trace section before and after candidate replay."""

    model_config = ConfigDict(extra="forbid")

    same: bool
    expected: Any
    actual: Any


def campaign_trace_diff(
    expected: CampaignTraceEvidence,
    actual: CampaignTraceEvidence,
) -> dict[str, CampaignEvidenceSectionDiff]:
    before = expected.model_dump()
    after = actual.model_dump()
    return {
        section: CampaignEvidenceSectionDiff(
            same=before[section] == after[section],
            expected=before[section],
            actual=after[section],
        )
        for section in TRACE_SECTIONS
    }


class CampaignSpecimenReplay(BaseModel):
    model_config = ConfigDict(extra="forbid")

    specimen_id: str = Field(min_length=1, max_length=64)
    passed: bool
    changed_sections: list[str] = Field(default_factory=list, max_length=16)
    actual: CampaignTraceEvidence | None = None
    diff: dict[str, CampaignEvidenceSectionDiff] = Field(
        default_factory=dict,
        max_length=16,
    )
    error: str | None = Field(default=None, max_length=4000)


class CampaignReviewReplay(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str = Field(min_length=1, max_length=128)
    scope: Literal["explicit", "target_rule"]
    verdict: str = Field(min_length=1, max_length=32)
    target_rule: str | None = Field(default=None, max_length=256)
    target_present: bool | None = None
    replayed: bool
    actual: CampaignTraceEvidence | None = None
    error: str | None = Field(default=None, max_length=4000)


class CampaignStandingGateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=128)
    kind: Literal["answer", "projection", "synthetic", "lint", "firewall"]
    passed: bool
    baseline_fingerprint: str | None = Field(default=None, max_length=128)
    candidate_fingerprint: str | None = Field(default=None, max_length=128)
    item_ids_digest: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    baseline: dict[str, Any] | None = None
    candidate: dict[str, Any] | None = None
    diff: dict[str, Any] | None = None
    detail: str = Field(default="", max_length=8000)


class CampaignPromotionGate(BaseModel):
    """One complete M4 result before central publication metadata."""

    model_config = ConfigDict(extra="forbid")

    format: Literal["rulekit/campaign-gate@1"] = "rulekit/campaign-gate@1"
    candidate_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    candidate_commit: str = Field(pattern=r"^[0-9a-f]{7,64}$")
    registry_fingerprint: str = Field(min_length=8, max_length=128)
    baseline_commit: str = Field(pattern=r"^[0-9a-f]{7,64}$")
    passed: bool
    specimens: list[CampaignSpecimenReplay] = Field(max_length=16)
    reviews: list[CampaignReviewReplay] = Field(max_length=256)
    standing: list[CampaignStandingGateResult] = Field(max_length=32)

    @model_validator(mode="after")
    def _pass_matches_every_component(self) -> "CampaignPromotionGate":
        components_pass = (
            all(item.passed for item in self.specimens)
            and all(item.replayed for item in self.reviews)
            and all(item.passed for item in self.standing)
        )
        if self.passed != components_pass:
            raise ValueError("promotion-gate pass must match every component")
        if len(json.dumps(self.model_dump(), sort_keys=True)) > 8_000_000:
            raise ValueError("promotion-gate evidence exceeds 8000000 characters")
        return self


class DurableCampaignPromotionGate(CampaignPromotionGate):
    id: str = Field(pattern=r"^campaign-gate-[0-9a-f]{16}$")
    project: str = Field(min_length=1, max_length=256)
    timestamp: str = Field(min_length=20, max_length=64)


def campaign_gate_path(project: Project) -> Path:
    return project.root / "generation" / "campaign" / "gates.jsonl"


def append_campaign_gate(
    project: Project,
    gate: CampaignPromotionGate,
) -> dict[str, Any]:
    durable = DurableCampaignPromotionGate(
        **gate.model_dump(),
        id="campaign-gate-" + uuid.uuid4().hex[:16],
        project=project.doc.name,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    path = campaign_gate_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(durable.model_dump(), sort_keys=True) + "\n")
    return durable.model_dump()


def read_campaign_gates(project: Project) -> list[dict[str, Any]]:
    path = campaign_gate_path(project)
    if not path.exists():
        return []
    rows = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            row = DurableCampaignPromotionGate.model_validate_json(line)
        except ValueError as exc:
            raise CampaignReviewError(
                f"invalid campaign gate at line {line_number}: {exc}"
            ) from exc
        rows.append(row.model_dump())
    return rows


def latest_campaign_gate(
    project: Project,
    candidate_id: str,
    candidate_commit: str,
    registry_fingerprint: str,
) -> dict[str, Any] | None:
    exact = [
        row
        for row in read_campaign_gates(project)
        if row["candidate_id"] == candidate_id
        and row["candidate_commit"] == candidate_commit
        and row["registry_fingerprint"] == registry_fingerprint
    ]
    return exact[-1] if exact else None
