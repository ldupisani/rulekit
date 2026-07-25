"""Stable records returned by the generation workbench."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RuleAvailability:
    """Whether G1 can realize a rule, with blockers kept user-visible."""

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
    shadowed: bool
    emitted_facts: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class GenerationCandidate:
    """One reproducible sentence-generation experiment."""

    id: str
    project: str
    registry_fingerprint: str
    generator_version: str
    seed: int
    target_rule: str
    target_description: str | None
    sentence: str
    requested_bindings: dict[str, str]
    target_bindings: dict[str, str]
    target_status: str
    actual_matches: tuple[MatchSummary, ...]
    facts: tuple[dict[str, Any], ...]
    collisions: tuple[dict[str, Any], ...]
    deficiencies: tuple[str, ...]
    attempts: int

    def to_json(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["actual_rule_ids"] = sorted(
            {match.rule_id for match in self.actual_matches}
        )
        return payload
