"""Append-only, project-local human review history.

Corrections never rewrite the file. Editing a review appends a new record
carrying `supersedes`, and deleting one appends a record carrying
`tombstones`; `read_reviews` folds those chains into the current state. The
designer therefore gets ordinary edit/delete behaviour while the ledger stays
append-only and every prior human verdict remains recoverable from disk.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..data.project import Project


DefectKind = Literal[
    "premise_too_broad",
    "premise_too_narrow",
    "wrong_category_membership",
    "wrong_lexical_sense",
    "wrong_morphology_agreement",
    "inappropriate_optional_branch",
    "missing_cross_slot_constraint",
    "sentence_ungrammatical",
    "semantically_implausible",
    "intended_rule_did_not_fire",
    "another_rule_interfered",
    "generator_realization_defect",
    "unexpected_fact",
    "incorrect_fact_field",
    "missing_fact_context",
    "other",
]


class SourceLocation(BaseModel):
    """A bounded source pointer copied from the project source index."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=2000)
    line: int = Field(ge=1)
    column: int = Field(ge=1)
    kind: str = Field(min_length=1, max_length=128)
    label: str = Field(min_length=1, max_length=512)


class FactDerivationEvidence(BaseModel):
    """The bounded declarative template and bindings shown beside a fact."""

    model_config = ConfigDict(extra="forbid")

    templates: dict[str, Any] = Field(default_factory=dict, max_length=64)
    bindings: dict[str, str] = Field(default_factory=dict, max_length=64)


class FactEvidence(BaseModel):
    """The exact emitted fact selected when a human records a defect."""

    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=1, max_length=128)
    fields: dict[str, Any] = Field(default_factory=dict, max_length=64)
    source: str = Field(min_length=1, max_length=256)
    sentence: int = Field(ge=-1)
    source_ref: SourceLocation | None = None
    derivation: FactDerivationEvidence | None = None


class PremiseAttachment(BaseModel):
    """The sentence, exact premise row, or emitted fact under review.

    The public name predates fact-level review and remains stable for ledger
    compatibility.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["sentence", "rule", "token", "where", "fact"]
    index: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _index_matches_kind(self) -> "PremiseAttachment":
        if self.kind == "sentence" and self.index is not None:
            raise ValueError("a sentence attachment has no premise index")
        if self.kind != "sentence" and self.index is None:
            raise ValueError("a non-sentence attachment requires an index")
        return self


class ReviewDefect(BaseModel):
    """One human-selected defect and the evidence surface it concerns."""

    model_config = ConfigDict(extra="forbid")

    kind: DefectKind
    attachment: PremiseAttachment
    fact: FactEvidence | None = None

    @model_validator(mode="after")
    def _fact_matches_attachment(self) -> "ReviewDefect":
        fact_kinds = {
            "unexpected_fact",
            "incorrect_fact_field",
            "missing_fact_context",
        }
        if self.kind in fact_kinds and self.attachment.kind != "fact":
            raise ValueError("a fact defect must be attached to an emitted fact")
        if self.attachment.kind == "fact" and self.fact is None:
            raise ValueError("a fact attachment requires the emitted fact snapshot")
        if self.attachment.kind != "fact" and self.fact is not None:
            raise ValueError("only a fact attachment may carry a fact snapshot")
        return self


class HypothesisRecord(BaseModel):
    """One advisory, source-linked debugging hypothesis."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=128)
    kind: str = Field(min_length=1, max_length=128)
    claim: str = Field(min_length=1, max_length=2000)
    observations: list[str] = Field(min_length=1, max_length=16)
    premise: PremiseAttachment
    sources: list[SourceLocation] = Field(default_factory=list, max_length=32)
    note: str = Field(default="", max_length=4000)
    status: Literal["open", "confirmed", "rejected", "inconclusive"] = "open"


class ReviewRecord(BaseModel):
    """The bounded request accepted from the designer."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1, max_length=128)
    origin: Literal["generated", "reading"] = "generated"
    review_kind: Literal["premise", "sentence"] = "premise"
    sentence: str = Field(min_length=1, max_length=2000)
    target_rule: str | None = Field(default=None, min_length=1, max_length=256)
    seed: int
    registry_fingerprint: str = Field(min_length=8, max_length=128)
    verdict: Literal["valid", "invalid", "unclear"]
    requested_bindings: dict[str, str] = Field(default_factory=dict, max_length=64)
    defects: list[ReviewDefect] = Field(default_factory=list, max_length=16)
    hypotheses: list[HypothesisRecord] = Field(default_factory=list, max_length=32)
    interpretation: str = Field(default="", max_length=4000)
    suggested_rule: str = Field(default="", max_length=4000)
    note: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def _subject_matches_review_kind(self) -> "ReviewRecord":
        if self.review_kind == "premise" and self.target_rule is None:
            raise ValueError("a premise review requires a target rule")
        if self.review_kind == "sentence" and self.target_rule is not None:
            raise ValueError("a sentence review cannot claim a target rule")
        if self.review_kind == "sentence" and self.origin != "reading":
            raise ValueError("a sentence review must originate in Reading")
        return self


def review_path(project: Project) -> Path:
    """The one durable review path; callers cannot supply another."""

    return project.root / "generation" / "reviews.jsonl"


def _legacy_id(record: dict) -> str:
    """A stable id for rows written before ids existed.

    Derived from the immutable pair, so the same historical row always folds
    to the same identity across reads — a random id would orphan any edit the
    moment the designer reloaded.
    """

    seed = f"{record.get('candidate_id', '')}|{record.get('timestamp', '')}"
    return "rev-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _append(project: Project, record: dict) -> dict:
    path = review_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def _raw_reviews(project: Project) -> list[dict]:
    """Every record in write order, each guaranteed to carry an id."""

    path = review_path(project)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        record.setdefault("id", _legacy_id(record))
        rows.append(record)
    return rows


def _fold(rows: list[dict]) -> list[dict]:
    """Collapse supersede/tombstone chains down to the live records."""

    superseded = {r["supersedes"] for r in rows if r.get("supersedes")}
    tombstoned = {r["tombstones"] for r in rows if r.get("tombstones")}
    return [
        r
        for r in rows
        # a tombstone is a marker, never itself a review
        if not r.get("tombstones")
        and r["id"] not in superseded
        and r["id"] not in tombstoned
    ]


def append_review(project: Project, review: ReviewRecord) -> dict:
    """Append a review and return the exact durable record."""

    return _append(
        project,
        {
            **review.model_dump(),
            "id": "rev-" + uuid.uuid4().hex[:16],
            "project": project.doc.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


def update_review(
    project: Project,
    review_id: str,
    verdict: str,
    note: str,
    hypotheses: list[HypothesisRecord] | None = None,
    interpretation: str | None = None,
    suggested_rule: str | None = None,
) -> dict:
    """Append a correction that supersedes `review_id`.

    Only a live record may be corrected: editing an already superseded or
    tombstoned row would silently resurrect it when the chain is folded.
    """

    current = {r["id"]: r for r in _fold(_raw_reviews(project))}
    previous = current.get(review_id)
    if previous is None:
        raise KeyError(review_id)
    corrected = {
        **{k: v for k, v in previous.items() if k not in {"id", "timestamp"}},
        "id": "rev-" + uuid.uuid4().hex[:16],
        "supersedes": review_id,
        "verdict": verdict,
        "note": note,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if hypotheses is not None:
        corrected["hypotheses"] = [
            hypothesis.model_dump() for hypothesis in hypotheses
        ]
    if interpretation is not None:
        corrected["interpretation"] = interpretation
    if suggested_rule is not None:
        corrected["suggested_rule"] = suggested_rule
    return _append(
        project,
        corrected,
    )


def delete_review(project: Project, review_id: str) -> dict:
    """Append a tombstone hiding `review_id` from the folded history."""

    current = {r["id"]: r for r in _fold(_raw_reviews(project))}
    if review_id not in current:
        raise KeyError(review_id)
    return _append(
        project,
        {
            "id": "rev-" + uuid.uuid4().hex[:16],
            "tombstones": review_id,
            "project": project.doc.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


def read_reviews(project: Project, limit: int = 100) -> list[dict]:
    """Return the newest bounded slice of LIVE reviews, newest first.

    The bound applies after folding, so a heavily edited history still yields
    a full page of current records rather than a page of spent corrections.
    """

    return _fold(_raw_reviews(project))[-limit:][::-1]
