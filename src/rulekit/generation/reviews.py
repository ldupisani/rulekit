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
from ..kernel.engine import analyze, solve
from ..kernel.model import _jsonable
from ..kernel.patterns import match_ask
from .candidate import AskScenarioMode, GenerationMode, LexicalRelaxation


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
    "intended_ask_did_not_fire",
    "incorrect_query_binding",
    "irrelevant_premise_evidence",
    "incorrect_answer",
    "incorrect_decline",
    "scenario_not_minimal",
    "unexpected_fact",
    "incorrect_fact_field",
    "missing_fact_context",
    "other",
]

InterpretationJudgment = Literal[
    "correct", "incorrect", "unclear", "not_reviewed"
]
ResultJudgment = Literal[
    "correct_answer",
    "correct_decline",
    "correct_facts",
    "incorrect",
    "unclear",
    "not_applicable",
    "not_reviewed",
]
NaturalnessJudgment = Literal["preferred", "acceptable", "marginal"]

_REVIEW_EVIDENCE_ROWS_CACHE: dict[
    tuple[str, int, int], tuple[tuple[dict, ...], tuple[dict, ...]]
] = {}
_ASK_EVIDENCE_CACHE: dict[tuple[str, int, int, str], dict[str, Any]] = {}
_PREMISE_EVIDENCE_CACHE: dict[tuple[str, int, int, str], dict[str, Any]] = {}
_VALIDATED_PREMISE_CACHE: dict[
    tuple[str, int, int, str], tuple[dict[str, Any], ...]
] = {}


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


class AskScenarioReviewEvidence(BaseModel):
    """The exact generated question, evidence, and solver result reviewed.

    Ask reviews pin the whole scenario rather than only its final question.
    The ordinary review lifecycle can therefore edit, resolve, or tombstone a
    verdict without ever reconstructing evidence from a later registry.
    """

    model_config = ConfigDict(extra="forbid")

    target_ask: str = Field(min_length=1, max_length=256)
    scenario_mode: AskScenarioMode
    question: str = Field(min_length=1, max_length=2000)
    text: str = Field(min_length=1, max_length=8000)
    consumer: str | None = Field(default=None, min_length=1, max_length=128)
    query: dict[str, Any] = Field(default_factory=dict, max_length=64)
    premises: list[str] = Field(default_factory=list, max_length=8)
    premise_rules: list[str] = Field(default_factory=list, max_length=8)
    premise_review_ids: list[str | None] = Field(
        default_factory=list,
        max_length=8,
    )
    answer: dict[str, Any] = Field(default_factory=dict, max_length=64)
    answer_shape: str = Field(min_length=1, max_length=128)
    minimal: bool

    @model_validator(mode="after")
    def _scenario_is_self_consistent(self) -> "AskScenarioReviewEvidence":
        if self.question not in self.text:
            raise ValueError("ask scenario text must contain its exact question")
        if len(self.premises) != len(self.premise_rules):
            raise ValueError(
                "ask scenario premise sentences and rule ids must align"
            )
        if self.premise_review_ids and len(self.premises) != len(
            self.premise_review_ids
        ):
            raise ValueError(
                "ask scenario premise sentences and review ids must align"
            )
        return self


class PremiseReviewEvidence(BaseModel):
    """The exact matcher and fact contract visible during premise review."""

    model_config = ConfigDict(extra="forbid")

    target_status: str = Field(min_length=1, max_length=64)
    target_bindings: dict[str, str] = Field(default_factory=dict, max_length=64)
    actual_rule_ids: list[str] = Field(default_factory=list, max_length=64)
    facts: list[dict[str, Any]] = Field(default_factory=list, max_length=64)
    collisions: list[dict[str, Any]] = Field(default_factory=list, max_length=32)
    deficiencies: list[str] = Field(default_factory=list, max_length=64)


class ReviewRecord(BaseModel):
    """The bounded request accepted from the designer."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1, max_length=128)
    origin: Literal["generated", "reading"] = "generated"
    generation_mode: GenerationMode = "strict"
    lexical_relaxations: list[LexicalRelaxation] = Field(
        default_factory=list, max_length=16
    )
    review_kind: Literal["premise", "sentence", "ask"] = "premise"
    sentence: str = Field(min_length=1, max_length=2000)
    context_before: list[str] = Field(default_factory=list, max_length=8)
    context_after: list[str] = Field(default_factory=list, max_length=8)
    target_rule: str | None = Field(default=None, min_length=1, max_length=256)
    premise_evidence: PremiseReviewEvidence | None = None
    ask_scenario: AskScenarioReviewEvidence | None = None
    seed: int
    registry_fingerprint: str = Field(min_length=8, max_length=128)
    verdict: Literal["valid", "invalid", "unclear"]
    interpretation_judgment: InterpretationJudgment = "not_reviewed"
    result_judgment: ResultJudgment = "not_reviewed"
    naturalness: NaturalnessJudgment | None = None
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
        if self.review_kind != "premise" and self.premise_evidence is not None:
            raise ValueError("only a premise review may carry premise evidence")
        if self.review_kind != "premise" and self.target_rule is not None:
            raise ValueError("only a premise review can claim a target rule")
        if self.review_kind == "sentence" and self.origin != "reading":
            raise ValueError("a sentence review must originate in Reading")
        if self.review_kind == "ask":
            if self.origin != "generated":
                raise ValueError("an ask review must originate in Generate")
            if self.ask_scenario is None:
                raise ValueError("an ask review requires pinned scenario evidence")
            if self.sentence != self.ask_scenario.question:
                raise ValueError("an ask review sentence must be its exact question")
        elif self.ask_scenario is not None:
            raise ValueError("only an ask review may carry ask scenario evidence")
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
    """Collapse supersede/delete/resolve chains down to open records."""

    superseded = {r["supersedes"] for r in rows if r.get("supersedes")}
    tombstoned = {r["tombstones"] for r in rows if r.get("tombstones")}
    resolved = {r["resolves"] for r in rows if r.get("resolves")}
    return [
        r
        for r in rows
        # lifecycle markers are history, never open review work
        if not r.get("tombstones")
        and not r.get("resolves")
        and r["id"] not in superseded
        and r["id"] not in tombstoned
        and r["id"] not in resolved
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
    interpretation_judgment: InterpretationJudgment | None = None,
    result_judgment: ResultJudgment | None = None,
    naturalness: NaturalnessJudgment | None = None,
    update_naturalness: bool = False,
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
    if interpretation_judgment is not None:
        corrected["interpretation_judgment"] = interpretation_judgment
    if result_judgment is not None:
        corrected["result_judgment"] = result_judgment
    if naturalness is not None or update_naturalness:
        corrected["naturalness"] = naturalness
    return _append(
        project,
        corrected,
    )


def delete_review(project: Project, review_id: str) -> dict:
    """Append a tombstone hiding `review_id` from the folded history."""

    current = {
        r["id"]: r
        for r in (
            *_fold(_raw_reviews(project)),
            *read_review_history(project, 100_000),
        )
    }
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


def resolve_review(
    project: Project, review_id: str, note: str = ""
) -> dict:
    """Append a visible resolution without changing the human judgment.

    Resolution is distinct from deletion: open-review gates stop replaying the
    row, but the Designer history keeps the exact sentence, verdict, defects,
    and note visible. A previously tombstoned row may be resolved so an agent
    can repair an accidental delete without rewriting the ledger.
    """

    rows = _raw_reviews(project)
    if any(row.get("resolves") == review_id for row in rows):
        raise KeyError(review_id)
    previous = next(
        (
            row
            for row in reversed(rows)
            if row.get("id") == review_id
            and not row.get("tombstones")
            and not row.get("resolves")
        ),
        None,
    )
    if previous is None:
        raise KeyError(review_id)
    resolved_at = datetime.now(timezone.utc).isoformat()
    return _append(
        project,
        {
            **{key: value for key, value in previous.items() if key != "id"},
            "id": "rev-" + uuid.uuid4().hex[:16],
            "resolves": review_id,
            "resolved_at": resolved_at,
            "resolution_note": note,
        },
    )


def read_reviews(project: Project, limit: int = 100) -> list[dict]:
    """Return the newest bounded slice of LIVE reviews, newest first.

    The bound applies after folding, so a heavily edited history still yields
    a full page of current records rather than a page of spent corrections.
    """

    return _fold(_raw_reviews(project))[-limit:][::-1]


def read_review_history(project: Project, limit: int = 100) -> list[dict]:
    """Return open and resolved reviews, while retaining true deletions.

    Resolution markers copy the immutable reviewed artefact so old Designer
    servers also render them. New callers receive an explicit status and never
    confuse the copied marker with open work.
    """

    rows = _raw_reviews(project)
    superseded = {row["supersedes"] for row in rows if row.get("supersedes")}
    tombstoned = {row["tombstones"] for row in rows if row.get("tombstones")}
    resolved_targets = {
        row["resolves"] for row in rows if row.get("resolves")
    }
    resolution_by_target = {
        row["resolves"]: row
        for row in rows
        if row.get("resolves") and row["id"] not in tombstoned
    }
    history: list[dict] = []
    for row in rows:
        if row.get("tombstones") or row.get("resolves"):
            continue
        if row["id"] in superseded:
            continue
        resolved = resolution_by_target.get(row["id"])
        if resolved is not None:
            history.append({**resolved, "review_status": "resolved"})
        elif row["id"] in resolved_targets:
            # The resolution marker itself was tombstoned after verification;
            # do not resurrect the original review as open work.
            continue
        elif row["id"] not in tombstoned:
            history.append({**row, "review_status": "open"})
    return history[-limit:][::-1]


def ask_review_signature(review: dict) -> str | None:
    """Return a vocabulary-independent structural key for one ask review.

    Exact words deliberately do not participate. Repeated judgments of the
    same declared ask branch therefore increase confidence in one coverage
    group instead of manufacturing thousands of apparent grammar shapes.
    """

    scenario = review.get("ask_scenario")
    if not isinstance(scenario, dict):
        return None
    payload = {
        "target_ask": scenario.get("target_ask"),
        "scenario_mode": scenario.get("scenario_mode"),
        "consumer": scenario.get("consumer"),
        "answer_shape": scenario.get("answer_shape"),
        "query_fields": sorted((scenario.get("query") or {}).keys()),
        "binding_fields": sorted((review.get("requested_bindings") or {}).keys()),
        "premise_rules": scenario.get("premise_rules") or [],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "askcov-" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def _review_evidence_rows(
    project: Project,
) -> tuple[tuple[dict, ...], tuple[dict, ...]]:
    """Reuse non-deleted evidence until its append-only file changes.

    Resolution closes an inbox item but deliberately retains its reviewed
    artefact. Tombstones are the only lifecycle operation that removes a row
    from this evidence fold.
    """

    path = review_path(project)
    if not path.exists():
        return (), ()
    stat = path.stat()
    key = (str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    cached = _REVIEW_EVIDENCE_ROWS_CACHE.get(key)
    if cached is not None:
        return cached
    history = read_review_history(project, limit=100_000)
    ask_rows = tuple(
        review
        for review in history
        if isinstance(review.get("ask_scenario"), dict)
    )
    premise_rows = tuple(
        review
        for review in history
        if review.get("target_rule") is not None
        and (review.get("review_kind") or "premise") == "premise"
    )
    if len(_REVIEW_EVIDENCE_ROWS_CACHE) >= 8:
        _REVIEW_EVIDENCE_ROWS_CACHE.clear()
    result = ask_rows, premise_rows
    _REVIEW_EVIDENCE_ROWS_CACHE[key] = result
    return result


def _evidence_cache_key(project: Project) -> tuple[str, int, int, str]:
    path = review_path(project)
    if not path.exists():
        return str(path.resolve()), 0, 0, project.registry.fingerprint
    stat = path.stat()
    return (
        str(path.resolve()),
        stat.st_mtime_ns,
        stat.st_size,
        project.registry.fingerprint,
    )


def _bounded_cache_store(cache: dict, key: tuple, value: Any) -> Any:
    if len(cache) >= 8:
        cache.clear()
    cache[key] = value
    return value


def _live_ask_reviews(project: Project) -> tuple[dict, ...]:
    # Compatibility name: these are live *evidence*, including resolved rows.
    return _review_evidence_rows(project)[0]


def _live_premise_reviews(project: Project) -> tuple[dict, ...]:
    return _review_evidence_rows(project)[1]


def review_needs_attention(review: dict) -> bool:
    """Return whether a live judgment still records an unresolved problem.

    Verdict, interpretation, result, and attached defects are independent
    review axes.  A grammatically valid surface can therefore still report a
    bad fact or malformed sentence; treating that row as clean positive
    evidence would erase the very problem the reviewer recorded.
    """

    evidence = review.get("premise_evidence") or {}
    machine_gaps = bool(evidence.get("collisions") or evidence.get("deficiencies"))
    if review.get("target_rule") and evidence:
        machine_gaps |= evidence.get("target_status") not in {"matched", "shadowed"}
    return machine_gaps or bool(review.get("defects")) or review.get("verdict") in {
        "invalid",
        "unclear",
    } or review.get("interpretation_judgment") in {
        "incorrect",
        "unclear",
    } or review.get("result_judgment") in {"incorrect", "unclear"}


def _is_clean_valid_review(review: dict) -> bool:
    return review.get("verdict") == "valid" and not review_needs_attention(review)


def premise_review_signature(review: dict) -> str | None:
    target = review.get("target_rule")
    if not isinstance(target, str):
        return None
    evidence = review.get("premise_evidence") or {}
    payload = {
        "target_rule": target,
        "generation_mode": review.get("generation_mode") or "strict",
        "binding_fields": sorted((review.get("requested_bindings") or {}).keys()),
        "context_before": len(review.get("context_before") or []),
        "context_after": len(review.get("context_after") or []),
        "fact_types": sorted(
            str(fact.get("type")) for fact in evidence.get("facts", [])
        ),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "premcov-" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def premise_review_target_counts(project: Project) -> dict[str, int]:
    """Count durable positive premise evidence per declared target."""

    counts: dict[str, int] = {}
    for review in _live_premise_reviews(project):
        target = review.get("target_rule")
        if _is_clean_valid_review(review) and isinstance(target, str):
            counts[target] = counts.get(target, 0) + 1
    return counts


def _fact_contract(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    contracted = [
        {
            "type": fact.get("type"),
            "fields": fact.get("fields") or {},
            "source": fact.get("source"),
            "sentence": fact.get("sentence"),
        }
        for fact in facts
    ]
    return sorted(
        contracted,
        key=lambda fact: json.dumps(fact, sort_keys=True, separators=(",", ":")),
    )


def _reviewed_facts_match(current: list[dict], expected: list[dict]) -> bool:
    """Replay the captured contract, allowing only typed reference enrichment.

    This is not human approval of newly exposed identity data. Every recorded
    field, including any recorded identity, remains exact. A one-to-one match
    preserves duplicate facts and ignores serialization ordering only.
    """
    from dataclasses import MISSING, fields
    from typing import get_args, get_type_hints
    from ..kernel.patterns import _FACT_CLASSES
    from ..kernel.reference_identity import ReferenceIdentity
    from ..kernel.model import Provenance

    classes = {cls.__name__: cls for cls in _FACT_CLASSES.values()}
    nullable_required: dict[type, dict[str, None]] = {}

    def preserves_flat_constraints(old, new) -> bool:
        # Older rows have flat descriptor projections, not a complete identity.
        # Added nested ownership or local anchors may refine them but cannot
        # contradict a descriptor the reviewer already saw. Display equality
        # is checked directly, never parsed back into structural identity.
        return bool(
            old.head in (new.head, new.display())
            and (old.label is None or old.label == new.label)
            and set(old.qualifiers).issubset(new.qualifiers)
            and (old.owner is None or (new.owner is not None
                 and preserves_flat_constraints(old.owner, new.owner)))
        )

    def compatible(actual: dict, recorded: dict) -> bool:
        if any(actual[key] != recorded[key] for key in ("type", "source", "sentence")):
            return False
        now, before = actual["fields"], recorded["fields"]
        if any(key not in now or now[key] != value for key, value in before.items()):
            return False
        cls = classes.get(actual["type"])
        declared = {field.name: field.metadata["reference_for"] for field in fields(cls)
                    if "reference_for" in field.metadata} if cls else {}
        for key in now.keys() - before.keys():
            role = declared.get(key)
            if role is None:
                return False
            try:
                ref = ReferenceIdentity.from_dict(now[key])
            except (TypeError, ValueError, KeyError):
                return False
            if (not ref.resolved or ref.to_dict() != now[key]
                    or now.get(role) not in (ref.head, ref.display())):
                return False
            try:
                # Reuse the fact type's own legacy adapter. In particular,
                # Relation's item qualifiers are not participant qualifiers.
                # FactEvidence omits null fields, including required nullable
                # ones such as an elided relation measure. Restore only those
                # explicitly nullable constructor fields, never missing data.
                if cls not in nullable_required:
                    hints = get_type_hints(cls)
                    nullable_required[cls] = {
                        item.name: None for item in fields(cls)
                        if item.default is MISSING and item.default_factory is MISSING
                        and type(None) in get_args(hints.get(item.name))
                    }
                flat_fact = cls(
                    provenance=Provenance(actual["source"], actual["sentence"]),
                    **(nullable_required[cls] | {
                        name: value for name, value in now.items() if name not in declared
                    }),
                )
                flat = getattr(flat_fact, key)
            except (TypeError, ValueError, KeyError):
                return False
            if not preserves_flat_constraints(flat, ref):
                return False
        return True

    actual, recorded = _fact_contract(current), _fact_contract(expected)
    if len(actual) != len(recorded):
        return False
    # Augmenting-path matching handles older rows with fewer identity fields
    # beside newer rows, without a greedy order-dependent assignment.
    edges = [[i for i, candidate in enumerate(actual) if compatible(candidate, row)]
             for row in recorded]
    assigned: dict[int, int] = {}

    def assign(row: int, seen: set[int]) -> bool:
        for candidate in edges[row]:
            if candidate in seen:
                continue
            seen.add(candidate)
            if candidate not in assigned or assign(assigned[candidate], seen):
                assigned[candidate] = row
                return True
        return False

    return all(assign(row, set()) for row in range(len(recorded)))


def replay_premise_review(
    project: Project,
    review: dict,
    *,
    include_candidate: bool = False,
) -> dict[str, Any]:
    """Replay a pinned positive premise through the ordinary document path."""

    target = review.get("target_rule")
    if not isinstance(target, str):
        return {"status": "not_applicable", "detail": "not a premise review"}
    try:
        # Local import avoids making review schemas a dependency of the
        # premise generator while still using its one canonical retest path.
        from .sample import retest_candidate

        candidate = retest_candidate(
            project,
            rule_id=target,
            sentence=str(review.get("sentence") or ""),
            seed=int(review.get("seed") or 0),
            requested_bindings=dict(review.get("requested_bindings") or {}),
            origin=str(review.get("origin") or "generated"),
            generation_mode=str(review.get("generation_mode") or "strict"),
            lexical_relaxations=tuple(
                LexicalRelaxation(**item)
                for item in review.get("lexical_relaxations") or []
            ),
            context_before=tuple(review.get("context_before") or []),
            context_after=tuple(review.get("context_after") or []),
        )
    except Exception as exc:
        return {
            "status": "regressed",
            "detail": f"replay failed: {type(exc).__name__}: {exc}",
        }
    if candidate.target_status not in {"matched", "shadowed"}:
        return {
            "status": "regressed",
            "detail": f"the reviewed target is now {candidate.target_status}",
        }
    if candidate.collisions:
        return {
            "status": "regressed",
            "detail": "the reviewed premise now produces a collision",
        }

    evidence = review.get("premise_evidence")
    if isinstance(evidence, dict):
        actual = candidate.to_json()
        comparisons = [
            ("target status", actual["target_status"], evidence.get("target_status")),
            ("target bindings", actual["target_bindings"], evidence.get("target_bindings")),
            ("co-firing rules", actual["actual_rule_ids"], evidence.get("actual_rule_ids")),
            ("facts", _reviewed_facts_match(actual["facts"], evidence.get("facts") or []), True),
            ("collisions", list(actual["collisions"]), evidence.get("collisions") or []),
        ]
        for label, current, expected in comparisons:
            if current != expected:
                return {
                    "status": "regressed",
                    "detail": f"the premise {label} changed",
                }
        # A positive exemplar regresses when replay GAINS a grammatical gap.
        # Removing an old deficiency is a monotone improvement: the reviewed
        # target, bindings, co-firing rules, and fact contract remain exact,
        # while a newly anchored construction no longer reports a false gap.
        current_deficiencies = set(actual["deficiencies"])
        expected_deficiencies = set(evidence.get("deficiencies") or [])
        if not current_deficiencies <= expected_deficiencies:
            return {
                "status": "regressed",
                "detail": "the premise gained deficiencies",
            }
    status = (
        "current"
        if review.get("registry_fingerprint") == project.registry.fingerprint
        else "machine_reconfirmed"
    )
    result: dict[str, Any] = {
        "status": status,
        "detail": "target premise and emitted facts replayed",
    }
    if include_candidate:
        result["candidate"] = candidate.to_json()
    return result


def premise_review_evidence(project: Project) -> dict[str, Any]:
    cache_key = _evidence_cache_key(project)
    cached = _PREMISE_EVIDENCE_CACHE.get(cache_key)
    if cached is not None:
        return cached
    reviews = list(_live_premise_reviews(project))
    grouped: dict[str, list[dict]] = {}
    for review in reviews:
        signature = premise_review_signature(review)
        if signature is not None:
            grouped.setdefault(signature, []).append(review)

    groups: list[dict[str, Any]] = []
    for signature, rows in grouped.items():
        valid = [row for row in rows if _is_clean_valid_review(row)]
        canonical = None
        if valid:
            preference = {"preferred": 0, "acceptable": 1, None: 2, "marginal": 3}
            best_preference = min(
                preference.get(row.get("naturalness"), 2) for row in valid
            )
            canonical = max(
                (
                    row
                    for row in valid
                    if preference.get(row.get("naturalness"), 2)
                    == best_preference
                ),
                key=lambda row: str(row.get("timestamp") or ""),
            )
        replay = (
            replay_premise_review(project, canonical)
            if canonical is not None
            else {"status": "unvalidated", "detail": "no valid judgment"}
        )
        groups.append(
            {
                "signature": signature,
                "target_rule": rows[-1].get("target_rule"),
                "generation_mode": rows[-1].get("generation_mode") or "strict",
                "binding_fields": sorted(
                    (rows[-1].get("requested_bindings") or {}).keys()
                ),
                "review_count": len(rows),
                "verdict_counts": {
                    verdict: sum(row.get("verdict") == verdict for row in rows)
                    for verdict in ("valid", "invalid", "unclear")
                },
                "naturalness_counts": {
                    value: sum(row.get("naturalness") == value for row in valid)
                    for value in ("preferred", "acceptable", "marginal")
                },
                "canonical_review_id": canonical.get("id") if canonical else None,
                "last_reviewed_at": max(
                    str(row.get("timestamp") or "") for row in rows
                ),
                "replay_status": replay["status"],
                "replay_detail": replay["detail"],
            }
        )
    groups.sort(key=lambda group: (str(group["target_rule"]), group["signature"]))
    targets: dict[str, dict[str, int]] = {}
    for group in groups:
        target = str(group["target_rule"])
        counts = targets.setdefault(
            target,
            {"groups": 0, "validated_groups": 0, "valid_reviews": 0},
        )
        counts["groups"] += 1
        counts["valid_reviews"] += group["verdict_counts"]["valid"]
        if group["replay_status"] in {"current", "machine_reconfirmed"}:
            counts["validated_groups"] += 1
    result = {
        "summary": {
            "review_count": len(reviews),
            "valid_count": sum(row.get("verdict") == "valid" for row in reviews),
            "clean_valid_count": sum(_is_clean_valid_review(row) for row in reviews),
            "action_count": sum(
                row.get("review_status") != "resolved"
                and review_needs_attention(row)
                for row in reviews
            )
            + sum(group["replay_status"] == "regressed" for group in groups),
            "group_count": len(groups),
            "validated_group_count": sum(
                group["replay_status"] in {"current", "machine_reconfirmed"}
                for group in groups
            ),
            "regressed_group_count": sum(
                group["replay_status"] == "regressed" for group in groups
            ),
            "target_count": len(targets),
        },
        "targets": targets,
        "groups": groups,
    }
    return _bounded_cache_store(_PREMISE_EVIDENCE_CACHE, cache_key, result)


def validated_premise_candidates(project: Project) -> list[dict[str, Any]]:
    """Return one replay-valid strict premise per structural review group."""

    cache_key = _evidence_cache_key(project)
    cached = _VALIDATED_PREMISE_CACHE.get(cache_key)
    if cached is not None:
        return list(cached)
    by_id = {review.get("id"): review for review in _live_premise_reviews(project)}
    candidates: list[dict[str, Any]] = []
    for group in premise_review_evidence(project)["groups"]:
        if group["generation_mode"] != "strict":
            continue
        review = by_id.get(group["canonical_review_id"])
        if review is None:
            continue
        replay = replay_premise_review(project, review, include_candidate=True)
        if replay["status"] not in {"current", "machine_reconfirmed"}:
            continue
        candidate = replay["candidate"]
        candidates.append(
            {
                **candidate,
                "sentence": candidate["text"],
                "validated_review_id": review.get("id"),
            }
        )
    _bounded_cache_store(
        _VALIDATED_PREMISE_CACHE, cache_key, tuple(candidates)
    )
    return candidates


def ask_review_surface_signature(
    *,
    target_ask: str,
    scenario_mode: str,
    consumer: str | None,
    query_fields: list[str] | tuple[str, ...],
    binding_fields: list[str] | tuple[str, ...],
) -> str:
    """Key the independently selectable surface branch of an ask."""

    encoded = json.dumps(
        {
            "target_ask": target_ask,
            "scenario_mode": scenario_mode,
            "consumer": consumer,
            "query_fields": sorted(query_fields),
            "binding_fields": sorted(binding_fields),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "asksurf-" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def ask_review_target_counts(
    project: Project,
    *,
    scenario_mode: str | None = None,
) -> dict[str, int]:
    """Count live positive ask evidence without performing replay work.

    A target reviewed as a deliberately unanswered standalone question is not
    evidence that its validated-premise scenario has been explored.  Callers
    may therefore keep each generation frontier independent while the default
    remains the historical all-mode count used by ordinary ask generation.
    """

    counts: dict[str, int] = {}
    for review in _live_ask_reviews(project):
        scenario = review.get("ask_scenario")
        if not _is_clean_valid_review(review):
            continue
        if (
            scenario_mode is not None
            and scenario.get("scenario_mode") != scenario_mode
        ):
            continue
        target = scenario.get("target_ask")
        if isinstance(target, str):
            counts[target] = counts.get(target, 0) + 1
    return counts


def validated_premise_rule_usage_counts(project: Project) -> dict[str, int]:
    """Count which premise-rule families have supported validated asks.

    The count is authoring coverage only.  It never changes runtime matching
    or inference.  Older ask reviews already pin their premise rule ids, so
    the frontier can diversify immediately without rewriting the append-only
    ledger or depending on vocabulary-specific sentence text.
    """

    counts: dict[str, int] = {}
    for review in _live_ask_reviews(project):
        scenario = review.get("ask_scenario")
        if (
            not _is_clean_valid_review(review)
            or not isinstance(scenario, dict)
            or scenario.get("scenario_mode") != "validated_premises"
        ):
            continue
        for rule_id in set(scenario.get("premise_rules") or []):
            if isinstance(rule_id, str) and rule_id:
                counts[rule_id] = counts.get(rule_id, 0) + 1
    return counts


def ask_review_consumer_counts(
    project: Project,
    *,
    scenario_mode: str | None = None,
) -> dict[str, int]:
    """Count clean positive reviews by semantic answer consumer."""

    counts: dict[str, int] = {}
    for review in _live_ask_reviews(project):
        scenario = review.get("ask_scenario")
        if not _is_clean_valid_review(review) or not isinstance(scenario, dict):
            continue
        if (
            scenario_mode is not None
            and scenario.get("scenario_mode") != scenario_mode
        ):
            continue
        consumer = scenario.get("consumer")
        if isinstance(consumer, str) and consumer:
            counts[consumer] = counts.get(consumer, 0) + 1
    return counts


def ask_review_surface_counts(project: Project) -> dict[str, int]:
    """Count positive judgments per vocabulary-independent ask branch."""

    counts: dict[str, int] = {}
    for review in _live_ask_reviews(project):
        scenario = review.get("ask_scenario")
        if not _is_clean_valid_review(review):
            continue
        signature = ask_review_surface_signature(
            target_ask=str(scenario.get("target_ask")),
            scenario_mode=str(scenario.get("scenario_mode")),
            consumer=(
                str(scenario["consumer"])
                if scenario.get("consumer") is not None
                else None
            ),
            query_fields=list((scenario.get("query") or {}).keys()),
            binding_fields=list((review.get("requested_bindings") or {}).keys()),
        )
        counts[signature] = counts.get(signature, 0) + 1
    return counts


def _answer_contract(answer: Any) -> dict[str, Any]:
    return {
        "kind": answer.kind,
        "value": _jsonable(answer.value),
        "committed": answer.committed,
        "clarification": answer.clarification is not None,
    }


def _expected_answer_contract(scenario: dict) -> dict[str, Any]:
    answer = scenario.get("answer") or {}
    return {
        "kind": answer.get("kind"),
        "value": answer.get("value"),
        "committed": bool(answer.get("committed")),
        "clarification": scenario.get("answer_shape") == "clarification",
    }


def _reviewed_query_matches(actual: Any, expected: Any) -> bool:
    """Allow a reviewed query to gain evidence-policy metadata only.

    A clean valid review confirms the surface interpretation and result. A
    later safety increment may make that same interpretation stricter by
    adding an ``evidence_*`` constraint. Requiring human re-review merely
    because the machine now records that constraint would flood the action
    inbox, while removing or changing any previously reviewed field must
    still regress exactly as before.
    """

    if actual == expected:
        return True
    if not isinstance(actual, dict) or not isinstance(expected, dict):
        return False
    if any(actual.get(key) != value for key, value in expected.items()):
        return False
    return all(
        key in expected or key.startswith("evidence_")
        for key in actual
    )


def replay_ask_review(project: Project, review: dict) -> dict[str, str]:
    """Replay one pinned positive ask without making reviews runtime inputs."""

    scenario = review.get("ask_scenario")
    if not isinstance(scenario, dict):
        return {"status": "not_applicable", "detail": "not an ask review"}
    question = str(scenario.get("question") or review.get("sentence") or "")
    text = str(scenario.get("text") or question)
    try:
        # Context-dependent asks must be replayed after the ordinary document
        # loop has rebuilt their discourse features. Analyzing the isolated
        # question drops a pronoun's referent group and can make a generic ask
        # appear to supersede the reviewed discourse-specific rule.
        result = solve(text, project.registry, tracing=False)
        reading = result.question or analyze(question, project.registry)
        matched = match_ask(reading, project.registry, store=result.store)
        if matched is None:
            return {
                "status": "regressed",
                "detail": "the reviewed question no longer matches an ask",
            }
        ask, query, _match = matched
        expected_ask = scenario.get("target_ask")
        if ask.id != expected_ask:
            return {
                "status": "regressed",
                "detail": f"{ask.id} now wins instead of {expected_ask}",
            }
        actual_query = _jsonable(query)
        if not _reviewed_query_matches(actual_query, scenario.get("query")):
            return {
                "status": "regressed",
                "detail": "the normalized query changed",
            }
        if _answer_contract(result.answer) != _expected_answer_contract(scenario):
            return {
                "status": "regressed",
                "detail": "the answer or decline contract changed",
            }
    except Exception as exc:  # evidence reporting must not break the Designer
        return {
            "status": "regressed",
            "detail": f"replay failed: {type(exc).__name__}: {exc}",
        }
    status = (
        "current"
        if review.get("registry_fingerprint") == project.registry.fingerprint
        else "machine_reconfirmed"
    )
    return {"status": status, "detail": "exact ask, query, and result replayed"}


def ask_review_evidence(project: Project) -> dict[str, Any]:
    """Fold live ask judgments into compact coverage and replay evidence."""

    cache_key = _evidence_cache_key(project)
    cached = _ASK_EVIDENCE_CACHE.get(cache_key)
    if cached is not None:
        return cached
    reviews = list(_live_ask_reviews(project))
    grouped: dict[str, list[dict]] = {}
    for review in reviews:
        signature = ask_review_signature(review)
        if signature is not None:
            grouped.setdefault(signature, []).append(review)

    groups: list[dict[str, Any]] = []
    for signature, rows in grouped.items():
        scenario = rows[-1]["ask_scenario"]
        valid = [row for row in rows if _is_clean_valid_review(row)]
        canonical = None
        if valid:
            preference = {"preferred": 0, "acceptable": 1, None: 2, "marginal": 3}
            best_preference = min(
                preference.get(row.get("naturalness"), 2) for row in valid
            )
            canonical = max(
                (
                    row
                    for row in valid
                    if preference.get(row.get("naturalness"), 2)
                    == best_preference
                ),
                key=lambda row: str(row.get("timestamp") or ""),
            )
        replay = (
            replay_ask_review(project, canonical)
            if canonical is not None
            else {"status": "unvalidated", "detail": "no valid judgment"}
        )
        groups.append(
            {
                "signature": signature,
                "target_ask": scenario.get("target_ask"),
                "scenario_mode": scenario.get("scenario_mode"),
                "consumer": scenario.get("consumer"),
                "answer_shape": scenario.get("answer_shape"),
                "query_fields": sorted((scenario.get("query") or {}).keys()),
                "binding_fields": sorted(
                    (rows[-1].get("requested_bindings") or {}).keys()
                ),
                "premise_rules": scenario.get("premise_rules") or [],
                "review_count": len(rows),
                "verdict_counts": {
                    verdict: sum(row.get("verdict") == verdict for row in rows)
                    for verdict in ("valid", "invalid", "unclear")
                },
                "naturalness_counts": {
                    value: sum(row.get("naturalness") == value for row in valid)
                    for value in ("preferred", "acceptable", "marginal")
                },
                "canonical_review_id": canonical.get("id") if canonical else None,
                "last_reviewed_at": max(
                    str(row.get("timestamp") or "") for row in rows
                ),
                "replay_status": replay["status"],
                "replay_detail": replay["detail"],
            }
        )
    groups.sort(key=lambda group: (str(group["target_ask"]), group["signature"]))

    target_counts: dict[str, dict[str, int]] = {}
    for group in groups:
        target = str(group["target_ask"])
        counts = target_counts.setdefault(
            target,
            {"groups": 0, "validated_groups": 0, "valid_reviews": 0},
        )
        counts["groups"] += 1
        counts["valid_reviews"] += group["verdict_counts"]["valid"]
        if group["replay_status"] in {"current", "machine_reconfirmed"}:
            counts["validated_groups"] += 1

    result = {
        "summary": {
            "review_count": len(reviews),
            "valid_count": sum(row.get("verdict") == "valid" for row in reviews),
            "clean_valid_count": sum(_is_clean_valid_review(row) for row in reviews),
            "action_count": sum(
                row.get("review_status") != "resolved"
                and review_needs_attention(row)
                for row in reviews
            )
            + sum(group["replay_status"] == "regressed" for group in groups),
            "group_count": len(groups),
            "validated_group_count": sum(
                group["replay_status"] in {"current", "machine_reconfirmed"}
                for group in groups
            ),
            "regressed_group_count": sum(
                group["replay_status"] == "regressed" for group in groups
            ),
            "target_count": len(target_counts),
        },
        "targets": target_counts,
        "groups": groups,
    }
    return _bounded_cache_store(_ASK_EVIDENCE_CACHE, cache_key, result)
