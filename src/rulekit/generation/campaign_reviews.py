"""Durable promotion-review evidence for isolated mining candidates.

Candidate manifests are immutable files keyed by candidate id and commit.
Human decisions append to one central project-local ledger. Candidate
worktrees can therefore disappear without losing the judgment, while a new
commit or registry fingerprint mechanically invalidates an older approval.

This module is Designer-only. The runtime kernel never imports campaign
manifests or human decisions.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..data.project import Project
from .candidate import GenerationMode, LexicalRelaxation
from .reviews import FactEvidence, SourceLocation


class CampaignReviewError(ValueError):
    """A manifest or human decision violates the durable queue contract."""


SpecimenKind = Literal[
    "strict_positive",
    "boundary_probe",
    "answerable",
    "decline",
]
SpecimenVerdict = Literal["valid", "invalid", "unclear"]
CandidateVerdict = Literal["approved", "changes_requested", "unclear"]
CampaignDefectKind = Literal[
    "premise",
    "fact",
    "ask_binding",
    "inference",
    "answer_shape",
    "group_completeness",
    "reference_context",
    "clarification",
    "proof",
    "generation",
    "other",
]


class CampaignVocabularyEvidence(BaseModel):
    """One explicitly bounded lexical admission considered by a candidate."""

    model_config = ConfigDict(extra="forbid")

    surface: str = Field(min_length=1, max_length=128)
    bound_by: str = Field(min_length=1, max_length=1000)
    quarantine: Literal["clear", "not_applicable"]
    collision_risk: str = Field(min_length=1, max_length=1000)


class CampaignClassEvidence(BaseModel):
    """Inspectable DEV evidence for the named class, never benchmark prose."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["coverage", "smoke"] = "coverage"
    pool_frequency: int = Field(ge=0)
    expected_solved: int = Field(ge=0)
    walked_item_ids: list[str] = Field(default_factory=list, max_length=64)
    premise_mechanism: str = Field(min_length=1, max_length=4000)
    ask_mechanism: str = Field(min_length=1, max_length=4000)
    structural_summary: list[str] = Field(min_length=1, max_length=32)
    vocabulary: list[CampaignVocabularyEvidence] = Field(
        default_factory=list,
        max_length=32,
    )

    @field_validator("walked_item_ids")
    @classmethod
    def _walked_ids_are_bounded(cls, values: list[str]) -> list[str]:
        if any(not value or len(value) > 256 for value in values):
            raise ValueError("walked DEV item ids must be non-empty and bounded")
        return values

    @field_validator("structural_summary")
    @classmethod
    def _structural_summaries_are_bounded(cls, values: list[str]) -> list[str]:
        if any(not value or len(value) > 2000 for value in values):
            raise ValueError("structural summaries must be non-empty and bounded")
        return values

    @model_validator(mode="after")
    def _coverage_claim_has_auditable_yield(self) -> "CampaignClassEvidence":
        if len(set(self.walked_item_ids)) != len(self.walked_item_ids):
            raise ValueError("walked DEV item ids must be unique")
        if self.mode == "coverage":
            if not self.walked_item_ids:
                raise ValueError("coverage evidence requires walked DEV item ids")
            if self.expected_solved < 1:
                raise ValueError("coverage evidence must expect at least one solve")
            if self.expected_solved > self.pool_frequency:
                raise ValueError("expected solved cannot exceed the measured pool")
        elif self.expected_solved != 0:
            raise ValueError("a smoke candidate cannot claim solved items")
        return self


class CampaignGenerationContract(BaseModel):
    """The generated surfaces a human must inspect before promotion."""

    model_config = ConfigDict(extra="forbid")

    premise_rules: list[str] = Field(default_factory=list, max_length=64)
    ask_rules: list[str] = Field(default_factory=list, max_length=64)
    required_specimen_kinds: list[SpecimenKind] = Field(
        min_length=1,
        max_length=4,
    )

    @model_validator(mode="after")
    def _targets_and_kinds_are_unique(self) -> "CampaignGenerationContract":
        for label, values in (
            ("premise rule", self.premise_rules),
            ("ask rule", self.ask_rules),
            ("specimen kind", self.required_specimen_kinds),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"campaign {label}s must be unique")
        if not self.premise_rules and not self.ask_rules:
            raise ValueError("generation contract requires a premise or ask target")
        return self

    @field_validator("premise_rules", "ask_rules")
    @classmethod
    def _rule_ids_are_bounded(cls, values: list[str]) -> list[str]:
        if any(not value or len(value) > 256 for value in values):
            raise ValueError("campaign generation rule ids must be bounded")
        return values


class CampaignImplementationContract(BaseModel):
    """Auditable expected scope and synthetic proof for constitution review."""

    model_config = ConfigDict(extra="forbid")

    files_expected: list[str] = Field(min_length=1, max_length=64)
    synthetic_tests: list[str] = Field(min_length=1, max_length=16)
    class_justification: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def _paths_are_unique_and_relative(self) -> "CampaignImplementationContract":
        for label, values in (
            ("expected file", self.files_expected),
            ("synthetic test", self.synthetic_tests),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"campaign {label}s must be unique")
            if any(
                value.startswith("/") or ".." in Path(value).parts
                for value in values
            ):
                raise ValueError(f"campaign {label}s must be repository-relative")
        if any(not value.startswith("tests/") for value in self.synthetic_tests):
            raise ValueError("campaign synthetic tests must live under tests/")
        return self

    @field_validator("files_expected", "synthetic_tests")
    @classmethod
    def _paths_are_bounded(cls, values: list[str]) -> list[str]:
        if any(not value or len(value) > 1000 for value in values):
            raise ValueError("campaign implementation paths must be bounded")
        return values


class CampaignConstitutionViolation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule: str = Field(min_length=1, max_length=128)
    file: str | None = Field(default=None, max_length=1000)
    detail: str = Field(min_length=1, max_length=4000)


class CampaignConstitutionEvidence(BaseModel):
    """Read-only reviewer verdict attached before central publication."""

    model_config = ConfigDict(extra="forbid")

    verdict: Literal["pass", "fail"]
    violations: list[CampaignConstitutionViolation] = Field(
        default_factory=list,
        max_length=32,
    )
    notes: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def _verdict_matches_violations(self) -> "CampaignConstitutionEvidence":
        if self.verdict == "pass" and self.violations:
            raise ValueError("a passing constitution review cannot list violations")
        if self.verdict == "fail" and not self.violations:
            raise ValueError("a failed constitution review requires a violation")
        return self


class CampaignAnswerEvidence(BaseModel):
    """The bounded answer snapshot displayed without executing candidate code."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(min_length=1, max_length=128)
    shape: str | None = Field(default=None, min_length=1, max_length=128)
    value: Any = None
    reason: str = Field(default="", max_length=4000)
    committed: bool | None = None
    clarification: dict[str, Any] | None = None

    @field_validator("value")
    @classmethod
    def _value_is_bounded_json(cls, value: Any) -> Any:
        try:
            rendered = json.dumps(value, sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise ValueError("answer evidence must be JSON-serializable") from exc
        if len(rendered) > 8000:
            raise ValueError("answer evidence exceeds 8000 serialized characters")
        return value

    @field_validator("clarification")
    @classmethod
    def _clarification_is_bounded_json(
        cls, value: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if value is None:
            return None
        rendered = json.dumps(value, sort_keys=True)
        if len(rendered) > 16000:
            raise ValueError(
                "clarification evidence exceeds 16000 serialized characters"
            )
        return value


class CampaignMatchEvidence(BaseModel):
    """One exact ordinary matcher result in a scenario replay."""

    model_config = ConfigDict(extra="forbid")

    sentence: int = Field(ge=0)
    rule_id: str = Field(min_length=1, max_length=256)
    bindings: dict[str, str] = Field(default_factory=dict, max_length=64)
    consumed: list[int] = Field(default_factory=list, max_length=256)
    shadowed: bool = False


class CampaignAskEvidence(BaseModel):
    """The winning ask rule and its normalized public query."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=256)
    query: dict[str, Any] | None = None


class CampaignTraceEvidence(BaseModel):
    """Canonical mechanical evidence compared by the M4 promotion gate."""

    model_config = ConfigDict(extra="forbid")

    matches: list[CampaignMatchEvidence] = Field(
        default_factory=list,
        max_length=128,
    )
    facts: list[FactEvidence] = Field(default_factory=list, max_length=128)
    collisions: list[dict[str, Any]] = Field(default_factory=list, max_length=64)
    deficiencies: list[str] = Field(default_factory=list, max_length=128)
    ask: CampaignAskEvidence | None = None
    answer: CampaignAnswerEvidence
    proof: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _evidence_is_bounded_json(self) -> "CampaignTraceEvidence":
        rendered = json.dumps(self.model_dump(), sort_keys=True)
        if len(rendered) > 128_000:
            raise ValueError(
                "campaign trace evidence exceeds 128000 serialized characters"
            )
        return self


class CampaignRetestRequest(BaseModel):
    """A bounded recipe for replaying one specimen in its candidate runtime.

    The sentence lives on :class:`CampaignSpecimen`, so it cannot disagree
    with the text the human is reviewing. The remaining fields are exactly
    the deterministic inputs accepted by the ordinary generation retest API.
    """

    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(min_length=1, max_length=256)
    seed: int
    requested_bindings: dict[str, str] = Field(default_factory=dict, max_length=64)
    attempts: int = Field(default=1, ge=1, le=64)
    origin: Literal["generated", "reading"] = "generated"
    generation_mode: GenerationMode = "strict"
    lexical_relaxations: list[LexicalRelaxation] = Field(
        default_factory=list,
        max_length=16,
    )


class CampaignSpecimen(BaseModel):
    """One reviewable positive, boundary, answerable, or decline example."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,63}$")
    kind: SpecimenKind
    title: str = Field(min_length=1, max_length=256)
    sentence: str = Field(min_length=1, max_length=4000)
    interpretation: str | None = Field(default=None, max_length=4000)
    reference_year: int | None = Field(default=None, ge=1, le=9999)
    target_rule: str | None = Field(default=None, min_length=1, max_length=256)
    source_ref: SourceLocation | None = None
    retest: CampaignRetestRequest | None = None
    expectation: str = Field(min_length=1, max_length=4000)
    actual_rule_ids: list[str] = Field(default_factory=list, max_length=64)
    facts: list[FactEvidence] = Field(default_factory=list, max_length=64)
    answer: CampaignAnswerEvidence | None = None
    deficiencies: list[str] = Field(default_factory=list, max_length=64)
    trace: CampaignTraceEvidence | None = None

    @field_validator("actual_rule_ids")
    @classmethod
    def _rule_ids_are_unique(cls, values: list[str]) -> list[str]:
        if any(not value or len(value) > 256 for value in values):
            raise ValueError("actual rule ids must be non-empty and bounded")
        if len(set(values)) != len(values):
            raise ValueError("actual rule ids must be unique")
        return values

    @field_validator("deficiencies")
    @classmethod
    def _deficiencies_are_bounded(cls, values: list[str]) -> list[str]:
        if any(not value or len(value) > 2000 for value in values):
            raise ValueError("deficiencies must be non-empty and bounded")
        return values


class CampaignCandidateManifest(BaseModel):
    """An immutable candidate review bundle published by the orchestrator."""

    model_config = ConfigDict(extra="forbid")

    format: Literal["rulekit/campaign-review@2"] = "rulekit/campaign-review@2"
    candidate_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    class_name: str = Field(min_length=1, max_length=512)
    branch: str = Field(min_length=1, max_length=256)
    commit: str = Field(pattern=r"^[0-9a-f]{7,64}$")
    registry_fingerprint: str = Field(min_length=8, max_length=128)
    mechanism: str = Field(min_length=1, max_length=4000)
    class_evidence: CampaignClassEvidence
    generation_contract: CampaignGenerationContract
    implementation_contract: CampaignImplementationContract
    constitution_review: CampaignConstitutionEvidence | None = None
    risks: list[str] = Field(default_factory=list, max_length=32)
    review_ids: list[str] = Field(default_factory=list, max_length=128)
    specimens: list[CampaignSpecimen] = Field(min_length=1, max_length=16)

    @field_validator("branch")
    @classmethod
    def _branch_is_display_only_but_bounded(cls, value: str) -> str:
        if any(char.isspace() for char in value):
            raise ValueError("branch cannot contain whitespace")
        return value

    @field_validator("risks")
    @classmethod
    def _risks_are_bounded(cls, values: list[str]) -> list[str]:
        if any(not value or len(value) > 2000 for value in values):
            raise ValueError("risks must be non-empty and bounded")
        return values

    @field_validator("review_ids")
    @classmethod
    def _review_ids_are_unique_and_bounded(cls, values: list[str]) -> list[str]:
        if any(
            not value.startswith("rev-") or len(value) > 128
            for value in values
        ):
            raise ValueError("campaign review ids must be bounded review identities")
        if len(set(values)) != len(values):
            raise ValueError("campaign review ids must be unique")
        return values

    @model_validator(mode="after")
    def _specimen_ids_are_unique(self) -> "CampaignCandidateManifest":
        ids = [specimen.id for specimen in self.specimens]
        if len(ids) != len(set(ids)):
            raise ValueError("campaign specimen ids must be unique")
        present = {specimen.kind for specimen in self.specimens}
        required = set(self.generation_contract.required_specimen_kinds)
        if missing := required - present:
            raise ValueError(
                "campaign manifest lacks required specimen kinds: "
                + ", ".join(sorted(missing))
            )
        return self


class DurableCampaignCandidateManifest(CampaignCandidateManifest):
    """A manifest after the central project attaches publication metadata."""

    project: str = Field(min_length=1, max_length=256)
    published_at: str = Field(min_length=20, max_length=64)


class CampaignSpecimenReview(BaseModel):
    """One human judgment attached to one immutable specimen."""

    model_config = ConfigDict(extra="forbid")

    specimen_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,63}$")
    verdict: SpecimenVerdict
    defects: list[CampaignDefectKind] = Field(default_factory=list, max_length=16)
    note: str = Field(default="", max_length=4000)


class CampaignReviewDecision(BaseModel):
    """A candidate-level promotion decision pinned to exact code and data."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    candidate_commit: str = Field(pattern=r"^[0-9a-f]{7,64}$")
    registry_fingerprint: str = Field(min_length=8, max_length=128)
    verdict: CandidateVerdict
    specimens: list[CampaignSpecimenReview] = Field(min_length=1, max_length=16)
    note: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def _specimen_reviews_are_unique(self) -> "CampaignReviewDecision":
        ids = [specimen.specimen_id for specimen in self.specimens]
        if len(ids) != len(set(ids)):
            raise ValueError("campaign specimen reviews must be unique")
        return self


class DurableCampaignReviewDecision(CampaignReviewDecision):
    """An append-only decision after the central project attaches identity."""

    id: str = Field(pattern=r"^campaign-review-[0-9a-f]{16}$")
    project: str = Field(min_length=1, max_length=256)
    timestamp: str = Field(min_length=20, max_length=64)


def campaign_manifest_root(project: Project) -> Path:
    """The fixed candidate-manifest directory; callers cannot redirect it."""

    return project.root / "generation" / "campaign" / "candidates"


def campaign_review_path(project: Project) -> Path:
    """The fixed central decision ledger; candidate worktrees never own it."""

    return project.root / "generation" / "campaign" / "reviews.jsonl"


def _manifest_path(project: Project, manifest: CampaignCandidateManifest) -> Path:
    return (
        campaign_manifest_root(project)
        / manifest.candidate_id
        / f"{manifest.commit}.json"
    )


def publish_campaign_manifest(
    project: Project,
    manifest: CampaignCandidateManifest,
) -> dict[str, Any]:
    """Publish one immutable manifest, idempotently for identical content."""

    if (
        manifest.constitution_review is None
        or manifest.constitution_review.verdict != "pass"
    ):
        raise CampaignReviewError(
            "campaign publication requires a passing constitution review"
        )

    path = _manifest_path(project, manifest)
    if path.exists():
        existing = DurableCampaignCandidateManifest.model_validate_json(
            path.read_text(encoding="utf-8")
        )
        payload = existing.model_dump(exclude={"project", "published_at"})
        if payload != manifest.model_dump():
            raise CampaignReviewError(
                f"campaign manifest {manifest.candidate_id!r} at "
                f"{manifest.commit} is immutable"
            )
        return existing.model_dump()

    durable = DurableCampaignCandidateManifest(
        **manifest.model_dump(),
        project=project.doc.name,
        published_at=datetime.now(timezone.utc).isoformat(),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(durable.model_dump(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return durable.model_dump()


def read_campaign_manifests(project: Project) -> list[dict[str, Any]]:
    """Read every immutable manifest in publication order."""

    root = campaign_manifest_root(project)
    if not root.exists():
        return []
    manifests = []
    for path in root.glob("*/*.json"):
        try:
            manifest = DurableCampaignCandidateManifest.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError) as exc:
            raise CampaignReviewError(
                f"invalid campaign manifest {path.relative_to(project.root)}: {exc}"
            ) from exc
        manifests.append(manifest.model_dump())
    return sorted(manifests, key=lambda row: (row["published_at"], row["candidate_id"]))


def read_campaign_review_records(project: Project) -> list[dict[str, Any]]:
    """Read the complete append-only decision ledger in write order."""

    path = campaign_review_path(project)
    if not path.exists():
        return []
    records = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            record = DurableCampaignReviewDecision.model_validate_json(line)
        except ValueError as exc:
            raise CampaignReviewError(
                f"invalid campaign review at line {line_number}: {exc}"
            ) from exc
        records.append(record.model_dump())
    return records


def _latest_manifests(project: Project) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for manifest in read_campaign_manifests(project):
        latest[manifest["candidate_id"]] = manifest
    return latest


def append_campaign_review(
    project: Project,
    decision: CampaignReviewDecision,
) -> dict[str, Any]:
    """Append one decision after proving it addresses the latest manifest."""

    manifest = _latest_manifests(project).get(decision.candidate_id)
    if manifest is None:
        raise CampaignReviewError(
            f"no campaign candidate {decision.candidate_id!r} is awaiting review"
        )
    if decision.candidate_commit != manifest["commit"]:
        raise CampaignReviewError(
            "candidate commit changed; reload the campaign review queue"
        )
    if decision.registry_fingerprint != manifest["registry_fingerprint"]:
        raise CampaignReviewError(
            "candidate registry fingerprint changed; reload the campaign review queue"
        )

    expected_ids = {specimen["id"] for specimen in manifest["specimens"]}
    reviewed_ids = {specimen.specimen_id for specimen in decision.specimens}
    unknown = reviewed_ids - expected_ids
    if unknown:
        raise CampaignReviewError(
            f"unknown campaign specimens: {', '.join(sorted(unknown))}"
        )
    if decision.verdict == "approved":
        if reviewed_ids != expected_ids:
            missing = expected_ids - reviewed_ids
            raise CampaignReviewError(
                "approval requires every specimen; missing "
                + ", ".join(sorted(missing))
            )
        if any(specimen.verdict != "valid" for specimen in decision.specimens):
            raise CampaignReviewError(
                "approval requires every specimen to be marked valid"
            )
    if decision.verdict == "changes_requested" and not any(
        specimen.verdict == "invalid" for specimen in decision.specimens
    ):
        raise CampaignReviewError(
            "changes requested requires at least one invalid specimen"
        )
    if decision.verdict == "unclear" and not any(
        specimen.verdict == "unclear" for specimen in decision.specimens
    ):
        raise CampaignReviewError(
            "an unclear decision requires at least one unclear specimen"
        )

    durable = DurableCampaignReviewDecision(
        **decision.model_dump(),
        id="campaign-review-" + uuid.uuid4().hex[:16],
        project=project.doc.name,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    path = campaign_review_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(durable.model_dump(), sort_keys=True) + "\n")
    return durable.model_dump()


def campaign_review_queue(project: Project) -> list[dict[str, Any]]:
    """Return one current queue row per candidate, newest candidates first."""

    manifests = _latest_manifests(project)
    reviews = read_campaign_review_records(project)
    queue = []
    for candidate_id, manifest in manifests.items():
        exact = [
            review
            for review in reviews
            if review["candidate_id"] == candidate_id
            and review["candidate_commit"] == manifest["commit"]
            and review["registry_fingerprint"] == manifest["registry_fingerprint"]
        ]
        stale = [
            review
            for review in reviews
            if review["candidate_id"] == candidate_id and review not in exact
        ]
        latest_review = exact[-1] if exact else None
        queue.append(
            {
                "manifest": manifest,
                "status": (
                    latest_review["verdict"]
                    if latest_review is not None
                    else "awaiting_review"
                ),
                "latest_review": latest_review,
                "stale_review_count": len(stale),
                "runtime_available": (
                    manifest["registry_fingerprint"]
                    == project.registry.fingerprint
                ),
            }
        )
    return sorted(
        queue,
        key=lambda row: row["manifest"]["published_at"],
        reverse=True,
    )
