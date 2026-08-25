"""Stable records returned by the generation workbench."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


GenerationMode = Literal["strict", "lexical_boundary", "safety_boundary"]
GenerationObjective = Literal[
    "least_attempted_rule",
    "least_generated_rule",
    "least_reviewed_rule",
    "least_validated_rule",
    "least_covered_structure",
    "review_attention",
    "random",
]
AskScenarioMode = Literal[
    "ask_only",
    "answerable",
    "validated_premises",
    "missing_evidence",
]


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
    generation: Literal[
        "premise", "contextual", "reader-only", "safety"
    ] = "premise"

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "supported": self.supported,
            "blockers": list(self.blockers),
            "generation": self.generation,
        }


@dataclass(frozen=True)
class AskAvailability:
    """Whether one declared ask has an independently realizable surface."""

    id: str
    consumer: str | None
    supported: bool
    blockers: tuple[str, ...] = ()
    supported_modes: tuple[AskScenarioMode, ...] = ()

    def supports(self, mode: AskScenarioMode) -> bool:
        return mode in self.supported_modes

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "consumer": self.consumer,
            "supported": self.supported,
            "blockers": list(self.blockers),
            "supported_modes": list(self.supported_modes),
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
    safety_interceptions: tuple[MatchSummary, ...]
    facts: tuple[dict[str, Any], ...]
    collisions: tuple[dict[str, Any], ...]
    deficiencies: tuple[str, ...]
    attempts: int
    lexical_relaxations: tuple[LexicalRelaxation, ...] = ()
    context_before: tuple[str, ...] = ()
    context_after: tuple[str, ...] = ()
    target_sentence_index: int = 0

    def to_json(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["text"] = " ".join(
            (*self.context_before, self.sentence, *self.context_after)
        )
        payload["actual_rule_ids"] = sorted(
            {match.rule_id for match in self.actual_matches}
        )
        payload["safety_rule_ids"] = sorted(
            {match.rule_id for match in self.safety_interceptions}
        )
        return payload


@dataclass(frozen=True)
class AskScenarioCandidate:
    """One declared ask, optionally paired with generated premise evidence."""

    id: str
    project: str
    registry_fingerprint: str
    generator_version: str
    scenario_mode: AskScenarioMode
    seed: int
    reference_year: int | None
    target_ask: str
    consumer: str | None
    question: str
    text: str
    requested_bindings: dict[str, str]
    target_bindings: dict[str, str]
    query: dict[str, Any]
    target_source: dict[str, Any] | None
    premises: tuple[dict[str, Any], ...]
    answer: dict[str, Any]
    answer_shape: str
    minimal: bool
    attempts: int
    search_attempts: int

    def to_json(self) -> dict[str, Any]:
        return asdict(self)
