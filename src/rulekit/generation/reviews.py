"""Append-only, project-local human review history."""

from __future__ import annotations

import json
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


def append_review(project: Project, review: ReviewRecord) -> dict:
    """Append a review and return the exact durable record."""

    record = {
        **review.model_dump(),
        "project": project.doc.name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    path = review_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def read_reviews(project: Project, limit: int = 100) -> list[dict]:
    """Return the newest bounded slice without involving the runtime."""

    path = review_path(project)
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines[-limit:]][::-1]
