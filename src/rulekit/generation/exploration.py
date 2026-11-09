"""Designer-only generation observations and exploration status.

Successful fresh realizations and failed fresh attempts use separate
append-only ledgers. Neither contains human judgments, and runtime reading,
matching, inference, and benchmarks never import them.
"""

from __future__ import annotations

import json
import random
import uuid
from collections import Counter, OrderedDict, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..data.project import Project
from .candidate import GenerationCandidate, GenerationObjective
from .reviews import SourceLocation, premise_review_target_counts, read_reviews
from .sample import (
    GenerationError,
    _Filler,
    _FixtureCacheKey,
    _absent_categories,
    _category_membership_requirements,
    _distinct_measure_groups,
    _domain,
    _flat_sentence,
    _filler_in_category,
    _leaf_tokens,
    _load_fixtures,
    _measure_key,
    _measure_key_assignment_exists,
    _outside_categories,
    _outside_slot_categories,
    _slot_category_exclusions,
    _token_nodes,
    _unbound_optional_paths,
    list_rule_availability,
)


_PROBE_CACHE_LOCK = RLock()
_PROBE_CACHE: OrderedDict[
    tuple[str, _FixtureCacheKey], tuple["ProbePlacement", ...]
] = OrderedDict()
_MAX_PROBE_CACHE_ENTRIES = 16


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
    objective: GenerationObjective = "least_attempted_rule"
    filters: list[str] = Field(default_factory=list, max_length=64)
    target_signature: str | None = Field(default=None, max_length=512)
    structural_signatures: list[str] = Field(default_factory=list, max_length=128)
    phenomena: list[str] = Field(default_factory=list, max_length=64)


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
    objective: GenerationObjective = "least_attempted_rule"
    filters: list[str] = Field(default_factory=list, max_length=64)
    target_signature: str | None = Field(default=None, max_length=512)


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
    objective: GenerationObjective = "least_attempted_rule"
    filters: tuple[str, ...] = ()
    target_signature: str | None = None


_NUMERIC_SLOT_TYPES = frozenset(
    {
        "counted",
        "fraction",
        "multiplier",
        "nonunit_multiplier",
        "number",
        "percent",
        "ratio",
    }
)
_GENERATION_OBJECTIVES = frozenset(
    {
        "least_attempted_rule",
        "least_generated_rule",
        "least_reviewed_rule",
        "least_validated_rule",
        "least_covered_structure",
        "review_attention",
        "random",
    }
)


def _rule_profile(project: Project, rule: Any) -> dict[str, list[str]]:
    """Return vocabulary-free structural tags and atomic coverage targets."""

    seq = _flat_sentence(rule) or []
    tokens = list(_token_nodes(seq))
    categories: set[str] = set()
    slot_types: set[str] = set()
    phenomena: set[str] = set()
    signatures: set[str] = set()

    for token_no, (_, token, _) in enumerate(tokens):
        if token.opt is not None:
            phenomena.add("optional_branches")
            signatures.update(
                {
                    f"optional:{token_no}:included",
                    f"optional:{token_no}:omitted",
                }
            )
            continue
        if len(token.lit_options) > 1:
            phenomena.add("literal_alternatives")
            signatures.update(
                f"literal:{token_no}:{option.casefold()}"
                for option in token.lit_options
            )
        if token.type is not None:
            slot_types.add(token.type)
        for category in (
            token.cat,
            token.common_noun_cat,
            token.bare_reference_category,
        ):
            if category is not None:
                categories.update(project.registry.cat_ancestors(category))

    declared_categories = set(project.registry.category_parents) | set(
        project.registry.category_members
    )

    def collect_declared_categories(value: Any) -> None:
        if isinstance(value, str) and value in declared_categories:
            categories.update(project.registry.cat_ancestors(value))
        elif isinstance(value, dict):
            for child in value.values():
                collect_declared_categories(child)
        elif isinstance(value, list):
            for child in value:
                collect_declared_categories(child)

    for predicate in rule.where:
        dumped = predicate.model_dump(exclude_none=True)
        collect_declared_categories(dumped)
        if set(dumped) & {"absent", "slot_not_category", "unbound"}:
            phenomena.add("negative_constraints")

    roots = {
        project.registry.root_sense(category)
        for category in categories
    } | slot_types
    if "pronoun" in roots:
        phenomena.add("pronouns")
    if roots & {"adjective", "adverb", "comparative"}:
        phenomena.add("modifiers")
    if roots & {"preposition", "adposition"}:
        phenomena.add("prepositions")
    if "modal" in roots or "modal" in categories:
        phenomena.add("modals")
    if roots & {"time", "temporal"} or "temporal" in categories:
        phenomena.add("temporal")
    if roots & {"conjunction", "coordination"} or "span" in slot_types:
        phenomena.add("coordination_or_spans")
    if slot_types & _NUMERIC_SLOT_TYPES:
        phenomena.add("numeric")
    if "sentences" in rule.match:
        phenomena.add("multi_sentence")
    if rule.question_assumption:
        phenomena.add("question_assumption")

    fact_types = {emit.fact for emit in rule.emits}
    signatures.update(
        f"fact:{emit.fact}({','.join(sorted(emit.fields))})"
        for emit in rule.emits
    )
    if not signatures:
        signatures.add("surface:base")
    return {
        "phenomena": sorted(phenomena),
        "categories": sorted(categories),
        "slot_types": sorted(slot_types),
        "fact_types": sorted(fact_types),
        "structural_signatures": sorted(signatures),
    }


def _candidate_structural_signatures(
    candidate: GenerationCandidate,
) -> tuple[str, ...]:
    """Project one successful round trip onto atomic structural outcomes."""

    signatures: set[str] = set()
    for premise in candidate.premises:
        if premise.slot_type == "optional" and premise.binding in {
            "included",
            "omitted",
        }:
            signatures.add(
                f"optional:{premise.index}:{premise.binding}"
            )
        elif (
            premise.kind == "token"
            and premise.expression.startswith("literal ")
            and " | " in premise.expression
            and premise.binding
        ):
            signatures.add(
                f"literal:{premise.index}:{premise.binding.casefold()}"
            )
    for match in candidate.actual_matches:
        if match.rule_id != candidate.target_rule:
            continue
        for fact in match.emitted_facts:
            fact_type = str(fact.get("type", ""))
            snake = "".join(
                ("_" + char.lower()) if char.isupper() else char
                for char in fact_type
            ).lstrip("_")
            if snake:
                derivation = fact.get("derivation", {})
                templates = (
                    derivation.get("templates", {})
                    if isinstance(derivation, dict)
                    else {}
                )
                fields = templates or fact.get("fields", {})
                field_names = (
                    sorted(fields) if isinstance(fields, dict) else []
                )
                signatures.add(
                    f"fact:{snake}({','.join(field_names)})"
                )
    if not signatures and candidate.target_status in {"matched", "shadowed"}:
        signatures.add("surface:base")
    return tuple(sorted(signatures))


def _filter_tags(profile: dict[str, list[str]]) -> set[str]:
    return {
        *(f"phenomenon:{value}" for value in profile["phenomena"]),
        *(f"category:{value}" for value in profile["categories"]),
        *(f"fact:{value}" for value in profile["fact_types"]),
        *(f"slot_type:{value}" for value in profile["slot_types"]),
    }


def exploration_path(project: Project) -> Path:
    """The one durable event path; callers cannot supply another."""

    return project.root / "generation" / "exploration.jsonl"


def exploration_failure_path(project: Project) -> Path:
    """The fixed failed-attempt path; callers cannot supply another."""

    return project.root / "generation" / "failures.jsonl"


def _probe_catalog(project: Project) -> tuple[ProbePlacement, ...]:
    fixtures = _load_fixtures(project.root)
    cache_key = (project.registry.fingerprint, fixtures.cache_key)
    with _PROBE_CACHE_LOCK:
        cached = _PROBE_CACHE.get(cache_key)
        if cached is not None:
            _PROBE_CACHE.move_to_end(cache_key)
            return cached
    supported = {
        item.id for item in list_rule_availability(project) if item.supported
    }
    catalog_entries: list[ProbePlacement] = []
    grouped_domains: dict[int, tuple[list[_Filler], dict[str, tuple[str, ...]]]] = {}

    def group_surfaces(fillers: Iterable[_Filler]) -> dict[str, tuple[str, ...]]:
        grouped: dict[str, set[str]] = defaultdict(set)
        for filler in fillers:
            if (
                filler.identity in project.registry.lexicon
                and filler.identity in project.source_index.lexicon
            ):
                grouped[filler.identity].add(filler.surface)
        return {
            identity: tuple(sorted(values, key=str.casefold))
            for identity, values in grouped.items()
        }
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
        measure_key_domains = {
            name: tuple(
                dict.fromkeys(_measure_key(filler) for filler in domain)
            )
            for name, domain in measure_domains.items()
        }
        measure_extension_cache: dict[
            tuple[str, tuple[str, str | None, str | None]], bool
        ] = {}

        def measure_assignment_extends(
            slot_name: str,
            filler: Any,
        ) -> bool:
            cache_key = (slot_name, _measure_key(filler))
            if cache_key not in measure_extension_cache:
                measure_extension_cache[cache_key] = (
                    _measure_key_assignment_exists(
                        distinct_measure_groups,
                        measure_key_domains,
                        {slot_name: cache_key[1]},
                    )
                )
            return measure_extension_cache[cache_key]
        category_membership_requirements = (
            _category_membership_requirements(rule)
        )
        membership_slots = {
            name
            for group, _ in category_membership_requirements
            for name in group
        }
        membership_domains = {
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
            for name in membership_slots
            if name in tokens_by_slot
        }

        def category_membership_assignment_extends(
            slot_name: str,
            filler: Any,
        ) -> bool:
            return all(
                all(
                    other_name == slot_name
                    or any(
                        _filler_in_category(
                            candidate, category, project.registry
                        )
                        == _filler_in_category(
                            filler, category, project.registry
                        )
                        for candidate in membership_domains.get(
                            other_name, ()
                        )
                    )
                    for other_name in group
                )
                for group, category in category_membership_requirements
                if slot_name in group
            )
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
            domain = _domain(token, project.registry, fixtures)
            exclusions = tuple(
                pair for pair in slot_category_exclusions if pair[0] == token.slot
            )
            measure = token.slot in measure_slots
            membership = token.slot in membership_slots
            if not (absent_categories or exclusions or measure or membership):
                # Hold the domain alongside its grouping so an evicted list's
                # identity cannot be reused during this build.
                key = id(domain)
                if key not in grouped_domains:
                    grouped_domains[key] = domain, group_surfaces(domain)
                grouped = grouped_domains[key][1]
            else:
                grouped = group_surfaces(
                    filler for filler in domain
                    if (not absent_categories or _outside_categories(
                        filler, absent_categories, project.registry
                    ))
                    and (not exclusions or _outside_slot_categories(
                        filler, token.slot, exclusions, project.registry
                    ))
                    and (not measure or measure_assignment_extends(token.slot, filler))
                    and (not membership or category_membership_assignment_extends(token.slot, filler))
                )
            catalog_entries.extend(
                ProbePlacement(rule.id, token.slot, token_index, identity, surfaces)
                for identity, surfaces in grouped.items()
            )
    catalog = tuple(sorted(
        catalog_entries,
        key=lambda entry: (entry.rule_id, entry.slot, entry.token_index, entry.identity),
    ))
    with _PROBE_CACHE_LOCK:
        _PROBE_CACHE[cache_key] = catalog
        _PROBE_CACHE.move_to_end(cache_key)
        while len(_PROBE_CACHE) > _MAX_PROBE_CACHE_ENTRIES:
            _PROBE_CACHE.popitem(last=False)
    return catalog


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
    project: Project,
    candidate: GenerationCandidate,
    selection: ExplorationSelection | None = None,
) -> dict[str, Any]:
    """Append one successful fresh realization and return the durable row."""

    rule = next(
        item
        for item in project.registry.rules
        if item.id == candidate.target_rule
    )
    profile = _rule_profile(project, rule)
    event = ExplorationEvent(
        candidate_id=candidate.id,
        rule_id=candidate.target_rule,
        seed=candidate.seed,
        registry_fingerprint=candidate.registry_fingerprint,
        fillers=_candidate_fillers(project, candidate),
        objective=(
            selection.objective
            if selection is not None
            else "least_attempted_rule"
        ),
        filters=list(selection.filters) if selection is not None else [],
        target_signature=(
            selection.target_signature if selection is not None else None
        ),
        structural_signatures=list(
            _candidate_structural_signatures(candidate)
        ),
        phenomena=profile["phenomena"],
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
        objective=selection.objective,
        filters=list(selection.filters),
        target_signature=selection.target_signature,
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


def _read_exploration_ledger(
    path: Path, model: type[BaseModel], kind: str,
) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_bytes().splitlines(keepends=True), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            checked = model.model_validate(raw)
        except ValueError as exc:
            # A concurrent writer may still be appending the last row.
            if isinstance(exc, (UnicodeDecodeError, json.JSONDecodeError)) and not line.endswith(b"\n"):
                break
            raise GenerationError(f"{path}:{line_no}: invalid exploration {kind}: {exc}") from exc
        rows.append({**raw, **checked.model_dump()})
    return rows


def read_exploration_events(project: Project) -> list[dict[str, Any]]:
    """Read and schema-check every generation observation in write order."""

    return _read_exploration_ledger(exploration_path(project), DurableExplorationEvent, "event")


def read_exploration_failures(project: Project) -> list[dict[str, Any]]:
    """Read and schema-check every failed attempt in write order."""

    return _read_exploration_ledger(
        exploration_failure_path(project), DurableExplorationFailure, "failure",
    )


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


def _failure_cause(error: str) -> str:
    """Collapse a bounded-attempt wrapper to the actionable last cause."""

    marker = "deterministic attempts: "
    cause = error.rsplit(marker, 1)[-1] if marker in error else error
    cause = cause.split("; failure profile:", 1)[0]
    return cause[:512]


def exploration_status(
    project: Project,
    *,
    include_placements: bool = True,
) -> dict[str, Any]:
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
    profiles = {
        rule.id: _rule_profile(project, rule)
        for rule in project.registry.rules
    }
    current_events = [
        event
        for event in events
        if event["registry_fingerprint"] == project.registry.fingerprint
    ]
    current_structural_events = [
        event for event in current_events if event["structural_signatures"]
    ]
    signature_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for event in current_events:
        signature_counts[event["rule_id"]].update(
            event.get("structural_signatures", ())
        )

    rule_generated = Counter(event["rule_id"] for event in events)
    rule_failed = Counter(failure["rule_id"] for failure in failures)
    rule_validated = Counter(premise_review_target_counts(project))
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
        profile = profiles[rule.id]
        declared_signatures = profile["structural_signatures"]
        covered_signatures = sorted(
            signature
            for signature in declared_signatures
            if signature_counts[rule.id][signature]
        )
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
                "validated_count": rule_validated[rule.id],
                "verdict_counts": {
                    verdict: rule_verdicts[rule.id][verdict]
                    for verdict in ("valid", "invalid", "unclear")
                },
                "last_generated_at": rule_last_generated.get(rule.id),
                "last_failed_at": rule_last_failed.get(rule.id),
                "last_reviewed_at": rule_last_reviewed.get(rule.id),
                "source": source.to_json() if source is not None else None,
                "profile": profile,
                "structural_covered": len(covered_signatures),
                "structural_total": len(declared_signatures),
                "covered_signatures": covered_signatures,
                "signature_counts": {
                    signature: signature_counts[rule.id][signature]
                    for signature in declared_signatures
                },
                "uncovered_signatures": [
                    signature
                    for signature in declared_signatures
                    if signature not in covered_signatures
                ],
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
        item = {
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
            "compatible_rules": sorted(
                {placement.rule_id for placement in placements}
            ),
        }
        if include_placements:
            item.update(
                {
                    "surfaces": sorted(
                        {
                            surface
                            for placement in placements
                            for surface in placement.surfaces
                        },
                        key=lambda value: value.casefold(),
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
        fillers.append(item)

    supported_rules = [item for item in rules if item["supported"]]
    structural_total = sum(
        item["structural_total"] for item in supported_rules
    )
    structural_covered = sum(
        item["structural_covered"] for item in supported_rules
    )
    filter_options = {
        "phenomena": sorted(
            {
                value
                for item in supported_rules
                for value in item["profile"]["phenomena"]
            }
        ),
        "categories": sorted(
            {
                value
                for item in supported_rules
                for value in item["profile"]["categories"]
            }
        ),
        "fact_types": sorted(
            {
                value
                for item in supported_rules
                for value in item["profile"]["fact_types"]
            }
        ),
        "slot_types": sorted(
            {
                value
                for item in supported_rules
                for value in item["profile"]["slot_types"]
            }
        ),
    }
    failure_groups: dict[str, dict[str, Any]] = {}
    for failure in failures:
        cause = _failure_cause(failure["error"])
        group = failure_groups.setdefault(
            cause,
            {"cause": cause, "count": 0, "rules": set()},
        )
        group["count"] += 1
        group["rules"].add(failure["rule_id"])
    top_failures = [
        {
            "cause": item["cause"],
            "count": item["count"],
            "rules": sorted(item["rules"]),
        }
        for item in sorted(
            failure_groups.values(),
            key=lambda item: (-item["count"], item["cause"]),
        )[:5]
    ]

    return {
        "rules": rules,
        "fillers": fillers,
        "filter_options": filter_options,
        "health": {
            "supported_rules": len(supported_rules),
            "blocked_rules": len(rules) - len(supported_rules),
            "structural_covered": structural_covered,
            "structural_total": structural_total,
            "structural_coverage": (
                structural_covered / structural_total
                if structural_total
                else 1.0
            ),
            "current_structural_events": len(current_structural_events),
            "successful_events": len(current_events),
            "historical_successful_events": len(events),
            "failed_attempts": len(failures),
            "failure_rate": (
                len(failures) / (len(current_events) + len(failures))
                if current_events or failures
                else 0.0
            ),
            "top_failures": top_failures,
        },
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
    objective: GenerationObjective = "least_attempted_rule",
    filters: tuple[str, ...] = (),
) -> ExplorationSelection:
    """Choose a filtered rule, optional structure, and lexical probe."""

    status = exploration_status(project, include_placements=False)
    rules = {item["id"]: item for item in status["rules"]}
    fillers = {item["identity"]: item for item in status["fillers"]}
    rng = random.Random(seed)
    filters = tuple(sorted(set(filters)))
    if objective not in _GENERATION_OBJECTIVES:
        raise GenerationError(f"unknown generation objective {objective!r}")
    known_filters = {
        tag
        for item in status["rules"]
        if item["supported"]
        for tag in _filter_tags(item["profile"])
    }
    unknown_filters = sorted(set(filters) - known_filters)
    if unknown_filters:
        raise GenerationError(
            "unknown or currently unreachable structural filter(s): "
            + ", ".join(unknown_filters)
        )

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
        missing_filters = sorted(
            set(filters) - _filter_tags(rule["profile"])
        )
        if missing_filters:
            raise GenerationError(
                f"{rule_id} does not satisfy the selected structural "
                f"filter(s): {', '.join(missing_filters)}"
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
            and set(filters).issubset(_filter_tags(item["profile"]))
            and (
                identity is None
                or item["id"] in fillers[identity]["compatible_rules"]
            )
        ]
        if not eligible:
            detail = (
                " for filters " + ", ".join(filters)
                if filters
                else ""
            )
            raise GenerationError(
                "this project has no supported premise rules" + detail
            )
        if objective == "random":
            tied = sorted(item["id"] for item in eligible)
        elif objective == "least_generated_rule":
            least = min(item["generated_count"] for item in eligible)
            tied = sorted(
                item["id"]
                for item in eligible
                if item["generated_count"] == least
            )
        elif objective == "least_reviewed_rule":
            least = min(item["reviewed_count"] for item in eligible)
            tied = sorted(
                item["id"]
                for item in eligible
                if item["reviewed_count"] == least
            )
        elif objective == "least_validated_rule":
            least = min(item["validated_count"] for item in eligible)
            tied = sorted(
                item["id"]
                for item in eligible
                if item["validated_count"] == least
            )
        elif objective == "review_attention":
            needing_attention = [
                item
                for item in eligible
                if item["verdict_counts"]["invalid"]
                or item["verdict_counts"]["unclear"]
            ]
            if not needing_attention:
                raise GenerationError(
                    "no filtered rule has a live invalid or unclear review"
                )
            most = max(
                item["verdict_counts"]["invalid"]
                + item["verdict_counts"]["unclear"]
                for item in needing_attention
            )
            tied = sorted(
                item["id"]
                for item in needing_attention
                if item["verdict_counts"]["invalid"]
                + item["verdict_counts"]["unclear"]
                == most
            )
        elif objective == "least_covered_structure":
            least = min(
                (
                    item["structural_covered"] / item["structural_total"]
                    if item["structural_total"]
                    else 1.0
                )
                for item in eligible
            )
            tied = sorted(
                item["id"]
                for item in eligible
                if (
                    item["structural_covered"] / item["structural_total"]
                    if item["structural_total"]
                    else 1.0
                )
                == least
            )
        else:
            least = min(item["attempt_count"] for item in eligible)
            tied = sorted(
                item["id"]
                for item in eligible
                if item["attempt_count"] == least
            )
        chosen_rule = tied[rng.randrange(len(tied))]

    chosen_status = rules[chosen_rule]
    target_signature = None
    if objective == "least_covered_structure":
        counts = chosen_status["signature_counts"]
        least = min(counts.values())
        tied_signatures = sorted(
            signature for signature, count in counts.items() if count == least
        )
        target_signature = tied_signatures[
            rng.randrange(len(tied_signatures))
        ]

    # Structural targeting and automatic lexical targeting are independent
    # objectives. Locking the least-attempted filler can make an otherwise
    # reachable optional branch impossible, so only combine them when the
    # reviewer explicitly selected a filler.
    if objective == "least_covered_structure" and identity is None:
        return ExplorationSelection(
            rule_id=chosen_rule,
            locked_bindings={},
            probe=None,
            objective=objective,
            filters=filters,
            target_signature=target_signature,
        )

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
            objective=objective,
            filters=filters,
            target_signature=target_signature,
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
        objective=objective,
        filters=filters,
        target_signature=target_signature,
    )
