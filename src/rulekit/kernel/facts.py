"""The fact store: dedupe, agreement, subsumption, and collision.

There is no mode in which two rules disagreeing about the same fact is
resolved by ordering: agreement dedupes, strict subsumption lets the more
specific rule win silently, and anything else quarantines BOTH facts,
declines the item, and records a Collision with both provenances.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..data.registry import Registry
from .model import Fact
from .patterns import RuleMatchResult, subsumes


@dataclass
class Collision:
    key: tuple
    a_source: str
    b_source: str
    a_value: object
    b_value: object


@dataclass
class FactStore:
    facts: list[Fact] = field(default_factory=list)
    collisions: list[Collision] = field(default_factory=list)
    quarantined: list[Fact] = field(default_factory=list)

    def admit(self, fact: Fact) -> bool:
        """Admit one fact. Same key + same value dedupes; same key +
        different value is a conflict → both quarantined."""
        for existing in self.facts:
            if existing.key() == fact.key():
                if existing.value_part() == fact.value_part():
                    return True  # agreement: dedupe
                self.collisions.append(
                    Collision(
                        key=fact.key(),
                        a_source=existing.provenance.source,
                        b_source=fact.provenance.source,
                        a_value=existing.value_part(),
                        b_value=fact.value_part(),
                    )
                )
                self.facts.remove(existing)
                self.quarantined.extend([existing, fact])
                return False
        self.facts.append(fact)
        return True

    def admit_rule_results(self, results: list[RuleMatchResult], reg: Registry) -> None:
        """Adjudicate a batch of pattern-rule matches from one sentence.

        Subsumption first: a match strictly subsumed by another (superset
        span, strictly higher specificity) is dropped silently — narrowing a
        category IS the conflict lever, so the narrow rule winning is the
        author's intent. Survivors' facts then admit individually, where
        same-key disagreement collides.
        """
        survivors: list[RuleMatchResult] = []
        for r in results:
            shadowed = any(
                other is not r and subsumes(other.match, r.match, reg)
                for other in results
            )
            if not shadowed:
                survivors.append(r)
        for r in survivors:
            for fact in r.facts:
                self.admit(fact)

    def by_kind(self, kind: type) -> list[Fact]:
        return [f for f in self.facts if isinstance(f, kind)]

    @property
    def clean(self) -> bool:
        return not self.collisions
