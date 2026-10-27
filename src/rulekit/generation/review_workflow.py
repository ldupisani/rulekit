"""Pinned retests and independently judged evidence updates for saved reviews.

Retesting never writes. Recording appends a fresh judgment linked to its source;
resolution remains the separate lifecycle operation in reviews.py.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..data.project import Project
from ..kernel.model import _jsonable
from .ask_generation import _answer_json
from .candidate import (
    LexicalRelaxation,
    reading_context_requirements,
    reading_grammar_deficiencies,
)
from .reviews import (
    InterpretationJudgment,
    NaturalnessJudgment,
    ResultJudgment,
    ReviewRecord,
    _read_reviewed_ask,
    append_review,
    read_review_history,
)
from .sample import (
    _collision_json,
    _fact_json,
    promote_sentence_review_candidate,
    retest_candidate,
)


class ReviewWorkflowConflict(ValueError):
    """The reviewed source or displayed retest is no longer current."""


class UpdatedEvidenceBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retest_token: str = Field(pattern=r"^[0-9a-f]{64}$")
    verdict: Literal["valid", "invalid", "unclear"]
    interpretation_judgment: InterpretationJudgment
    result_judgment: ResultJudgment
    naturalness: NaturalnessJudgment | None = None
    note: str = Field(default="", max_length=4000)


def saved_review(project: Project, review_id: str) -> dict:
    """Only a visible current record or visible resolution can be acted on."""
    for review in read_review_history(project, 100_000):
        if review["id"] == review_id:
            return review
    raise KeyError(review_id)


def retest_saved_review(project: Project, review_id: str) -> dict:
    review = saved_review(project, review_id)
    # Human judgments and defects belong to the old snapshot. The new draft
    # requires its own human judgment, even when the engine is unchanged.
    draft = {
        key: value for key, value in review.items() if key in ReviewRecord.model_fields
    }
    draft.update(
        updates_review_id=review_id,
        registry_fingerprint=project.registry.fingerprint,
        verdict="unclear",
        interpretation_judgment="not_reviewed",
        result_judgment="not_reviewed",
        naturalness=None,
        note="",
        defects=[],
        hypotheses=[],
    )
    blockers = []
    if review.get("ask_scenario"):
        scenario = dict(review["ask_scenario"])
        result, matched = _read_reviewed_ask(project, review)
        answer, shape = _answer_json(result.answer)
        query = _jsonable(matched[1]) if matched else {}
        actual_ask = matched[0].id if matched else None
        if actual_ask != scenario["target_ask"]:
            blockers.append(
                "The saved target ask no longer wins; inspect the reading before validating it."
            )
        scenario.update(
            query=query,
            consumer=query.get("consumer"),
            answer=answer,
            answer_shape=shape,
            minimal=False,
            premise_review_ids=[],
        )
        # Prior premise judgments and minimality are not fresh evidence.
        draft["ask_scenario"] = scenario
        readings = result.premises + ([result.question] if result.question else [])
        current = {
            "text": scenario["text"],
            "actual_ask": actual_ask,
            "query": query,
            "answer": answer,
            "facts": [_fact_json(f, project) for f in result.store.facts],
            "collisions": [_collision_json(c) for c in result.store.collisions],
            "deficiencies": [
                gap for reading in readings for gap in reading.deficiencies()
            ],
            "context_requirements": [
                asdict(requirement)
                for reading in readings
                for requirement in reading_context_requirements(reading)
            ],
            "grammar_deficiencies": [
                gap for reading in readings for gap in reading_grammar_deficiencies(reading)
            ],
        }
        for index, target in enumerate(scenario.get("premise_rules") or []):
            matches = (
                result.document.rule_results.get(index, []) if result.document else []
            )
            if target and not any(m.match.rule.id == target for m in matches):
                blockers.append(
                    f"Saved premise {index + 1} no longer matches {target}."
                )
    else:
        args = dict(
            sentence=review["sentence"],
            seed=review["seed"],
            context_before=tuple(review.get("context_before") or []),
            context_after=tuple(review.get("context_after") or []),
        )
        if review.get("target_rule"):
            candidate = retest_candidate(
                project,
                **args,
                rule_id=review["target_rule"],
                origin=review.get("origin") or "generated",
                generation_mode=review.get("generation_mode") or "strict",
                requested_bindings=review.get("requested_bindings") or {},
                lexical_relaxations=tuple(
                    LexicalRelaxation(**v)
                    for v in review.get("lexical_relaxations") or []
                ),
            )
            current = candidate.to_json()
            draft["premise_evidence"] = {
                key: current[key]
                for key in (
                    "target_status",
                    "target_bindings",
                    "actual_rule_ids",
                    "facts",
                    "collisions",
                    "deficiencies",
                )
            }
            if candidate.target_status not in {"matched", "shadowed"}:
                blockers.append(
                    f"The saved target premise is now {candidate.target_status}."
                )
        else:
            candidate = promote_sentence_review_candidate(project, **args)
            current = candidate.to_json()
        draft["candidate_id"] = candidate.id
    # Ask judgments validate the ask/query/result contract, not every premise
    # or the low-level question reader. Keep those observations inspectable
    # without turning them into premise-coverage claims.
    if not review.get("ask_scenario"):
        if current["collisions"]:
            blockers.append("The current reading contains conflicting facts.")
        blockers.extend(current["deficiencies"])
    if review.get("ask_scenario"):
        digest = hashlib.sha256(
            json.dumps(current, sort_keys=True).encode()
        ).hexdigest()[:20]
        draft["candidate_id"] = f"askretest-{digest}"
    draft = ReviewRecord.model_validate(draft).model_dump()
    payload = {
        "review_id": review_id,
        "registry_fingerprint": project.registry.fingerprint,
        "draft": draft,
        "current": current,
        "validation_blockers": blockers,
    }
    payload["retest_token"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()
    return payload


def record_updated_evidence(
    project: Project, review_id: str, body: UpdatedEvidenceBody
) -> dict:
    # Recompute from saved text: a client cannot submit arbitrary facts or
    # silently confirm a retest made before a registry/source change.
    retest = retest_saved_review(project, review_id)
    if body.retest_token != retest["retest_token"]:
        raise ReviewWorkflowConflict(
            "The reading changed. Retest this saved example again before recording evidence."
        )
    if (
        body.interpretation_judgment == "not_reviewed"
        or body.result_judgment == "not_reviewed"
    ):
        raise ReviewWorkflowConflict(
            "Review the current interpretation and result before recording updated evidence."
        )
    if body.verdict == "valid" and retest["validation_blockers"]:
        raise ReviewWorkflowConflict(
            "The current reading still has validation blockers; fix them or record an invalid/unclear judgment."
        )
    values = body.model_dump(exclude={"retest_token"})
    return append_review(
        project, ReviewRecord.model_validate({**retest["draft"], **values})
    )
