"""Designer-only generation observations and exploration status.

Successful fresh realizations and failed fresh attempts use separate
append-only ledgers. Neither contains human judgments, and runtime reading,
matching, inference, and benchmarks never import them.
"""

from __future__ import annotations

import json
import random
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..data.project import Project
from .candidate import GenerationCandidate
from .reviews import SourceLocation, read_reviews
from .sample import (
    GenerationError,
    _absent_categories,
    _distinct_measure_groups,
    _domain,
    _flat_sentence,
    _leaf_tokens,
    _load_fixtures,
    _measure_assignment_exists,
    _outside_categories,
    _outside_slot_categories,
    _slot_category_exclusions,
    _unbound_optional_paths,
    list_rule_availability,
)


class ExplorationFiller(BaseModel):
    """One lexicon-backed filler used by a successful realization."""

    model_config = ConfigDict(extra="forbid")

    slot: str = Field(min_length=1, max_length=128)
    token_index: int = Field(ge=0, le=1024)
    identity: str = Field(min_length=1, max_length=256)
    surface: str = Field(min_length=1, max_length=512)
    source: SourceLocation


class ExplorationEvent(BaseModel):
    """The bounded durable shape of one fresh generation observation."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1, max_length=128)
    rule_id: str = Field(min_length=1, max_length=256)
    seed: int
    registry_fingerprint: str = Field(min_length=8, max_length=128)
    fillers: list[ExplorationFiller] = Field(default_factory=list, max_length=64)


class DurableExplorationEvent(ExplorationEvent):
    """An observation after server-owned identity and time are attached."""

    id: str = Field(pattern=r"^exp-[0-9a-f]{16}$")
    project: str = Field(min_length=1, max_length=256)
    timestamp: str = Field(min_length=20, max_length=64)


class ExplorationFailure(BaseModel):
    """The bounded durable input for one unsuccessful fresh attempt."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(min_length=1, max_length=256)
    seed: int
    registry_fingerprint: str = Field(min_length=8, max_length=128)
    probe: ExplorationFiller | None = None
    error: str = Field(min_length=1, max_length=4000)


class DurableExplorationFailure(ExplorationFailure):
    """A failed attempt after server-owned identity and time are attached."""

    id: str = Field(pattern=r"^fail-[0-9a-f]{16}$")
    project: str = Field(min_length=1, max_length=256)
    timestamp: str = Field(min_length=20, max_length=64)


@dataclass(frozen=True)
class ProbePlacement:
    """One rule slot through which a lexicon identity can be realized."""

    rule_id: str
    slot: str
    token_index: int
    identity: str
    surfaces: tuple[str, ...]


@dataclass(frozen=True)
class ExplorationSelection:
    """A deterministic least-explored rule and optional lexical probe."""

    rule_id: str
    locked_bindings: dict[str, str]
    probe: dict[str, Any] | None


def exploration_path(project: Project) -> Path:
    """The one durable event path; callers cannot supply another."""

    return project.root / "generation" / "exploration.jsonl"


def exploration_failure_path(project: Project) -> Path:
    """The fixed failed-attempt path; callers cannot supply another."""

    return project.root / "generation" / "failures.jsonl"


def _probe_catalog(project: Project) -> tuple[ProbePlacement, ...]:
    fixtures = _load_fixtures(project.root)
    supported = {
        item.id for item in list_rule_availability(project) if item.supported
    }
    surfaces: dict[tuple[str, str, int, str], set[str]] = defaultdict(set)
    for rule in project.registry.rules:
        if rule.id not in supported:
            continue
        absent_categories = _absent_categories(rule)
        slot_category_exclusions = _slot_category_exclusions(rule)
        seq = _flat_sentence(rule) or []
        unbound_optional_paths = _unbound_optional_paths(rule, seq)
        distinct_measure_groups = _distinct_measure_groups(rule)
        tokens_by_slot = {
            token.slot: token
            for _, token, _ in _leaf_tokens(seq)
            if token.slot is not None
        }
        measure_slots = {
            name for group in distinct_measure_groups for name in group
        }
        measure_domains = {
            name: [
                filler
                for filler in _domain(
                    tokens_by_slot[name], project.registry, fixtures
                )
                if _outside_categories(
                    filler, absent_categories, project.registry
                )
                and _outside_slot_categories(
                    filler,
                    name,
                    slot_category_exclusions,
                    project.registry,
                )
            ]
            for name in measure_slots
            if name in tokens_by_slot
        }
        for token_index, (_, token, optional_ancestors) in enumerate(
            _leaf_tokens(seq)
        ):
            if (
                token.slot is None
                or any(
                    ancestor in unbound_optional_paths
                    for ancestor in optional_ancestors
                )
            ):
                continue
            for filler in _domain(token, project.registry, fixtures):
                if (
                    _outside_categories(
                        filler, absent_categories, project.registry
                    )
                    and _outside_slot_categories(
                        filler,
                        token.slot,
                        slot_category_exclusions,
                        project.registry,
                    )
                    and (
                        token.slot not in measure_slots
                        or _measure_assignment_exists(
                            distinct_measure_groups,
                            measure_domains,
                            {token.slot: filler},
                        )
                    )
                    and
                    filler.identity in project.registry.lexicon
                    and filler.identity in project.source_index.lexicon
                ):
                    surfaces[
                        (rule.id, token.slot, token_index, filler.identity)
                    ].add(filler.surface)
    return tuple(
        ProbePlacement(
            rule_id=rule_id,
            slot=slot,
            token_index=token_index,
            identity=identity,
            surfaces=tuple(sorted(values, key=lambda value: value.casefold())),
        )
        for (rule_id, slot, token_index, identity), values in sorted(
            surfaces.items()
        )
    )


def _candidate_fillers(
    project: Project, candidate: GenerationCandidate
) -> list[ExplorationFiller]:
    fixtures = _load_fixtures(project.root)
    rule = next(
        (
            item
            for item in project.registry.rules
            if item.id == candidate.target_rule
        ),
        None,
    )
    if rule is None:
        return []
    fillers: list[ExplorationFiller] = []
    seen: set[tuple[str, int, str, str]] = set()
    for token_index, (_, token, _) in enumerate(
        _leaf_tokens(_flat_sentence(rule) or [])
    ):
        if token.slot is None:
            continue
        surface = candidate.requested_bindings.get(token.slot)
        if surface is None:
            continue
        match = next(
            (
                filler
                for filler in _domain(token, project.registry, fixtures)
                if filler.surface.casefold() == surface.casefold()
            ),
            None,
        )
        if match is None or match.identity not in project.registry.lexicon:
            continue
        source = project.source_index.lexicon.get(match.identity)
        if source is None:
            continue
        key = (token.slot, token_index, match.identity, match.surface.casefold())
        if key in seen:
            continue
        seen.add(key)
        fillers.append(
            ExplorationFiller(
                slot=token.slot,
                token_index=token_index,
                identity=match.identity,
                surface=match.surface,
                source=SourceLocation.model_validate(source.to_json()),
            )
        )
    return fillers


def append_exploration(
    project: Project, candidate: GenerationCandidate
) -> dict[str, Any]:
    """Append one successful fresh realization and return the durable row."""

    event = ExplorationEvent(
        candidate_id=candidate.id,
        rule_id=candidate.target_rule,
        seed=candidate.seed,
        registry_fingerprint=candidate.registry_fingerprint,
        fillers=_candidate_fillers(project, candidate),
    )
    record = DurableExplorationEvent(
        **event.model_dump(),
        id="exp-" + uuid.uuid4().hex[:16],
        project=project.doc.name,
        timestamp=datetime.now(timezone.utc).isoformat(),
    ).model_dump()
    path = exploration_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def append_exploration_failure(
    project: Project,
    selection: ExplorationSelection,
    *,
    seed: int,
    error: str,
) -> dict[str, Any]:
    """Append one failed fresh attempt without claiming a generation."""

    raw_probe = selection.probe
    probe = (
        ExplorationFiller.model_validate(
            {
                key: raw_probe[key]
                for key in (
                    "slot",
                    "token_index",
                    "identity",
                    "surface",
                    "source",
                )
            }
        )
        if raw_probe is not None
        else None
    )
    failure = ExplorationFailure(
        rule_id=selection.rule_id,
        seed=seed,
        registry_fingerprint=project.registry.fingerprint,
        probe=probe,
        error=error,
    )
    record = DurableExplorationFailure(
        **failure.model_dump(),
        id="fail-" + uuid.uuid4().hex[:16],
        project=project.doc.name,
        timestamp=datetime.now(timezone.utc).isoformat(),
    ).model_dump()
    path = exploration_failure_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def read_exploration_events(project: Project) -> list[dict[str, Any]]:
    """Read and schema-check every generation observation in write order."""

    path = exploration_path(project)
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line_no, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            checked = DurableExplorationEvent.model_validate(raw)
        except Exception as exc:  # noqa: BLE001 - report corrupt authoring state
            raise GenerationError(
                f"{path}:{line_no}: invalid exploration event: {exc}"
            ) from exc
        events.append(
            {
                **raw,
                **checked.model_dump(),
            }
        )
    return events


def read_exploration_failures(project: Project) -> list[dict[str, Any]]:
    """Read and schema-check every failed attempt in write order."""

    path = exploration_failure_path(project)
    if not path.exists():
        return []
    failures: list[dict[str, Any]] = []
    for line_no, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            checked = DurableExplorationFailure.model_validate(raw)
        except Exception as exc:  # noqa: BLE001 - report corrupt authoring state
            raise GenerationError(
                f"{path}:{line_no}: invalid exploration failure: {exc}"
            ) from exc
        failures.append(
            {
                **raw,
                **checked.model_dump(),
            }
        )
    return failures


def _status(
    generated_count: int,
    reviewed_count: int,
    *,
    failed_count: int = 0,
    supported: bool = True,
) -> str:
    if not supported:
        return "blocked"
    if reviewed_count:
        return "reviewed"
    if generated_count:
        return "generated_unreviewed"
    if failed_count:
        return "attempted_failed"
    return "never_generated"


def exploration_status(project: Project) -> dict[str, Any]:
    """Fold current availability, observations, and live human reviews."""

    events = read_exploration_events(project)
    failures = [
        failure
        for failure in read_exploration_failures(project)
        if failure["registry_fingerprint"] == project.registry.fingerprint
    ]
    reviews = read_reviews(project, limit=100_000)
    availability = {
        item.id: item for item in list_rule_availability(project)
    }

    rule_generated = Counter(event["rule_id"] for event in events)
    rule_failed = Counter(failure["rule_id"] for failure in failures)
    rule_reviews = [
        review for review in reviews if review.get("target_rule") is not None
    ]
    rule_reviewed = Counter(review["target_rule"] for review in rule_reviews)
    rule_verdicts: dict[str, Counter[str]] = defaultdict(Counter)
    for review in rule_reviews:
        rule_verdicts[review["target_rule"]][review["verdict"]] += 1

    rule_last_generated: dict[str, str] = {}
    for event in events:
        timestamp = event.get("timestamp")
        if isinstance(timestamp, str):
            rule_last_generated[event["rule_id"]] = max(
                timestamp, rule_last_generated.get(event["rule_id"], timestamp)
            )
    rule_last_failed: dict[str, str] = {}
    for failure in failures:
        timestamp = failure.get("timestamp")
        if isinstance(timestamp, str):
            rule_last_failed[failure["rule_id"]] = max(
                timestamp,
                rule_last_failed.get(failure["rule_id"], timestamp),
            )
    rule_last_reviewed: dict[str, str] = {}
    for review in rule_reviews:
        timestamp = review.get("timestamp")
        if isinstance(timestamp, str):
            rule_last_reviewed[review["target_rule"]] = max(
                timestamp,
                rule_last_reviewed.get(review["target_rule"], timestamp),
            )

    rules = []
    for rule in project.registry.rules:
        current = availability[rule.id]
        source = project.source_index.rules.get(rule.id)
        generated_count = rule_generated[rule.id]
        failed_count = rule_failed[rule.id]
        reviewed_count = rule_reviewed[rule.id]
        rules.append(
            {
                **current.to_json(),
                "status": _status(
                    generated_count,
                    reviewed_count,
                    failed_count=failed_count,
                    supported=current.supported,
                ),
                "generated_count": generated_count,
                "failed_count": failed_count,
                "attempt_count": generated_count + failed_count,
                "reviewed_count": reviewed_count,
                "verdict_counts": {
                    verdict: rule_verdicts[rule.id][verdict]
                    for verdict in ("valid", "invalid", "unclear")
                },
                "last_generated_at": rule_last_generated.get(rule.id),
                "last_failed_at": rule_last_failed.get(rule.id),
                "last_reviewed_at": rule_last_reviewed.get(rule.id),
                "source": source.to_json() if source is not None else None,
            }
        )

    candidate_fillers: dict[str, set[str]] = defaultdict(set)
    filler_generated: Counter[str] = Counter()
    filler_failed: Counter[str] = Counter()
    filler_last_generated: dict[str, str] = {}
    filler_last_failed: dict[str, str] = {}
    for event in events:
        identities = {filler["identity"] for filler in event["fillers"]}
        candidate_fillers[event["candidate_id"]].update(identities)
        for identity in identities:
            filler_generated[identity] += 1
            timestamp = event.get("timestamp")
            if isinstance(timestamp, str):
                filler_last_generated[identity] = max(
                    timestamp, filler_last_generated.get(identity, timestamp)
                )
    for failure in failures:
        probe = failure.get("probe")
        if not isinstance(probe, dict):
            continue
        identity = probe["identity"]
        filler_failed[identity] += 1
        timestamp = failure.get("timestamp")
        if isinstance(timestamp, str):
            filler_last_failed[identity] = max(
                timestamp, filler_last_failed.get(identity, timestamp)
            )

    filler_reviewed: Counter[str] = Counter()
    filler_last_reviewed: dict[str, str] = {}
    for review in rule_reviews:
        for identity in candidate_fillers.get(review["candidate_id"], ()):
            filler_reviewed[identity] += 1
            timestamp = review.get("timestamp")
            if isinstance(timestamp, str):
                filler_last_reviewed[identity] = max(
                    timestamp,
                    filler_last_reviewed.get(identity, timestamp),
                )

    placements_by_identity: dict[str, list[ProbePlacement]] = defaultdict(list)
    for placement in _probe_catalog(project):
        placements_by_identity[placement.identity].append(placement)

    fillers = []
    for identity, placements in sorted(placements_by_identity.items()):
        source = project.source_index.lexicon[identity]
        generated_count = filler_generated[identity]
        failed_count = filler_failed[identity]
        reviewed_count = filler_reviewed[identity]
        fillers.append(
            {
                "identity": identity,
                "status": _status(
                    generated_count,
                    reviewed_count,
                    failed_count=failed_count,
                ),
                "generated_count": generated_count,
                "failed_count": failed_count,
                "attempt_count": generated_count + failed_count,
                "reviewed_count": reviewed_count,
                "last_generated_at": filler_last_generated.get(identity),
                "last_failed_at": filler_last_failed.get(identity),
                "last_reviewed_at": filler_last_reviewed.get(identity),
                "source": source.to_json(),
                "surfaces": sorted(
                    {
                        surface
                        for placement in placements
                        for surface in placement.surfaces
                    },
                    key=lambda value: value.casefold(),
                ),
                "compatible_rules": sorted(
                    {placement.rule_id for placement in placements}
                ),
                "placements": [
                    {
                        "rule_id": placement.rule_id,
                        "slot": placement.slot,
                        "token_index": placement.token_index,
                        "surfaces": list(placement.surfaces),
                    }
                    for placement in placements
                ],
            }
        )

    return {
        "rules": rules,
        "fillers": fillers,
        "summary": {
            "rules": dict(Counter(item["status"] for item in rules)),
            "fillers": dict(Counter(item["status"] for item in fillers)),
            "events": len(events),
            "failures": len(failures),
            "live_reviews": len(reviews),
        },
    }


def choose_exploration_target(
    project: Project,
    *,
    seed: int,
    rule_id: str | None = None,
    filler_identity: str | None = None,
) -> ExplorationSelection:
    """Choose a rule and lexical probe from the least-explored frontier."""

    status = exploration_status(project)
    rules = {item["id"]: item for item in status["rules"]}
    fillers = {item["identity"]: item for item in status["fillers"]}
    rng = random.Random(seed)

    identity = filler_identity.casefold() if filler_identity else None
    if identity is not None and identity not in fillers:
        raise GenerationError(
            f"lexicon entry {filler_identity!r} is not reachable through a "
            "currently supported premise-rule slot"
        )

    if rule_id is not None:
        rule = rules.get(rule_id)
        if rule is None:
            raise GenerationError(f"unknown premise rule {rule_id!r}")
        if not rule["supported"]:
            raise GenerationError(
                f"{rule_id} is blocked: {'; '.join(rule['blockers'])}"
            )
        if (
            identity is not None
            and rule_id not in fillers[identity]["compatible_rules"]
        ):
            raise GenerationError(
                f"lexicon entry {identity!r} cannot fill a supported slot in "
                f"{rule_id}"
            )
        chosen_rule = rule_id
    else:
        eligible = [
            item
            for item in status["rules"]
            if item["supported"]
            and (
                identity is None
                or item["id"] in fillers[identity]["compatible_rules"]
            )
        ]
        if not eligible:
            raise GenerationError("this project has no supported premise rules")
        least = min(item["attempt_count"] for item in eligible)
        tied = sorted(
            item["id"]
            for item in eligible
            if item["attempt_count"] == least
        )
        chosen_rule = tied[rng.randrange(len(tied))]

    placements = [
        placement
        for placement in _probe_catalog(project)
        if placement.rule_id == chosen_rule
        and (identity is None or placement.identity == identity)
    ]
    if not placements:
        return ExplorationSelection(
            rule_id=chosen_rule,
            locked_bindings={},
            probe=None,
        )

    if identity is None:
        least = min(
            fillers[placement.identity]["attempt_count"]
            for placement in placements
        )
        identities = sorted(
            {
                placement.identity
                for placement in placements
                if fillers[placement.identity]["attempt_count"] == least
            }
        )
        identity = identities[rng.randrange(len(identities))]
        placements = [
            placement
            for placement in placements
            if placement.identity == identity
        ]

    placements.sort(key=lambda item: (item.token_index, item.slot))
    placement = placements[rng.randrange(len(placements))]
    surface = placement.surfaces[rng.randrange(len(placement.surfaces))]
    source = project.source_index.lexicon[placement.identity]
    return ExplorationSelection(
        rule_id=chosen_rule,
        locked_bindings={placement.slot: surface},
        probe={
            "identity": placement.identity,
            "surface": surface,
            "rule_id": placement.rule_id,
            "slot": placement.slot,
            "token_index": placement.token_index,
            "source": source.to_json(),
        },
    )
