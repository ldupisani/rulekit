"""The designer's API: project browse, doc edit with validation + lint,
trace (the decision stream the stepper replays), and the impact panel.

State model: one Project loaded per server. A doc save re-loads packs from
disk and re-compiles; a compile error is REPORTED and the previous good
registry stays live (a broken registry never serves traces).
"""

from __future__ import annotations

import secrets
import traceback
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ..data.packs import PackError
from ..data.project import Project, load_project
from ..data.registry import CompileError, Registry
from ..data.sources import SourceIndex
from ..kernel.answer import assumption_records
from ..generation import (
    AskScenarioMode,
    GenerationError,
    GenerationMode,
    GenerationObjective,
    HypothesisRecord,
    LexicalRelaxation,
    ReviewRecord,
    ReviewDefect,
    append_exploration,
    append_exploration_failure,
    append_review,
    ask_review_evidence,
    choose_exploration_target,
    delete_review,
    derive_hypotheses,
    generate_candidate,
    generate_ask_scenario,
    generate_minimal_pair,
    exploration_status,
    list_ask_availability,
    list_rule_availability,
    promote_reading_candidate,
    promote_sentence_review_candidate,
    premise_review_evidence,
    read_review_history,
    read_reviews,
    resolve_review,
    retest_candidate,
    update_review,
)
from ..harness.bench import run_suite
from ..generation.reviews import (
    review_attention_reasons, review_needs_attention, review_replay,
)
from ..generation.review_workflow import (
    ReviewWorkflowConflict, UpdatedEvidenceBody, record_updated_evidence,
    retest_saved_review, saved_review,
)
from ..harness.snapshot import diff as snapshot_diff
from ..kernel.engine import solve
from ..kernel.model import PATTERN, Unit, _jsonable
from ..kernel.patterns import match_ask, subsumes
from ..lint.checks import lint_checks
from ..lint.overlap import lint_overlaps


# module-level (not nested in build_router): `from __future__ import
# annotations` stringifies hints and FastAPI resolves them against module
# globals — a locally-scoped model silently degrades to a query param
class DocBody(BaseModel):
    path: str
    content: str


class TraceBody(BaseModel):
    text: str
    interpretation: str | None = None
    reference_year: int | None = Field(default=None, ge=1, le=9999)


class ImpactBody(BaseModel):
    target: str = "suite"  # suite | dev-train | dev-holdout | test
    spend_test_look: bool = False


class GenerationCandidateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str | None = Field(default=None, max_length=256)
    filler_identity: str | None = Field(default=None, max_length=256)
    seed: int | None = None
    generation_mode: GenerationMode = "strict"
    objective: GenerationObjective = "least_attempted_rule"
    filters: list[str] = Field(default_factory=list, max_length=64)


class AskGenerationBody(BaseModel):
    """One exact ask surface and its optional generated evidence scenario."""

    model_config = ConfigDict(extra="forbid")

    ask_id: str | None = Field(default=None, max_length=256)
    seed: int | None = None
    scenario_mode: AskScenarioMode = "ask_only"
    reference_year: int | None = Field(default=None, ge=1, le=9999)
    locked_bindings: dict[str, str] = Field(
        default_factory=dict,
        max_length=64,
    )


class GenerationRetestBody(BaseModel):
    """One pinned candidate re-evaluated after the project reloads."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(min_length=1, max_length=256)
    sentence: str = Field(min_length=1, max_length=2000)
    seed: int
    requested_bindings: dict[str, str] = Field(default_factory=dict)
    attempts: int = Field(default=1, ge=1, le=64)
    origin: Literal["generated", "reading"] = "generated"
    generation_mode: GenerationMode = "strict"
    lexical_relaxations: list[LexicalRelaxation] = Field(
        default_factory=list, max_length=16
    )
    context_before: list[str] = Field(default_factory=list, max_length=8)
    context_after: list[str] = Field(default_factory=list, max_length=8)


class GenerationReadingBody(BaseModel):
    """One Reading sentence, optionally with an explicit matched premise."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str | None = Field(default=None, min_length=1, max_length=256)
    sentence: str = Field(min_length=1, max_length=2000)


class GenerationMinimalPairBody(BaseModel):
    """One controlled reroll with every other slot pinned."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(min_length=1, max_length=256)
    base_seed: int
    original_bindings: dict[str, str] = Field(max_length=64)
    reroll_slot: str = Field(min_length=1, max_length=128)


class GenerationHypothesisBody(GenerationRetestBody):
    """Human-selected defects evaluated against a fresh matcher replay."""

    verdict: Literal["valid", "invalid", "unclear"]
    defects: list[ReviewDefect] = Field(min_length=1, max_length=16)


class ReviewEditBody(BaseModel):
    """A correction. Only the human judgment is editable — the candidate,
    seed and fingerprint stay pinned to what was actually reviewed."""

    model_config = ConfigDict(extra="forbid")

    verdict: Literal["valid", "invalid", "unclear"]
    note: str = Field(default="", max_length=4000)
    hypotheses: list[HypothesisRecord] | None = Field(
        default=None, max_length=32
    )
    interpretation: str | None = Field(default=None, max_length=4000)
    suggested_rule: str | None = Field(default=None, max_length=4000)
    interpretation_judgment: Literal[
        "correct", "incorrect", "unclear", "not_reviewed"
    ] | None = None
    result_judgment: Literal[
        "correct_answer",
        "correct_decline",
        "correct_facts",
        "incorrect",
        "unclear",
        "not_applicable",
        "not_reviewed",
    ] | None = None
    naturalness: Literal["preferred", "acceptable", "marginal"] | None = None


class ReviewResolutionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str = Field(min_length=1, max_length=4000)


class ServerState:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.project: Project = load_project(project_root)
        self.baselines: dict[str, dict] = {}  # target -> snapshot
        import threading

        # one bench run at a time — a second tab must not race the first
        # (and two concurrent TEST looks would double-spend the ledger)
        self.run_lock = threading.Lock()
        # Generation/review I/O is independent from benchmark execution, but
        # two tabs must not interleave JSONL writes.
        self.generation_lock = threading.Lock()

    @property
    def registry(self) -> Registry:
        return self.project.registry

    def reload(self) -> str | None:
        """Re-load from disk; returns an error string (old registry kept)."""
        try:
            self.project = load_project(self.project_root)
            return None
        except (PackError, CompileError, Exception) as exc:  # noqa: BLE001
            return f"{type(exc).__name__}: {exc}"


def _unit_json(unit: Unit) -> dict[str, Any]:
    f = unit.features

    def obligation_target(target: Any) -> Any:
        if target is PATTERN:
            return "<pattern>"
        if isinstance(target, Unit):
            return target.surface
        if isinstance(target, (list, tuple)):
            return [obligation_target(item) for item in target]
        return None

    return {
        "uid": unit.uid,
        "surface": unit.surface,
        "senses": f.get("senses", []),
        "lemma": f.get("lemma"),
        "number": f.get("number"),
        "value": f.get("value"),
        "value_kind": f.get("value_kind"),
        "attributes": f.get("attributes", []),
        "unknown": bool(f.get("unknown")),
        "ambiguous": bool(f.get("ambiguous")),
        "pattern_consumed": bool(f.get("pattern_consumed")),
        "obligations": [
            {
                "role": ob.role,
                "need": ob.need,
                "met": ob.met,
                "optional": ob.optional,
                "target": obligation_target(ob.target),
            }
            for ob in unit.obligations()
        ],
    }


def _identifier_source_json(
    source_index: SourceIndex | None, identifier: str | None
) -> dict[str, Any] | None:
    """Resolve an identified YAML rule or ask through the authoring index."""

    if source_index is None or identifier is None:
        return None
    source = (
        source_index.rules.get(identifier)
        or source_index.asks.get(identifier)
    )
    return source.to_json() if source is not None else None


def _fact_json(
    fact, source_index: SourceIndex | None = None
) -> dict[str, Any]:
    fields = {
        k: _jsonable(v)
        for k, v in fact.__dict__.items()
        if k != "provenance" and v is not None
    }
    payload = {
        "type": type(fact).__name__,
        "fields": fields,
        "source": fact.provenance.source,
        "sentence": fact.provenance.sentence,
    }
    if fact.provenance.assumption:
        payload["scope"] = "question-assumption"
    source_ref = _identifier_source_json(
        source_index, fact.provenance.source
    )
    if source_ref is not None:
        payload["source_ref"] = source_ref
    return payload


def _reading_review_targets(
    results: list[Any],
    registry: Registry,
    source_index: SourceIndex | None = None,
) -> list[dict]:
    """Deduplicate the ordinary matcher results for explicit UI selection."""

    premise_results = [
        result
        for result in results
        if result.match.rule.generation != "safety"
    ]
    targets = []
    for rule_id in sorted(
        {result.match.rule.id for result in premise_results}
    ):
        selected = [
            result
            for result in premise_results
            if result.match.rule.id == rule_id
        ]
        shadowed = all(
            any(
                other is not result
                and subsumes(other.match, result.match, registry)
                for other in premise_results
            )
            for result in selected
        )
        rule = selected[0].match.rule
        target = {
            "rule_id": rule_id,
            "description": rule.description,
            "status": "shadowed" if shadowed else "matched",
        }
        source_ref = _identifier_source_json(source_index, rule_id)
        if source_ref is not None:
            target["source_ref"] = source_ref
        targets.append(target)
    return targets


def _reading_machine_matches(
    results: list[Any],
    registry: Registry,
) -> list[dict[str, Any]]:
    """Exact ordinary premise matches for inspecting rule bindings and overlap."""

    ordinary = [
        result
        for result in results
        if result.match.rule.generation != "safety"
    ]
    return [
        {
            "rule_id": result.match.rule.id,
            "bindings": {
                name: (
                    " ".join(unit.surface for unit in value)
                    if isinstance(value, tuple)
                    else value.surface
                )
                for name, value in sorted(result.match.slots.items())
            },
            "consumed": list(result.match.consumed),
            "shadowed": any(
                other is not result
                and subsumes(other.match, result.match, registry)
                for other in ordinary
            ),
        }
        for result in sorted(
            ordinary,
            key=lambda item: (
                item.match.rule.id,
                item.match.consumed,
                tuple(sorted(item.match.slots)),
            ),
        )
    ]


def _reading_safety_interceptions(
    results: list[Any],
    registry: Registry,
    source_index: SourceIndex | None = None,
) -> list[dict]:
    """Expose only fact-free guards not superseded by an ordinary premise."""

    ordinary = [
        result
        for result in results
        if result.match.rule.generation != "safety"
    ]
    surviving = [
        result
        for result in results
        if result.match.rule.generation == "safety"
        and not any(
            subsumes(other.match, result.match, registry)
            for other in ordinary
        )
    ]
    interceptions = []
    for rule_id in sorted(
        {result.match.rule.id for result in surviving}
    ):
        rule = next(
            result.match.rule
            for result in surviving
            if result.match.rule.id == rule_id
        )
        interception = {
            "rule_id": rule_id,
            "description": rule.description,
            "status": "intercepted",
        }
        source_ref = _identifier_source_json(source_index, rule_id)
        if source_ref is not None:
            interception["source_ref"] = source_ref
        interceptions.append(interception)
    return interceptions


def _decision_json(decision, source_index: SourceIndex) -> dict[str, Any]:
    payload = decision.to_json()
    source_ref = _identifier_source_json(
        source_index, payload.get("rule_id")
    )
    if source_ref is not None:
        payload["source_ref"] = source_ref
    return payload


def _semantic_role(fact) -> str:
    """Classify epistemic origin without changing the FactStore contract."""
    source = fact.provenance.source
    if source.startswith(("knowledge/", "provider/", "reference/")):
        return "knowledge"
    if source.startswith(("synth/", "inference/")):
        return "derived"
    return "observed"


def _semantic_fact_json(
    fact,
    fact_id: str,
    source_index: SourceIndex | None = None,
) -> dict[str, Any]:
    payload = _fact_json(fact, source_index)
    payload.update({
        "id": fact_id,
        "role": _semantic_role(fact),
        # Atom is the deliberately opaque, exact phrase-keyed proposition.
        # Every other fact kind exposes named semantic fields.
        "representation": "exact" if type(fact).__name__ == "Atom" else "structured",
    })
    return payload


def _semantic_node_json(node) -> dict[str, Any]:
    return {"kind": node.kind, "fields": dict(node.fields)}


def _clarification_json(clarification) -> dict[str, Any] | None:
    if clarification is None:
        return None
    return {
        "prompt": clarification.prompt,
        "selected": clarification.selected,
        "options": [
            {
                "id": option.id,
                "label": option.label,
                "description": option.description,
                "query": _semantic_node_json(option.query),
            }
            for option in clarification.options
        ],
    }


def _semantic_json(
    result,
    ask=None,
    source_index: SourceIndex | None = None,
) -> dict[str, Any]:
    """Designer projection of typed facts and structured answer proof.

    This is a view over the result, never a second inference engine. The
    consumer owns proof construction; the server only assigns stable ids to
    its evidence so the UI can cross-link it to the semantic field.
    """
    facts = list(result.store.facts)
    fact_ids = {id(fact): f"f{i}" for i, fact in enumerate(facts)}
    fact_payloads = [
        _semantic_fact_json(fact, fact_ids[id(fact)], source_index)
        for fact in facts
    ]

    answer_proof = result.answer.proof
    clarification = result.answer.clarification
    selected_option = None
    if clarification is not None:
        selected_option = next(
            (
                option
                for option in clarification.options
                if option.id == clarification.selected
            ),
            None,
        )

    if answer_proof is not None:
        query = _semantic_node_json(answer_proof.query)
    elif selected_option is not None:
        query = _semantic_node_json(selected_option.query)
    elif clarification is not None:
        query = {
            "kind": "Ambiguous",
            "fields": {"interpretations": len(clarification.options)},
        }
    elif ask is not None:
        query = {"kind": "Ask", "fields": dict(ask[1])}
    else:
        query = None
    proof = None
    if answer_proof is not None:
        steps = []
        for i, step in enumerate(answer_proof.steps):
            evidence = []
            for fact in step.evidence:
                fact_id = fact_ids.get(id(fact))
                if fact_id is None:
                    # Defensive fallback for a future proof over a fact copied
                    # out of the store: equality is exact for frozen Facts.
                    fact_id = next(
                        (
                            fact_ids[id(candidate)]
                            for candidate in facts
                            if candidate == fact
                        ),
                        None,
                    )
                evidence.append({
                    "id": fact_id,
                    **_fact_json(fact, source_index),
                    "role": _semantic_role(fact),
                    "representation": (
                        "exact" if type(fact).__name__ == "Atom" else "structured"
                    ),
                })
            step_payload = {
                "id": f"p{i}",
                "rule": step.rule,
                "conclusion": _semantic_node_json(step.conclusion),
                "evidence": evidence,
                "detail": step.detail,
            }
            source_ref = _identifier_source_json(source_index, step.rule)
            if source_ref is not None:
                step_payload["source_ref"] = source_ref
            steps.append(step_payload)
        proof = {
            "query": _semantic_node_json(answer_proof.query),
            "steps": steps,
            "status": (
                "proved" if result.answer.committed else "undetermined"
            ),
        }

    return {
        "query": query,
        "interpretations": (
            [
                {
                    "id": option.id,
                    "label": option.label,
                    "description": option.description,
                    "query": _semantic_node_json(option.query),
                    "selected": option.id == clarification.selected,
                }
                for option in clarification.options
            ]
            if clarification is not None else []
        ),
        "facts": fact_payloads,
        "proof": proof,
        "roles": {
            "observed": "asserted by a reader from a source sentence",
            "knowledge": "supplied by an explicitly enabled knowledge source",
            "derived": "produced by a named inference from other facts",
        },
    }


def _observation_json(obs) -> dict[str, Any]:
    """One deictic resolution: who asked, from where, over what, and what happened.

    This is the channel that records what the engine THREW AWAY. A decline mutates
    nothing, so it is invisible to the Decision trace — but the declines are where all
    the information is.
    """
    return {
        "source": obs.source,  # shares vocabulary with fact.source AND decision.kind
        "dimension": obs.dimension,
        "metric": obs.metric,
        "round": obs.round,
        "attempts": obs.attempts,
        "origo": {
            "sentence": obs.origo.sentence,
            "span": list(obs.origo.span) if obs.origo.span else None,
            "moment": obs.origo.moment,  # always null — the temporal origo is unbuilt
            "locus": obs.origo.locus,  # always null — the spatial origo is unbuilt
        },
        "filters": list(obs.filters),
        "candidates": [
            {
                "key": c.key,
                "dimension": c.dimension,
                # null whenever the candidate genuinely has no coordinate. Most sites
                # resolve over bare measure/entity strings; the viewer must draw those
                # unanchored rather than invent a position for them.
                "sentence": c.sentence,
                "span": list(c.span) if c.span else None,
                "ref": f"unit:{c.uid}" if c.uid is not None else None,
                "data_uid": (
                    f"{c.sentence}:{c.uid}"
                    if c.uid is not None and c.sentence is not None
                    else None
                ),
                "distance": c.distance,
                "eliminated_by": c.eliminated_by,
            }
            for c in obs.candidates
        ],
        "outcome": obs.outcome,
        "winner": obs.winner,
        "arbitration": obs.arbitration,
        "reason": obs.reason,
    }


def _field_json(result) -> dict[str, Any]:
    """The deictic field itself: what coordinates EXIST, per dimension.

    A pure projection of the Result — no kernel machinery. Each axis reports its own
    degeneracy honestly, because three of the four are degenerate and a viewer that
    hid that would be drawing a field the engine does not have.
    """
    readings = result.premises + ([result.question] if result.question else [])
    quantities = [
        f for f in result.store.facts if type(f).__name__ == "Quantity"
    ]
    event_times = [
        f for f in result.store.facts if type(f).__name__ == "EventTime"
    ]
    before = [f for f in result.store.facts if type(f).__name__ == "Before"]

    # PERSON — the only axis with true positional coordinates. This is also where the
    # capitalisation heuristic dumps any capitalised mid-sentence word that is not
    # timeperiod-exempt, so a month can appear here as a rival person (deixis.md §4).
    person = [
        {
            "key": u.features.get("lemma", u.features.get("fold")),
            "surface": u.surface,
            "uid": u.uid,
            "sentence": r.sentence_index,
            "span": list(u.span),
            "data_uid": f"{r.sentence_index}:{u.uid}",
        }
        for r in readings
        for u in r.units
        if u.sense() == "name"
    ]

    # DISCOURSE — measures and entities are bare strings. Their ONLY coordinate is the
    # sentence their facts came from, so they render as sentence BANDS, never spans.
    def _bands(attr: str) -> list[dict[str, Any]]:
        bands: dict[str, set[int]] = {}
        for q in quantities:
            key = getattr(q, attr, None)
            if key is None:
                continue
            bands.setdefault(str(key), set()).add(q.provenance.sentence)
        return [
            {"key": k, "sentences": sorted(v)} for k, v in sorted(bands.items())
        ]

    # TIME has two deliberately separate representations. Quantity.time remains an
    # opaque surface label used only for equality. EventTime carries a pack-declared
    # signed relative coordinate; Before records every strict pair supported by those
    # coordinates. Never infer an order for the opaque labels.
    time_labels = sorted({q.time for q in quantities if getattr(q, "time", None)})
    ordered_events = [
        {
            "event": fact.event,
            "entity": fact.entity,
            "verb": fact.verb,
            "object": fact.obj,
            "marker": fact.marker,
            "offset": fact.offset,
            "sentence": fact.provenance.sentence,
        }
        for fact in sorted(
            event_times,
            key=lambda item: (item.offset, item.provenance.sentence, item.event),
        )
    ]

    return {
        "narrative": [
            {
                "sentence": r.sentence_index,
                "is_question": result.question is r,
                "text": r.text,
            }
            for r in readings
        ],
        "person": {"candidates": person},
        "discourse": {
            "measures": _bands("measure"),
            "entities": _bands("entity"),
        },
        "time": {
            "labels": time_labels,
            "events": ordered_events,
            "before": [
                {"earlier": fact.earlier, "later": fact.later}
                for fact in before
            ],
            "ordered": bool(ordered_events),
            "note": (
                "relative event markers use pack-declared signed offsets and preserve "
                "strict event order. Quantity time labels remain opaque and are never "
                "placed on this axis; asks still cannot name a reference moment."
                if ordered_events
                else "no ordered relative event marker was preserved. Quantity time "
                "labels remain opaque and are used only for equality."
            ),
        },
        "place": {
            "loci": [],
            "note": (
                "the spatial origo is unbuilt: prepositions are matched and discarded, "
                "and a container is an entity string indistinguishable from a person "
                "(docs/deixis.md §1.4, phase 4)."
            ),
        },
    }


def pack_documents(project) -> list[dict]:
    """THE editable document set — the one definition the UI listing and the
    read/write allowlist both use.

    Never cached: `ServerState.reload()` can change the pack set, and an
    allowlist that outlived a reload would be a stale authority.
    """
    docs = []
    for pack in project.packs:
        root = pack.root.resolve()
        for path in sorted(pack.root.rglob("*.yaml")):
            # A SYMLINK OUT OF THE PACK IS NOT A PACK DOCUMENT. `rglob` happily
            # lists one, and because the request side resolves too, both would
            # resolve to the same target and membership would pass — so
            # resolve-and-compare alone does NOT contain the tree. A link
            # planted in a pack (deliberately or as a convenience) pointing at
            # `../../data/test.parquet` would otherwise expose TEST golds
            # through an allowlisted name.
            #
            # Membership guards the REQUEST; containment guards the LIST. Both,
            # and each does a job the other cannot.
            if not path.resolve().is_relative_to(root):
                continue
            docs.append({
                "pack": pack.name,
                "path": str(path),
                "name": str(path.relative_to(pack.root)),
            })
    return docs


def resolve_editable_doc(raw: str, project) -> Path | None:
    """The editable path for `raw`, or None if it is out of bounds.

    ⚠ THIS IS A FIREWALL BOUNDARY, not a convenience check, and it is a pure
    function so it can be tested without an HTTP stack — an unrunnable check on
    a boundary is no check.

    The previous version admitted anything under a pack root OR under the
    PROJECT root, and that second disjunct is the whole project directory —
    including `data/` (the DEV/TEST parquet) and `snapshots/`. The designer
    could therefore READ TEST items and OVERWRITE datasets and baselines over
    HTTP, defeating the DEV/TEST firewall `docs/methodology.md` is built around
    and putting silent corruption of a baseline one request away.

    Now it is an ALLOWLIST of exactly the pack YAML documents the UI is offered,
    compared on RESOLVED paths so a symlink out of the tree resolves to
    something not on the list. MEMBERSHIP, not containment: `..` traversal, a
    dataset, a snapshot, `project.yaml`, a non-YAML file inside a pack, and any
    not-yet-existing path all fail it.

    This costs the UI nothing: `app.js` only ever opens a path handed to it by
    `/api/project`, which is this same set.
    """
    path = Path(raw).resolve()
    allowed = {Path(d["path"]).resolve() for d in pack_documents(project)}
    return path if path in allowed else None


def trace_project(project: Project, body: TraceBody) -> dict[str, Any]:
    """Run the ordinary Designer trace for reading and review inspection."""

    registry = project.registry
    source_index = project.source_index
    try:
        result = solve(
            body.text,
            registry,
            interpretation=body.interpretation,
            reference_year=body.reference_year,
        )
    except Exception as exc:  # noqa: BLE001 — surface, don't 500
        return {
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc()[-2000:],
        }
    readings = result.premises + ([result.question] if result.question else [])
    ask = match_ask(result.question, registry, store=result.store) if result.question else None
    return {
        "error": None,
        "answer": {
            "kind": result.answer.kind,
            "value": result.answer.value,
            "reason": result.answer.reason,
            "committed": result.answer.committed,
            "clarification": _clarification_json(result.answer.clarification),
            "assumptions": assumption_records(result.answer),
        },
        "rounds": result.document.rounds if result.document else 1,
        "ask": (
            {
                "id": ask[0].id,
                "query": (
                    {
                        key: value
                        for key, value in ask[1].items()
                        if not key.startswith("__")
                    }
                    or None
                ),
                "source_ref": _identifier_source_json(source_index, ask[0].id),
            }
            if ask is not None
            else None
        ),
        "sentences": [
            {
                "index": reading.sentence_index,
                "text": reading.text,
                "is_question": result.question is reading,
                **(
                    {"scope": "question-assumption"}
                    if reading.assumption
                    else {}
                ),
                "units": [_unit_json(unit) for unit in reading.units],
                "decisions": [
                    _decision_json(decision, source_index)
                    for decision in reading.decisions
                ],
                "review_targets": (
                    []
                    if result.question is reading or result.document is None
                    else _reading_review_targets(
                        result.document.rule_results.get(
                            reading.sentence_index,
                            [],
                        ),
                        registry,
                        source_index,
                    )
                ),
                "machine_matches": (
                    []
                    if result.question is reading or result.document is None
                    else _reading_machine_matches(
                        result.document.rule_results.get(
                            reading.sentence_index,
                            [],
                        ),
                        registry,
                    )
                ),
                "safety_interceptions": (
                    []
                    if result.question is reading or result.document is None
                    else _reading_safety_interceptions(
                        result.document.rule_results.get(
                            reading.sentence_index,
                            [],
                        ),
                        registry,
                        source_index,
                    )
                ),
            }
            for reading in readings
        ],
        "facts": [_fact_json(fact, source_index) for fact in result.store.facts],
        "semantic": _semantic_json(result, ask, source_index),
        "collisions": [
            {
                "key": _jsonable(list(collision.key)),
                "a": collision.a_source,
                "b": collision.b_source,
                "a_value": _jsonable(collision.a_value),
                "b_value": _jsonable(collision.b_value),
            }
            for collision in result.store.collisions
        ],
        "agreement_ambiguities": [
            event.to_trace_event()
            for event in result.store.agreement_ambiguities
        ],
        "gaps": (
            [gap.describe() for gap in result.document.gaps]
            if result.document
            else []
        ),
        "deficiencies": result.deficiencies(),
        "deixis": {
            "observations": (
                [
                    _observation_json(observation)
                    for observation in result.log.journal.observations
                ]
                if result.log.journal is not None
                else []
            ),
            "field": _field_json(result),
        },
    }


def build_router(state: ServerState) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/project")
    def project_info():
        docs = pack_documents(state.project)
        source_index = state.project.source_index
        sources = {}
        if source_index is not None:
            sources = {
                identifier: source.to_json()
                for identifier, source in {
                    **source_index.rules,
                    **source_index.asks,
                }.items()
            }
        return {
            "name": state.project.doc.name,
            "packs": [p.name for p in state.project.packs],
            "fingerprint": state.registry.fingerprint[:16],
            "registry_fingerprint": state.registry.fingerprint,
            "docs": docs,
            "has_suite": bool(state.project.doc.suite),
            "has_datasets": bool(state.project.doc.datasets),
            "impact_targets": (
                (["suite"] if state.project.doc.suite else [])
                + (["dev-train", "dev-holdout", "test"]
                   if state.project.doc.datasets else [])
            ),
            "rules": [r.id for r in state.registry.rules],
            "asks": [a.id for a in state.registry.asks],
            "sources": sources,
        }

    def _resolve_doc_path(raw: str) -> Path:
        path = resolve_editable_doc(raw, state.project)
        if path is None:
            raise HTTPException(403, "not an editable pack document")
        return path

    @router.get("/doc")
    def read_doc(path: str):
        p = _resolve_doc_path(path)
        if not p.exists():
            raise HTTPException(404, f"{path} not found")
        return {"path": path, "content": p.read_text()}

    @router.put("/doc")
    def write_doc(body: DocBody):
        p = _resolve_doc_path(body.path)
        previous = p.read_text() if p.exists() else None
        p.write_text(body.content)
        error = state.reload()
        if error is not None:
            # roll back the file so the on-disk state matches the live registry
            if previous is not None:
                p.write_text(previous)
            else:
                p.unlink(missing_ok=True)
            state.reload()
            return {"ok": False, "error": error, "lint": []}
        findings = lint_overlaps(state.registry) + lint_checks(state.registry)
        return {
            "ok": True,
            "error": None,
            "fingerprint": state.registry.fingerprint[:16],
            "lint": [
                {"level": f.level, "code": f.code, "message": f.message}
                for f in findings
                if f.level != "info"
            ],
        }

    @router.post("/trace")
    def trace(body: TraceBody):
        return trace_project(state.project, body)

    def _target_items(target: str) -> list[dict] | None:
        if target == "suite":
            return state.project.suite_items() or None
        if state.project.doc.datasets:
            return state.project.dataset_items(target)
        return None

    @router.post("/impact")
    def impact(body: ImpactBody):
        """The firewall, enforced in the tool itself:
        - suite / dev-train: fully inspectable (per-item outcomes returned)
        - dev-holdout: a DELTA GATE — bucket counts + opaque item ids only
        - test: aggregates only, requires spend_test_look, lands in the ledger
        """
        target = body.target
        if target == "test" and not body.spend_test_look:
            return {"error": "TEST is one-look and aggregate-only — tick "
                             "'spend the TEST look' to spend it (ledgered)"}
        try:
            items = _target_items(target)
        except ValueError as exc:
            return {"error": str(exc)}
        if not items:
            return {"error": f"no items for target {target!r}"}

        if not state.run_lock.acquire(blocking=False):
            return {"error": "a bench run is already in progress — wait for it to finish"}
        try:
            report = run_suite(items, state.registry)
        finally:
            state.run_lock.release()
        snapshot = report.to_snapshot()
        inspectable = target in ("suite", "dev-train")

        if target == "test":
            from ..harness.firewall import record_test_look

            record_test_look(
                state.project.snapshots_dir / "test-ledger.jsonl",
                state.registry.fingerprint, report.aggregates(),
            )
            return {
                "error": None, "target": target,
                "aggregates": report.aggregates(),
                "items": None, "diff": None,
                "note": "TEST look SPENT and recorded in snapshots/test-ledger.jsonl "
                        "— a precision drop vs your last look means REVERT",
            }

        d = None
        baseline = state.baselines.get(target)
        if baseline is not None:
            dd = snapshot_diff(baseline, snapshot)
            d = {
                "solved": dd.solved, "broke": dd.broke,
                "decl_to_wrong": dd.decl_to_wrong, "wrong_to_decl": dd.wrong_to_decl,
                "verdict": dd.verdict(),
            }
        return {
            "error": None,
            "target": target,
            "aggregates": report.aggregates(),
            "items": (
                {
                    r.id: {"outcome": r.outcome, "expected": _jsonable(r.expected),
                           "got": _jsonable(r.got), "reason": r.reason[:120]}
                    for r in report.results
                    if r.outcome in ("wrong", "errored") or target == "suite"
                }
                if inspectable else None
            ),
            "diff": d,
            "has_baseline": baseline is not None,
            "note": None if inspectable else
                    "dev-holdout is a delta gate: buckets only, ids are opaque "
                    "— diagnose classes on dev-train, never tune to these items",
        }

    @router.post("/baseline")
    def set_baseline(body: ImpactBody):
        if body.target == "test":
            return {"error": "TEST has no baseline — the ledger is its history"}
        try:
            items = _target_items(body.target)
        except ValueError as exc:
            return {"error": str(exc)}
        if not items:
            return {"error": f"no items for target {body.target!r}"}
        if not state.run_lock.acquire(blocking=False):
            return {"error": "a bench run is already in progress — wait for it to finish"}
        try:
            report = run_suite(items, state.registry)
        finally:
            state.run_lock.release()
        state.baselines[body.target] = report.to_snapshot()
        return {"error": None, "target": body.target, "aggregates": report.aggregates()}

    @router.get("/lint")
    def lint():
        findings = lint_overlaps(state.registry) + lint_checks(state.registry)
        return [
            {"level": f.level, "code": f.code, "message": f.message}
            for f in findings
        ]

    @router.get("/generation/rules")
    def generation_rules():
        try:
            rules = list_rule_availability(state.project)
        except GenerationError as exc:
            raise HTTPException(422, str(exc)) from exc
        premise_rules = [rule for rule in rules if rule.generation != "safety"]
        safety_rules = [rule for rule in rules if rule.generation == "safety"]
        return {
            "rules": [rule.to_json() for rule in premise_rules],
            "safety_rules": [rule.to_json() for rule in safety_rules],
            "supported": sum(rule.supported for rule in premise_rules),
            "total": len(premise_rules),
            "safety_total": len(safety_rules),
        }

    @router.get("/generation/asks")
    def generation_asks():
        try:
            asks = list_ask_availability(state.project)
            evidence = ask_review_evidence(state.project)
        except GenerationError as exc:
            raise HTTPException(422, str(exc)) from exc
        target_counts = evidence["targets"]
        return {
            "asks": [
                {
                    **ask.to_json(),
                    **target_counts.get(
                        ask.id,
                        {"groups": 0, "validated_groups": 0, "valid_reviews": 0},
                    ),
                }
                for ask in asks
            ],
            "supported": sum(ask.supported for ask in asks),
            "total": len(asks),
            "evidence": evidence["summary"],
        }

    @router.post("/generation/ask")
    def generation_ask(body: AskGenerationBody):
        seed = secrets.randbits(53) if body.seed is None else body.seed
        with state.generation_lock:
            try:
                candidate = generate_ask_scenario(
                    state.project,
                    ask_id=body.ask_id,
                    seed=seed,
                    scenario_mode=body.scenario_mode,
                    reference_year=body.reference_year,
                    locked_bindings=body.locked_bindings,
                )
            except GenerationError as exc:
                raise HTTPException(422, str(exc)) from exc
        return candidate.to_json()

    @router.get("/generation/exploration")
    def generation_exploration():
        with state.generation_lock:
            try:
                return exploration_status(
                    state.project,
                    include_placements=False,
                )
            except GenerationError as exc:
                raise HTTPException(422, str(exc)) from exc

    @router.post("/generation/candidate")
    def generation_candidate(body: GenerationCandidateBody):
        seed = secrets.randbits(53) if body.seed is None else body.seed
        with state.generation_lock:
            selection = None
            event = None
            try:
                if body.generation_mode == "strict":
                    selection = choose_exploration_target(
                        state.project,
                        rule_id=body.rule_id,
                        filler_identity=body.filler_identity,
                        seed=seed,
                        objective=body.objective,
                        filters=tuple(body.filters),
                    )
                    candidate = generate_candidate(
                        state.project,
                        rule_id=selection.rule_id,
                        seed=seed,
                        locked_bindings=selection.locked_bindings,
                        generation_mode="strict",
                        structural_target=selection.target_signature,
                    )
                    event = append_exploration(
                        state.project, candidate, selection
                    )
                elif body.generation_mode == "lexical_boundary":
                    if body.filler_identity is not None:
                        raise GenerationError(
                            "focused lexicon probes are strict-mode coverage; "
                            "clear the probe before using lexical boundary mode"
                        )
                    if body.filters or body.objective != "least_attempted_rule":
                        raise GenerationError(
                            "structural objectives and filters apply to strict "
                            "coverage; clear them before using lexical boundary "
                            "mode"
                        )
                    candidate = generate_candidate(
                        state.project,
                        rule_id=body.rule_id,
                        seed=seed,
                        generation_mode="lexical_boundary",
                    )
                else:
                    if body.filler_identity is not None or body.filters:
                        raise GenerationError(
                            "safety-boundary generation does not use premise "
                            "lexicon probes or structural filters"
                        )
                    candidate = generate_candidate(
                        state.project,
                        rule_id=body.rule_id,
                        seed=seed,
                        generation_mode="safety_boundary",
                    )
            except GenerationError as exc:
                if selection is not None and body.generation_mode == "strict":
                    append_exploration_failure(
                        state.project,
                        selection,
                        seed=seed,
                        error=str(exc),
                    )
                raise HTTPException(422, str(exc)) from exc
        return {
            **candidate.to_json(),
            "exploration_event_id": event["id"] if event is not None else None,
            "exploration_probe": (
                selection.probe if selection is not None else None
            ),
            "exploration_objective": (
                selection.objective if selection is not None else None
            ),
            "exploration_filters": (
                list(selection.filters) if selection is not None else []
            ),
            "exploration_target_signature": (
                selection.target_signature if selection is not None else None
            ),
            "structural_signatures": (
                event["structural_signatures"] if event is not None else []
            ),
        }

    @router.post("/generation/from-reading")
    def generation_from_reading(body: GenerationReadingBody):
        try:
            candidate = (
                promote_reading_candidate(
                    state.project,
                    rule_id=body.rule_id,
                    sentence=body.sentence,
                )
                if body.rule_id is not None
                else promote_sentence_review_candidate(
                    state.project,
                    sentence=body.sentence,
                )
            )
        except GenerationError as exc:
            raise HTTPException(422, str(exc)) from exc
        return candidate.to_json()

    @router.post("/generation/retest")
    def generation_retest(body: GenerationRetestBody):
        try:
            candidate = retest_candidate(
                state.project,
                rule_id=body.rule_id,
                sentence=body.sentence,
                seed=body.seed,
                requested_bindings=body.requested_bindings,
                attempts=body.attempts,
                origin=body.origin,
                generation_mode=body.generation_mode,
                lexical_relaxations=tuple(body.lexical_relaxations),
                context_before=tuple(body.context_before),
                context_after=tuple(body.context_after),
            )
        except GenerationError as exc:
            raise HTTPException(422, str(exc)) from exc
        return candidate.to_json()

    @router.post("/generation/minimal-pair")
    def generation_minimal_pair(body: GenerationMinimalPairBody):
        with state.generation_lock:
            try:
                candidate = generate_minimal_pair(
                    state.project,
                    rule_id=body.rule_id,
                    base_seed=body.base_seed,
                    original_bindings=body.original_bindings,
                    reroll_slot=body.reroll_slot,
                )
                event = append_exploration(state.project, candidate)
            except GenerationError as exc:
                raise HTTPException(422, str(exc)) from exc
        return {
            "reroll_slot": body.reroll_slot,
            "locked_bindings": {
                slot: surface
                for slot, surface in body.original_bindings.items()
                if slot != body.reroll_slot
            },
            "candidate": candidate.to_json(),
            "exploration_event_id": event["id"],
        }

    @router.post("/generation/hypotheses")
    def generation_hypotheses(body: GenerationHypothesisBody):
        try:
            candidate = retest_candidate(
                state.project,
                rule_id=body.rule_id,
                sentence=body.sentence,
                seed=body.seed,
                requested_bindings=body.requested_bindings,
                attempts=body.attempts,
                origin=body.origin,
                generation_mode=body.generation_mode,
                lexical_relaxations=tuple(body.lexical_relaxations),
                context_before=tuple(body.context_before),
                context_after=tuple(body.context_after),
            )
        except GenerationError as exc:
            raise HTTPException(422, str(exc)) from exc
        hypotheses = derive_hypotheses(
            candidate,
            verdict=body.verdict,
            defects=body.defects,
        )
        return {
            "candidate": candidate.to_json(),
            "hypotheses": [
                hypothesis.model_dump() for hypothesis in hypotheses
            ],
            "detail": (
                None
                if hypotheses
                else (
                    "No mechanical hypothesis is available for the selected "
                    "defect and current matcher evidence."
                )
            ),
        }

    @router.post("/generation/review")
    def generation_review(body: ReviewRecord):
        with state.generation_lock:
            record = append_review(state.project, body)
        return {"ok": True, "review": record}

    @router.get("/generation/history")
    def generation_history(
        limit: int = 100,
        offset: int = 0,
        view: Literal["attention", "archive"] = "archive",
    ):
        bounded = max(1, min(limit, 500))
        start = max(0, offset)
        with state.generation_lock:
            history = read_review_history(state.project, 100_000)
            evidence = ask_review_evidence(state.project)
            premise_evidence = premise_review_evidence(state.project)
        regressions = {
            group["canonical_review_id"]: group["replay_detail"]
            for group in evidence["groups"] + premise_evidence["groups"]
            if group["replay_status"] == "regressed"
        }
        # Coverage may choose another healthy exemplar. Check each positive
        # independently so that no regressed issue is hidden by that choice.
        for review in history:
            if review.get("verdict") == "valid" and not review_needs_attention(review):
                replay = review_replay(state.project, review)
                if replay["status"] == "regressed":
                    regressions[review["id"]] = replay["detail"]
        for review in history:
            review["attention_reasons"] = review_attention_reasons(review)
            if review["id"] in regressions:
                review["attention_reasons"].append({
                    "code": "regressed", "source": "current_replay",
                    "detail": regressions[review["id"]],
                })
        if view == "attention":
            history = [
                review
                for review in history
                if review.get("review_status") != "resolved"
                and review["attention_reasons"]
            ]
        page = history[start : start + bounded]
        for review in page:
            target = review.get("target_rule")
            if target is None and isinstance(review.get("ask_scenario"), dict):
                target = review["ask_scenario"].get("target_ask")
            source_ref = _identifier_source_json(
                state.project.source_index,
                target,
            )
            if source_ref is not None:
                review["source_ref"] = source_ref
        return {
            "reviews": page,
            "total": len(history),
            "offset": start,
            "limit": bounded,
        }

    @router.get("/generation/review-evidence")
    def generation_review_evidence():
        with state.generation_lock:
            ask_evidence = ask_review_evidence(state.project)
            premise_evidence = premise_review_evidence(state.project)
        return {
            **ask_evidence,
            "ask_summary": ask_evidence["summary"],
            "premise_summary": premise_evidence["summary"],
            "premise_targets": premise_evidence["targets"],
            "premise_groups": premise_evidence["groups"],
        }

    @router.patch("/generation/review/{review_id}")
    def generation_review_edit(review_id: str, body: ReviewEditBody):
        # a correction APPENDS; the superseded record stays on disk
        with state.generation_lock:
            try:
                record = update_review(
                    state.project,
                    review_id,
                    body.verdict,
                    body.note,
                    body.hypotheses,
                    body.interpretation,
                    body.suggested_rule,
                    body.interpretation_judgment,
                    body.result_judgment,
                    body.naturalness,
                    "naturalness" in body.model_fields_set,
                )
            except KeyError as exc:
                raise HTTPException(404, f"no live review {review_id}") from exc
        return {"ok": True, "review": record}

    def _review_action(call):
        with state.generation_lock:
            try:
                return call()
            except KeyError as exc:
                raise HTTPException(404, "Review changed or was excluded; reload the review history.") from exc
            except ReviewWorkflowConflict as exc:
                raise HTTPException(409, str(exc)) from exc
            except (GenerationError, ValueError) as exc:
                raise HTTPException(422, str(exc)) from exc

    @router.post("/generation/review/{review_id}/retest")
    def generation_review_retest(review_id: str):
        return _review_action(lambda: retest_saved_review(state.project, review_id))

    @router.post("/generation/review/{review_id}/evidence")
    def generation_review_updated_evidence(review_id: str, body: UpdatedEvidenceBody):
        record = _review_action(lambda: record_updated_evidence(state.project, review_id, body))
        return {"ok": True, "review": record}

    @router.post("/generation/review/{review_id}/resolve")
    def generation_review_resolve(review_id: str, body: ReviewResolutionBody):
        def close_review():
            review = saved_review(state.project, review_id)
            if review["review_status"] == "resolved":
                raise ReviewWorkflowConflict("This review is already resolved.")
            if not body.note.strip():
                raise ValueError("Describe why this issue can be closed.")
            return resolve_review(state.project, review_id, body.note.strip())
        return {"ok": True, "review": _review_action(close_review)}

    @router.delete("/generation/review/{review_id}")
    def generation_review_delete(review_id: str):
        # a delete APPENDS a tombstone; nothing is removed from the ledger
        with state.generation_lock:
            try:
                record = delete_review(state.project, review_id)
            except KeyError as exc:
                raise HTTPException(404, f"no live review {review_id}") from exc
        return {"ok": True, "tombstone": record}

    return router
