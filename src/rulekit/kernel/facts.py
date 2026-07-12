"""The fact store: dedupe, agreement, subsumption, and collision.

There is no mode in which two rules disagreeing about the same fact is
resolved by ordering: agreement dedupes, strict subsumption lets the more
specific rule win silently, and anything else quarantines BOTH facts,
declines the item, and records a Collision with both provenances.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from ..data.registry import Registry
from .model import Fact, Price, Quantity
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
        different value is a conflict → both quarantined — UNLESS both
        sides are Quantity facts carrying two DIFFERENT possessive owners
        of the same bare-lemma entity ("Kennedy's house" vs "Benedict's
        house", both fold to entity='house'): that is not a genuine
        disagreement, it is two distinct entities the bare lemma alone
        can't tell apart, so both re-key to entity[owner] and are admitted
        as separate facts instead. Scoped to the collision itself — a
        possessive noun that never collides keeps its bare identity
        untouched (cross-mention folding like "Tom's dog ... the dog ..."
        is unaffected). The same re-key applies, independently, when the
        two sides instead carry two DIFFERENT attributive-modifier
        qualifiers of the same bare-lemma entity ("coconut tree" vs
        "mango tree", both fold to entity='tree') — increment 34's mirror
        of the owner mechanism, gated on `qualifier` instead of `owner`.

        A THIRD, independent mirror (mining candidate qualified-measure-
        keys) applies the same discipline to the MEASURE key instead of
        the entity key: "12 white marbles" vs "6 blue marbles" both fold
        to measure='marble', and two differently-qualified Price facts
        ("a red shirt for $32" vs "3 blue shirts at $27 each") both fold
        to item='shirt'. When both sides carry a non-null
        `measure_qualifier` (Quantity) or `qualifier` (Price) and they
        DIFFER, re-key `measure`/`item` to `bare[qualifier]` and admit
        both instead of quarantining. A null-vs-non-null pairing (the
        collection total vs. one named subset, e.g. "20 marbles" then "12
        white marbles") is NOT a naming collision — it is a genuine
        part/whole relation and must keep declining, exactly like the
        owner/entity-qualifier mechanisms above only split when BOTH
        sides are non-null.

        That null-vs-non-null guard alone is not enough when the total
        uses a DIFFERENT verb/occurrence than its parts ("collected 65
        shells… got 13 purple, 8 pink, 18 yellow, and 12 blue shells"): the
        total's key never even collides with the parts' key, so a chain of
        3+ mutually-different-qualifier parts can pairwise-split itself
        completely clean, leaving the untouched bare total looking like an
        uncontested, independent single holding — a confident wrong (found
        on dev-holdout during development). The fix generalizes the same
        invariant across the WHOLE store rather than just the colliding
        pair: a split is refused whenever any OTHER already-admitted fact
        for the same entity/item shares the bare measure with a null
        qualifier — a bare sibling anywhere means a total is in play, so
        this falls through to the ordinary quarantine-and-decline path
        instead of laundering a genuine part/whole relation into a clean
        store."""
        for existing in self.facts:
            if existing.key() == fact.key():
                if existing.value_part() == fact.value_part():
                    return True  # agreement: dedupe
                if (
                    isinstance(existing, Quantity)
                    and isinstance(fact, Quantity)
                    and existing.owner
                    and fact.owner
                    and existing.owner != fact.owner
                ):
                    self.facts.remove(existing)
                    self.facts.append(
                        replace(existing, entity=f"{existing.entity}[{existing.owner}]")
                    )
                    self.facts.append(replace(fact, entity=f"{fact.entity}[{fact.owner}]"))
                    return True
                if (
                    isinstance(existing, Quantity)
                    and isinstance(fact, Quantity)
                    and existing.qualifier
                    and fact.qualifier
                    and existing.qualifier != fact.qualifier
                ):
                    self.facts.remove(existing)
                    self.facts.append(
                        replace(existing, entity=f"{existing.entity}[{existing.qualifier}]")
                    )
                    self.facts.append(
                        replace(fact, entity=f"{fact.entity}[{fact.qualifier}]")
                    )
                    return True
                if (
                    isinstance(existing, Quantity)
                    and isinstance(fact, Quantity)
                    and existing.measure_qualifier
                    and fact.measure_qualifier
                    and existing.measure_qualifier != fact.measure_qualifier
                    and not any(
                        isinstance(other, Quantity)
                        and other.entity == fact.entity
                        and other.measure == fact.measure
                        and other.measure_qualifier is None
                        for other in self.facts
                    )
                ):
                    self.facts.remove(existing)
                    self.facts.append(
                        replace(
                            existing,
                            measure=f"{existing.measure}[{existing.measure_qualifier}]",
                        )
                    )
                    self.facts.append(
                        replace(fact, measure=f"{fact.measure}[{fact.measure_qualifier}]")
                    )
                    return True
                if (
                    isinstance(existing, Price)
                    and isinstance(fact, Price)
                    and existing.qualifier
                    and fact.qualifier
                    and existing.qualifier != fact.qualifier
                    and not any(
                        isinstance(other, Price)
                        and other.item == fact.item
                        and other.qualifier is None
                        for other in self.facts
                    )
                ):
                    self.facts.remove(existing)
                    self.facts.append(
                        replace(existing, item=f"{existing.item}[{existing.qualifier}]")
                    )
                    self.facts.append(
                        replace(fact, item=f"{fact.item}[{fact.qualifier}]")
                    )
                    return True
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
