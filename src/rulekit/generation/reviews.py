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
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..data.project import Project


class ReviewRecord(BaseModel):
    """The bounded request accepted from the designer."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1, max_length=128)
    sentence: str = Field(min_length=1, max_length=2000)
    target_rule: str = Field(min_length=1, max_length=256)
    seed: int
    registry_fingerprint: str = Field(min_length=8, max_length=128)
    verdict: Literal["valid", "invalid", "unclear"]
    note: str = Field(default="", max_length=4000)


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
) -> dict:
    """Append a correction that supersedes `review_id`.

    Only a live record may be corrected: editing an already superseded or
    tombstoned row would silently resurrect it when the chain is folded.
    """

    current = {r["id"]: r for r in _fold(_raw_reviews(project))}
    previous = current.get(review_id)
    if previous is None:
        raise KeyError(review_id)
    return _append(
        project,
        {
            **{k: v for k, v in previous.items() if k not in {"id", "timestamp"}},
            "id": "rev-" + uuid.uuid4().hex[:16],
            "supersedes": review_id,
            "verdict": verdict,
            "note": note,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
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
