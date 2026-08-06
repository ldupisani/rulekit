"""Stable records returned by the generation workbench."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


GenerationMode = Literal["strict", "lexical_boundary"]


@dataclass(frozen=True)
class LexicalRelaxation:
    """One slot deliberately sampled outside its declared lexical gate."""

    slot: str
    surface: str
    identity: str
    requirement: str
    broader_domain: str


@dataclass(frozen=True)
class RuleAvailability:
    """Whether the current generator can realize a rule."""

    id: str
    description: str | None
    supported: bool
    blockers: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "supported": self.supported,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class MatchSummary:
    """One actual rule match produced by the ordinary matcher."""

    rule_id: str
    bindings: dict[str, str]
    consumed: tuple[int, ...]
    consumed_surfaces: tuple[str, ...]
    shadowed: bool
    emitted_facts: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class PremiseSummary:
    """One rule token or cross-slot predicate explained for a reviewer."""

    index: int
    kind: str
    expression: str
    binding: str | None
    status: str
    reason: str
    slot: str | None = None
    slot_type: str | None = None
    category_path: tuple[str, ...] = ()
    consumed: tuple[int, ...] = ()
    sources: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class ConsumedUnitSummary:
    """A unit consumed by the target match."""

    uid: int
    surface: str
    sense: str | None
    lemma: str | None


@dataclass(frozen=True)
class GenerationCandidate:
    """One reproducible sentence-generation experiment."""

    id: str
    project: str
    registry_fingerprint: str
    generator_version: str
    origin: Literal["generated", "reading"]
    generation_mode: GenerationMode
    seed: int
    target_rule: str | None
    target_description: str | None
    sentence: str
    requested_bindings: dict[str, str]
    target_bindings: dict[str, str]
    target_status: str
    target_specificity: tuple[int, int, int] | None
    target_source: dict[str, Any] | None
    premises: tuple[PremiseSummary, ...]
    consumed_units: tuple[ConsumedUnitSummary, ...]
    actual_matches: tuple[MatchSummary, ...]
    facts: tuple[dict[str, Any], ...]
    collisions: tuple[dict[str, Any], ...]
    deficiencies: tuple[str, ...]
    attempts: int
    lexical_relaxations: tuple[LexicalRelaxation, ...] = ()

    def to_json(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["actual_rule_ids"] = sorted(
            {match.rule_id for match in self.actual_matches}
        )
        return payload
