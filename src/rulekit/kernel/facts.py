"""The fact store: dedupe, agreement, subsumption, and collision.

There is no mode in which two rules disagreeing about the same fact is
resolved by ordering: agreement dedupes, strict subsumption lets the more
specific rule win silently, and anything else quarantines BOTH facts,
declines the item, and records a Collision with both provenances.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from ..data.registry import Registry
from .model import Fact, Predication, Price, Provenance, Quantity
from .patterns import RuleMatchResult, subsumes


@dataclass
class Collision:
    key: tuple
    a_source: str
    b_source: str
    a_value: object
    b_value: object


@dataclass(frozen=True)
class AgreementAmbiguity:
    """Two independently attributed derivations collapsed to one fact.

    This is diagnostic evidence only.  The store keeps its first fact and
    preserves the long-standing same-key/same-value dedupe behaviour; a later
    corpus report decides whether either derivation needs a semantic change.
    """

    key: tuple
    value: object
    retained: Provenance
    deduped: Provenance

    def to_trace_event(self) -> dict:
        return {
            "kind": "agreement-ambiguity",
            "key": list(self.key),
            "value": self.value,
            "retained": {
                "source": self.retained.source,
                "sentence": self.retained.sentence,
                "decision_seq": self.retained.decision_seq,
                "distributive": self.retained.distributive,
                **({"assumption": True} if self.retained.assumption else {}),
            },
            "deduped": {
                "source": self.deduped.source,
                "sentence": self.deduped.sentence,
                "decision_seq": self.deduped.decision_seq,
                "distributive": self.deduped.distributive,
                **({"assumption": True} if self.deduped.assumption else {}),
            },
            "reason": "separate derivations agreed on one fact; retained the first",
        }


@dataclass
class FactStore:
    facts: list[Fact] = field(default_factory=list)
    collisions: list[Collision] = field(default_factory=list)
    quarantined: list[Fact] = field(default_factory=list)
    agreement_ambiguities: list[AgreementAmbiguity] = field(default_factory=list)

    def _record_agreement(self, existing: Fact, fact: Fact) -> None:
        """Keep one event per provenance pair, even across saturation rounds."""
        if existing.provenance == fact.provenance:
            return
        event = AgreementAmbiguity(
            key=fact.key(),
            value=fact.value_part(),
            retained=existing.provenance,
            deduped=fact.provenance,
        )
        if event not in self.agreement_ambiguities:
            self.agreement_ambiguities.append(event)

    def admit(self, fact: Fact) -> bool:
        """Admit one fact. Same key + same value dedupes; same key +
        different value is a conflict → both quarantined — UNLESS both
        sides are Quantity facts carrying two DIFFERENT possessive owners
        of the same bare-lemma entity ("Kennedy's house" vs "Benedict's
        house", both fold to entity='house'): that is not a genuine
        disagreement, it is two distinct entities the bare lemma alone
        can't tell apart, so both re-key to entity[owner] and are admitted
        as separate facts instead. The owner split precedes agreement
        deduplication, so equal values from different owners also remain two
        facts. Later owned siblings enter the same qualified keyspace
        directly; a lone possessive noun keeps its bare identity untouched
        (cross-mention folding like "Tom's dog ... the dog ..." is
        unaffected). The same re-key applies, independently, when the
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

        A FOURTH, independent mirror (mining candidate labeled-entity-
        identity) applies the same entity-key discipline as `owner`/
        `qualifier` to a trailing INDEX label: "Jar A has 28 marbles" vs
        "Jar B has 15 marbles" both fold to entity='jar'; when both sides
        carry a non-null `label` (Quantity) and they DIFFER, re-key
        `entity` to `bare[label]` and admit both — same shape as `owner`/
        `qualifier`, no null-vs-non-null total guard needed (an index
        label never legitimately co-occurs with an unlabeled bare sibling
        the way a measure qualifier's part/whole total does).

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
        store.

        A FIFTH, independent mirror (mining candidate conjoined-event-
        conjuncts) disambiguates by within-sentence CONJUNCT POSITION
        instead of any naming field: "sold 3 boxes to her aunt and 4 boxes
        to her uncle" — both conjuncts share the SAME bare entity/measure
        with no owner/qualifier/measure_qualifier/label to split on at all.
        Tried LAST, after all four naming mirrors, so a genuinely qualifier-
        differentiated pair ("1 purple hat" / "4 green hats") still takes
        the measure_qualifier path unchanged (keeping its paired Price
        facts, which carry no `segment`, in lockstep). Unlike the naming
        mirrors this one renames nothing — both sides admit as-is, sharing
        one key(); every consumer already reads Quantity facts by iterating
        `store.by_kind(Quantity)` and filtering by attribute, never by a
        unique key lookup, so the existing Sigma-events fold sums the
        conjuncts unchanged. A SAME-VALUE conjunct pair ("3 rolls to
        grandma ... 3 rolls to a neighbour") reaches this mirror too
        (segment still differs, so it never hits the top-of-loop agreement
        dedupe) and so is never silently undercounted to one occurrence."""
        # THE QUALIFIED SPLIT IS PAIRWISE, SO ODD LISTS STRANDED THE LAST ONE.
        #
        # The measure-qualifier split below only fires on a KEY COLLISION, and
        # re-keying both sides REMOVES the bare key they collided on. So a
        # third qualified sibling arrives, finds nothing to collide with, and
        # is stored BARE — a silently dropped qualifier, not a decline:
        #
        #   "15 brown bears, 24 white bears and 27 black bears"
        #     brown -> stored bare 'bear'
        #     white -> COLLIDES -> both re-keyed to bear[brown], bear[white]
        #     black -> no bare 'bear' left -> stored as bare 'bear'   <-- bug
        #
        # Confirmed by prediction before it was fixed: the defect is PARITY,
        # so n=3 and n=5 stranded the last conjunct while n=4 and n=6 were
        # clean (the 4th collides with the stranded 3rd and rescues it).
        #
        # The cure is to make the qualified keying ORDER-INDEPENDENT rather
        # than to add another pairwise case: if this measure already has a
        # qualified sibling on this entity, this fact belongs in that same
        # keyspace. The `no bare sibling` condition is copied verbatim from
        # the split below — a stated unqualified holding IS the whole, and
        # splitting alongside it would misread the whole as another part.
        # Ownership has the same odd-sibling problem but no part/whole
        # exception: once two owners coexist, every later owned sibling must
        # enter the owner-qualified entity keyspace directly.
        if (
            isinstance(fact, Quantity)
            and fact.owner
            and "[" not in str(fact.entity)
            and any(
                isinstance(other, Quantity)
                and other.owner
                and str(other.entity) == f"{fact.entity}[{other.owner}]"
                for other in self.facts
            )
        ):
            fact = replace(fact, entity=f"{fact.entity}[{fact.owner}]")
        # Measure qualifiers use the order-independent cure described above,
        # including their separate unqualified-total guard.
        if (
            isinstance(fact, Quantity)
            and fact.measure_qualifier
            and "[" not in str(fact.measure)
            and any(
                isinstance(other, Quantity)
                and other.entity == fact.entity
                and str(other.measure) == f"{fact.measure}[{other.measure_qualifier}]"
                for other in self.facts
            )
            and not any(
                isinstance(other, Quantity)
                and other.entity == fact.entity
                and other.measure == fact.measure
                and other.measure_qualifier is None
                for other in self.facts
            )
        ):
            fact = replace(fact, measure=f"{fact.measure}[{fact.measure_qualifier}]")
        for existing in self.facts:
            if existing.key() == fact.key():
                # A conjunct-segment split (mirror #5 below) must win even
                # when the two conjuncts happen to state the SAME value
                # ("3 rolls to grandma ... 3 rolls to a neighbour") — the
                # ordinary agreement-dedupe below would otherwise treat
                # them as one restated fact and the fold would UNDERCOUNT
                # (3 + 3 folding to a single 3 instead of 6). Checked here,
                # ahead of the dedupe, but the actual split still happens
                # at mirror #5 in its normal (last-resort) priority order.
                conjunct_split = (
                    isinstance(existing, Quantity)
                    and isinstance(fact, Quantity)
                    and (existing.segment is not None or fact.segment is not None)
                    and (existing.segment or 0) != (fact.segment or 0)
                )
                owner_split = (
                    isinstance(existing, Quantity)
                    and isinstance(fact, Quantity)
                    and bool(existing.owner)
                    and bool(fact.owner)
                    and existing.owner != fact.owner
                )
                if (
                    existing.value_part() == fact.value_part()
                    and not conjunct_split
                    and not owner_split
                ):
                    self._record_agreement(existing, fact)
                    if (
                        isinstance(existing, Predication)
                        and isinstance(fact, Predication)
                        and fact.dobj_unquantified
                        and not existing.dobj_unquantified
                    ):
                        # Agreement about the predicate cannot erase newly
                        # stated uncertainty about its object's amount.
                        self.facts[self.facts.index(existing)] = replace(
                            existing, dobj_unquantified=True
                        )
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
                    isinstance(existing, Quantity)
                    and isinstance(fact, Quantity)
                    and existing.label
                    and fact.label
                    and existing.label != fact.label
                ):
                    self.facts.remove(existing)
                    self.facts.append(
                        replace(existing, entity=f"{existing.entity}[{existing.label}]")
                    )
                    self.facts.append(replace(fact, entity=f"{fact.entity}[{fact.label}]"))
                    return True
                if (
                    isinstance(existing, Quantity)
                    and isinstance(fact, Quantity)
                    and (existing.segment is not None or fact.segment is not None)
                    and (existing.segment or 0) != (fact.segment or 0)
                ):
                    # A FIFTH, independent mirror (mining candidate
                    # conjoined-event-conjuncts) — the within-sentence
                    # CONJUNCT position, tried only once none of the four
                    # mirrors above already explained the collision (so a
                    # genuinely qualifier/owner/label-differentiated pair
                    # still re-keys exactly as before, keeping its paired
                    # Price facts — which carry no `segment` — in
                    # lockstep). "sold 3 boxes to her aunt and 4 boxes to
                    # her uncle" folds both conjuncts to the SAME bare
                    # entity/measure with no other distinguishing field at
                    # all; unlike the other four mirrors this one needs no
                    # rename — downstream fold consumers iterate
                    # `store.by_kind(Quantity)` and filter by attribute, not
                    # by a unique key lookup — so both facts admit as-is,
                    # sharing one key(), and the existing Sigma-events fold
                    # sums them unchanged. A SAME-VALUE conjunct pair ("3
                    # rolls to grandma ... 3 rolls to a neighbour") takes
                    # this same path (segment still differs) instead of the
                    # top-of-loop agreement dedupe, so it is never silently
                    # undercounted to one occurrence.
                    #
                    # `None` normalizes to 0 in the comparison because the
                    # FIRST/head conjunct's own fact is emitted before its
                    # siblings are even walked (learn.py's pre-existing
                    # first-item emission site) and deliberately keeps
                    # `segment=None` rather than being retrofitted to 0 —
                    # every fact predating this field stays byte-identical.
                    # A head/first-conjunct pair (None vs 1) must still
                    # split here, so the `or 0` reads a bare None as segment
                    # position zero for this comparison only; requiring at
                    # least one side non-None keeps two ordinary unrelated
                    # facts (segment None on both sides, the overwhelming
                    # common case) falling through to quarantine exactly as
                    # before this mirror existed.
                    self.facts.append(fact)
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
