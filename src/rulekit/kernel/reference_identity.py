"""Lossless nominal reference constraints, independent of amounts and predicates.

Descriptions constrain a reference; they do not assert that two compatible
descriptions are the same individual. Resolution requires one observed identity.
This module consumes reader structure, never reparses a displayed entity key.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from .model import Unit


@dataclass(frozen=True)
class ReferenceIdentity:
    head: str
    owner: ReferenceIdentity | None = None
    label: str | None = None
    qualifiers: tuple[str, ...] = ()
    resolved: bool = True
    # A local anonymous possessor is anchored by its first mention, not by a
    # named antecedent. Coordinates belong to this document's fact store only.
    utterance_anchor: tuple[int, int] | None = None

    @property
    def described(self) -> bool:
        return bool(self.owner or self.label or self.qualifiers)

    def key(self) -> tuple:
        key = (self.head, self.owner.key() if self.owner else None,
               self.label, self.qualifiers, self.resolved)
        return key + (self.utterance_anchor,) if self.utterance_anchor is not None else key

    def to_dict(self) -> dict:
        result = {"head": self.head,
                "owner": self.owner.to_dict() if self.owner else None,
                "label": self.label, "qualifiers": list(self.qualifiers),
                "resolved": self.resolved}
        if self.utterance_anchor is not None:
            result["utterance_anchor"] = list(self.utterance_anchor)
        return result

    @classmethod
    def from_dict(cls, value: dict, _depth: int = 0) -> ReferenceIdentity:
        if (not isinstance(value, dict)
                or set(value) - {"head", "owner", "label", "qualifiers", "resolved", "utterance_anchor"}
                or not isinstance(value.get("head"), str)
                or not value["head"].strip()
                or not isinstance(value.get("resolved", True), bool)
                or (value.get("label") is not None and not isinstance(value["label"], str))
                or not isinstance(value.get("qualifiers", []), (list, tuple))
                or any(not isinstance(part, str) for part in value.get("qualifiers", []))
                or (value.get("owner") is not None and not isinstance(value["owner"], dict))
                or (value.get("utterance_anchor") is not None and (
                    not isinstance(value["utterance_anchor"], (list, tuple))
                    or len(value["utterance_anchor"]) != 2
                    or any(type(part) is not int or part < 0 for part in value["utterance_anchor"])))):
            raise ValueError("malformed reference identity")
        if _depth >= 32:
            return cls(value.get("head", ""), resolved=False)
        owner = value.get("owner")
        parsed_owner = cls.from_dict(owner, _depth + 1) if owner is not None else None
        return cls(value["head"], parsed_owner,
                   value.get("label"), tuple(value.get("qualifiers", ())),
                   value.get("resolved", True) and (parsed_owner is None or parsed_owner.resolved),
                   tuple(value["utterance_anchor"]) if value.get("utterance_anchor") is not None else None)

    def display(self) -> str:
        """Compatibility/display projection, never an input to resolution."""
        descriptors = ([self.owner.display()] if self.owner else [])
        descriptors += list(self.qualifiers)
        descriptors += [self.label] if self.label else []
        return self.head + "".join(f"[{part}]" for part in descriptors)

    def binding_key(self):
        """Preserve simple journal labels; described references stay structural."""
        return self.key() if self.described or not self.resolved or self.utterance_anchor is not None else self.head


def flat_reference(head: str, owner: str | None = None,
                   label: str | None = None,
                   qualifier: str | None = None) -> ReferenceIdentity:
    """Adapter for older fact producers that already expose separate fields."""
    return ReferenceIdentity(head, ReferenceIdentity(owner) if owner else None,
                             label or None, (qualifier,) if qualifier else ())


def reference_from_unit(unit: Unit, _seen: frozenset[int] = frozenset()) -> ReferenceIdentity:
    if id(unit) in _seen or len(_seen) >= 32:
        return ReferenceIdentity("", resolved=False)
    seen = _seen | {id(unit)}
    if unit.sense() == "pronoun":
        target = next((ob.target for ob in unit.obligations()
                       if ob.need == "refers" and hasattr(ob.target, "features")), None)
        if target is not None:
            return reference_from_unit(target, seen)
        return ReferenceIdentity(unit.features.get("lemma", ""), resolved=False)
    features = unit.features
    owner_data = features.get("owner_reference")
    if owner_data is not None:
        try:
            owner = ReferenceIdentity.from_dict(owner_data)
        except (TypeError, ValueError, KeyError):
            # Explicit malformed structure is not permission to fall back to
            # a flat owner string. Retain an unresolved boundary for the UI.
            owner = ReferenceIdentity("", resolved=False)
    else:
        owner = ReferenceIdentity(features["owner"]) if features.get("owner") else None
    resolved = features.get("owner_ref_uid") is None or bool(features.get("owner_resolved"))
    qualifiers = features.get("reference_qualifiers")
    if qualifiers is None:
        qualifiers = (features["qualifier"],) if features.get("qualifier") else ()
    return ReferenceIdentity(features.get("lemma", features.get("fold", "")),
                             owner, features.get("label") or None,
                             tuple(sorted(set(qualifiers))),
                             resolved and (owner is None or owner.resolved))


def constrains(query: ReferenceIdentity, evidence: ReferenceIdentity) -> bool:
    """Every explicit constraint must be present in the evidence."""
    return bool(query.resolved and evidence.resolved and query.head == evidence.head
                and query.utterance_anchor == evidence.utterance_anchor
                and (query.label is None or query.label == evidence.label)
                and set(query.qualifiers).issubset(evidence.qualifiers)
                and (query.owner is None or (evidence.owner is not None
                     and constrains(query.owner, evidence.owner))))


def distinct_references(a: ReferenceIdentity, b: ReferenceIdentity) -> bool:
    """A missing descriptor is not proof that two role bindings differ."""
    if a.head != b.head:
        return True
    return bool(
        (a.label is not None and b.label is not None and a.label != b.label)
        or (a.owner is not None and b.owner is not None
            and distinct_references(a.owner, b.owner))
    )


def resolve_reference(query: ReferenceIdentity,
                      candidates: Iterable[ReferenceIdentity]) -> ReferenceIdentity | None:
    """Unique compatible identity, before filtering by measure, verb or value.

    A bare mention is a reference, not an extra described individual. It cannot
    supply a descriptor missing from the evidence. Compatible but differently
    described candidates are intentionally not unified.
    """
    pool = {ref for ref in candidates if ref.head == query.head}
    if not query.resolved or any(not ref.resolved for ref in pool):
        return None
    described = {ref for ref in pool if ref.described}
    if described:
        pool = described
    matches = {ref for ref in pool if constrains(query, ref)}
    return next(iter(matches)) if len(matches) == 1 else None


def fact_references(fact) -> tuple[ReferenceIdentity, ...]:
    return tuple(ref for field in ("entity_ref", "subject_ref", "standard_ref")
                 if isinstance(ref := getattr(fact, field, None), ReferenceIdentity))


def attributed_occurrences(query: ReferenceIdentity, attributions) -> tuple[int, ...] | None:
    """Select a participant only when all compatible occurrences can be resolved."""
    if any(role is None or role.actor is None or not role.actor.resolved for role in attributions):
        return None
    actors = [role.actor for role in attributions]
    same_head = [role for role in attributions if role.actor.head == query.head]
    if len(same_head) > 1 and any(role.actor_indefinite for role in same_head):
        return None
    selected = resolve_reference(query, actors)
    if selected is None:
        return None
    resolved = [resolve_reference(actor, actors) for actor in actors]
    if any(actor.head == query.head and identity is None
           for actor, identity in zip(actors, resolved, strict=True)):
        return None
    return tuple(index for index, identity in enumerate(resolved) if identity == selected)


def reference_pool(store) -> set[ReferenceIdentity]:
    return set(store.references) | {ref for fact in store.facts for ref in fact_references(fact)}


def scope_reference_store(store, query: ReferenceIdentity, *, allow_absent: bool = False):
    """A nonmutating, fail-closed view for legacy single-participant folds.

    Other heads remain available. For this head every adapted fact must resolve
    to the same identity. Untyped actor evidence cannot bypass an ambiguous head.
    The original typed facts and their provenance are retained on view copies.
    """
    from dataclasses import replace
    from .facts import FactStore
    from .model import Quantity, Relation, Predication, GroupTotal
    from .guards import _NUMERIC_FACT_FIELDS

    pool = reference_pool(store)
    if (allow_absent and query.resolved and not query.described
            and not any(ref.head == query.head for ref in pool)):
        return store
    selected = resolve_reference(query, pool)
    if selected is None:
        return None
    rivals = {ref for ref in pool if ref.head == query.head and ref.described}
    actor_heads = {ref.head for fact in store.facts
                   for field in ("entity_ref", "subject_ref")
                   if isinstance(ref := getattr(fact, field, None), ReferenceIdentity)}
    scoped = []
    for fact in store.facts:
        if isinstance(fact, Quantity):
            from .item_references import project_item_reference
            fact = project_item_reference(fact, store)
        if isinstance(fact, GroupTotal) and fact.scope is None and len(rivals) > 1:
            return None
        if isinstance(fact, Relation) and any(
            ref.head == query.head for ref in (fact.subject_ref, fact.standard_ref)
        ):
            if any(ref.head in actor_heads and resolve_reference(ref, pool) is None
                   for ref in (fact.subject_ref, fact.standard_ref)):
                return None
        fields = (("entity", "entity_ref"),) if isinstance(fact, Quantity) else (
            (("subject", "subject_ref"), ("standard", "standard_ref"))
            if isinstance(fact, Relation) else
            (("subject", "subject_ref"),) if isinstance(fact, Predication) else ())
        updates = {}
        omit = False
        for role, ref_field in fields:
            ref = getattr(fact, ref_field)
            if ref.head != query.head:
                continue
            identity = resolve_reference(ref, pool)
            if identity is None:
                return None
            if identity != selected:
                omit = True
                break
            updates[role] = query.head
        if omit:
            continue
        if not fields and len(rivals) > 1 and any(
            isinstance(getattr(fact, field, None), (int, float))
            for field in _NUMERIC_FACT_FIELDS
        ) and any(
            getattr(fact, field, None) == query.head
            for field in ("entity", "subject", "scope")
        ):
            return None
        scoped.append(replace(fact, **updates) if updates else fact)
    # A later fold may query another head. Its amount-free rivals must remain
    # visible even though this view narrowed the current participant.
    references = tuple(ref for ref in pool if ref.head != query.head) + (selected,)
    return FactStore(facts=scoped, references=references,
                     item_reference_clauses=store.item_reference_clauses)


def scope_entity_store(store, entity: str):
    """Legacy fold adapter: display keys identify facts, never parsed identities."""
    from .model import Quantity
    pool = reference_pool(store)
    exact = {resolve_reference(q.entity_ref, pool)
             for q in store.by_kind(Quantity) if q.entity == entity}
    if None in exact:
        return None, entity
    if len(exact) > 1:
        return None, entity
    reference = next(iter(exact)) if len(exact) == 1 else ReferenceIdentity(entity)
    if not any(ref.head == reference.head for ref in reference_pool(store)):
        return store, entity  # an unmigrated family, with no rival quantity identity
    scoped = scope_reference_store(store, reference)
    return scoped, reference.head


def scope_query_store(store, query: dict):
    """One identity gate for answer dispatch and answer-use accounting.

    An absent bare head leaves legacy class/rate consumers to prove their own
    evidence; it does not erase an observed rival. An explicitly declared
    owned-location holder fallback instead resolves the full owner identity.
    """
    raw = query.get("evidence_entity_reference")
    if raw is None:
        return store
    reference = ReferenceIdentity.from_dict(raw)
    pool = reference_pool(store)
    head_observed = any(ref.head == reference.head for ref in pool)
    if not head_observed and reference.resolved:
        if not reference.described:
            return store
        fallback = query.get("owned_place_holder_fallback")
        if (fallback and reference.owner is not None
                and reference.owner.head == fallback):
            return scope_reference_store(store, reference.owner)
    return scope_reference_store(store, reference)
