"""Deterministic, advisory hypotheses for the generation workbench.

The human supplies the defect. This module only asks whether the current
matcher evidence supports a useful, source-linked next place to inspect.
It never drafts or applies a rule change.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any, Literal

from .candidate import GenerationCandidate, PremiseSummary
from .reviews import (
    HypothesisRecord,
    PremiseAttachment,
    ReviewDefect,
    SourceLocation,
)


def _attached_premise(
    candidate: GenerationCandidate,
    attachment: PremiseAttachment,
) -> PremiseSummary | None:
    if attachment.kind == "sentence":
        return None
    return next(
        (
            premise
            for premise in candidate.premises
            if premise.kind == attachment.kind
            and premise.index == attachment.index
        ),
        None,
    )


def _attached_fact(
    candidate: GenerationCandidate,
    defect: ReviewDefect,
) -> dict[str, Any] | None:
    attachment = defect.attachment
    if (
        attachment.kind != "fact"
        or attachment.index is None
        or defect.fact is None
    ):
        return None
    if attachment.index >= len(candidate.facts):
        return None
    fact = candidate.facts[attachment.index]
    current = {
        key: fact[key]
        for key in ("type", "fields", "source", "sentence")
    }
    # Source navigation and the declarative derivation are explanatory
    # metadata. Fact identity remains the exact resolved type/fields/source/
    # sentence tuple, so adding either explanation cannot orphan an otherwise
    # immutable attachment.
    snapshot = defect.fact.model_dump(
        exclude={"source_ref", "derivation"}
    )
    return fact if current == snapshot else None


def _sources(
    candidate: GenerationCandidate,
    premise: PremiseSummary | None,
    fact: dict[str, Any] | None = None,
) -> list[SourceLocation]:
    raw = list(premise.sources) if premise is not None else []
    if fact is not None:
        if fact.get("source_ref") is not None:
            raw.append(fact["source_ref"])
        elif (
            fact.get("source") == candidate.target_rule
            and candidate.target_source is not None
        ):
            raw.append(candidate.target_source)
    elif candidate.target_source is not None:
        raw.append(candidate.target_source)
    seen: set[tuple[str, int, str]] = set()
    out: list[SourceLocation] = []
    for source in raw:
        key = (str(source["path"]), int(source["line"]), str(source["kind"]))
        if key in seen:
            continue
        seen.add(key)
        out.append(SourceLocation.model_validate(source))
    return out


def _hypothesis(
    candidate: GenerationCandidate,
    *,
    kind: str,
    claim: str,
    observations: Iterable[str],
    premise: PremiseAttachment,
    sources: list[SourceLocation],
) -> HypothesisRecord:
    digest = hashlib.sha256(
        (
            f"{candidate.id}\0{kind}\0{premise.kind}\0{premise.index}"
        ).encode()
    ).hexdigest()[:16]
    return HypothesisRecord(
        id=f"hyp-{digest}",
        kind=kind,
        claim=claim,
        observations=list(observations),
        premise=premise,
        sources=sources,
    )


def _duplicate_bindings(candidate: GenerationCandidate) -> list[list[str]]:
    by_surface: dict[str, list[str]] = {}
    for slot, surface in sorted(candidate.requested_bindings.items()):
        by_surface.setdefault(surface.casefold(), []).append(slot)
    return [slots for slots in by_surface.values() if len(slots) > 1]


def derive_hypotheses(
    candidate: GenerationCandidate,
    *,
    verdict: Literal["valid", "invalid", "unclear"],
    defects: list[ReviewDefect],
) -> tuple[HypothesisRecord, ...]:
    """Return only hypotheses supported by the selected defect and trace."""

    out: list[HypothesisRecord] = []
    seen: set[tuple[str, str, int | None]] = set()

    def add(
        *,
        kind: str,
        claim: str,
        observations: Iterable[str],
        attachment: PremiseAttachment,
        premise: PremiseSummary | None,
        fact: dict[str, Any] | None = None,
    ) -> None:
        key = (kind, attachment.kind, attachment.index)
        sources = _sources(candidate, premise, fact)
        if key in seen or not sources:
            return
        seen.add(key)
        out.append(
            _hypothesis(
                candidate,
                kind=kind,
                claim=claim,
                observations=observations,
                premise=attachment,
                sources=sources,
            )
        )

    for defect in defects:
        attachment = defect.attachment
        premise = _attached_premise(candidate, attachment)
        fact = _attached_fact(candidate, defect)
        human_observation = (
            f"human verdict {verdict!r} selected defect "
            f"{defect.kind.replace('_', ' ')!r}"
        )

        if defect.kind in {
            "premise_too_broad",
            "wrong_category_membership",
            "semantically_implausible",
        } and premise is not None:
            if premise.category_path:
                add(
                    kind="category_gate_too_broad",
                    claim=(
                        f"The category gate on {premise.slot or premise.expression} "
                        "may admit a filler outside the intended boundary."
                    ),
                    observations=(
                        human_observation,
                        f"{premise.binding!r} passed {premise.expression}",
                        "category path: " + " → ".join(premise.category_path),
                    ),
                    attachment=attachment,
                    premise=premise,
                )
            elif candidate.target_status in {"matched", "shadowed"}:
                add(
                    kind="premise_gate_too_broad",
                    claim=(
                        f"The attached gate {premise.expression!r} may be broader "
                        "than the rule's intended premise."
                    ),
                    observations=(
                        human_observation,
                        f"the target rule {candidate.target_status}",
                        f"the attached binding was {premise.binding!r}",
                    ),
                    attachment=attachment,
                    premise=premise,
                )

        if defect.kind in {
            "premise_too_narrow",
            "intended_rule_did_not_fire",
        } and candidate.target_status == "absent":
            label = premise.expression if premise is not None else candidate.target_rule
            add(
                kind="premise_gate_too_narrow",
                claim=(
                    f"The target gate {label!r} may exclude a sentence the rule "
                    "is intended to accept."
                ),
                observations=(
                    human_observation,
                    "the intended target rule was absent after ordinary matching",
                    "partial premise failures are unavailable, so inspect the "
                    "attached declaration rather than assuming which gate failed",
                ),
                attachment=attachment,
                premise=premise,
            )

        if fact is not None and defect.kind in {
            "unexpected_fact",
            "incorrect_fact_field",
            "missing_fact_context",
        }:
            kind, claim = {
                "unexpected_fact": (
                    "fact_emission_not_justified",
                    "The attached rule emission may create a fact that this "
                    "sentence does not justify.",
                ),
                "incorrect_fact_field": (
                    "fact_emission_mapping",
                    "The attached fact type or field mapping may not preserve "
                    "the sentence's intended semantics.",
                ),
                "missing_fact_context": (
                    "fact_context_boundary",
                    "The attached fact may omit an identity, qualifier, role, "
                    "time, or other discriminator needed by downstream "
                    "reasoning.",
                ),
            }[defect.kind]
            add(
                kind=kind,
                claim=claim,
                observations=(
                    human_observation,
                    (
                        f"emitted {fact['type']} from {fact['source']} with "
                        f"fields {json.dumps(fact['fields'], sort_keys=True)}"
                    ),
                    (
                        "the review is attached to the immutable fact snapshot "
                        f"at index {attachment.index}"
                    ),
                ),
                attachment=attachment,
                premise=None,
                fact=fact,
            )

        if defect.kind == "missing_cross_slot_constraint":
            for slots in _duplicate_bindings(candidate):
                add(
                    kind="missing_distinct_predicate",
                    claim=(
                        "A distinct predicate may be missing between slots "
                        + ", ".join(slots)
                        + "."
                    ),
                    observations=(
                        human_observation,
                        "the generator selected the same filler for these roles: "
                        + ", ".join(slots),
                    ),
                    attachment=attachment,
                    premise=premise,
                )

        if defect.kind in {
            "another_rule_interfered",
            "intended_rule_did_not_fire",
        }:
            co_firing = sorted(
                {
                    match.rule_id
                    for match in candidate.actual_matches
                    if match.rule_id != candidate.target_rule
                }
            )
            if candidate.target_status == "shadowed":
                add(
                    kind="shadowing_boundary",
                    claim=(
                        "The target rule's specificity or overlap boundary may "
                        "allow another rule to shadow it."
                    ),
                    observations=(
                        human_observation,
                        "the ordinary matcher marked the target as shadowed",
                        "co-firing rules: " + (", ".join(co_firing) or "none"),
                    ),
                    attachment=attachment,
                    premise=premise,
                )
            elif (
                defect.kind == "another_rule_interfered"
                and co_firing
                and candidate.collisions
            ):
                add(
                    kind="cofiring_overlap_boundary",
                    claim=(
                        "The target and co-firing rule premises may overlap "
                        "without a sound specificity boundary."
                    ),
                    observations=(
                        human_observation,
                        "co-firing rules: " + ", ".join(co_firing),
                        f"the fact store reported {len(candidate.collisions)} collision(s)",
                    ),
                    attachment=attachment,
                    premise=premise,
                )

        if defect.kind == "wrong_morphology_agreement" and premise is not None:
            add(
                kind="morphology_or_realizer_boundary",
                claim=(
                    "The attached slot's morphology declaration or generation "
                    "realizer may not enforce the intended surface form."
                ),
                observations=(
                    human_observation,
                    f"the generated binding was {premise.binding!r}",
                    f"the matcher evaluated {premise.expression!r}",
                ),
                attachment=attachment,
                premise=premise,
            )

        if defect.kind == "wrong_lexical_sense" and premise is not None:
            add(
                kind="lexical_sense_boundary",
                claim=(
                    "The attached lexicon sense or slot gate may not represent "
                    "the intended use of this filler."
                ),
                observations=(
                    human_observation,
                    f"the generated binding was {premise.binding!r}",
                    f"the matcher evaluated {premise.expression!r}",
                ),
                attachment=attachment,
                premise=premise,
            )

        if (
            defect.kind == "generator_realization_defect"
            and premise is not None
            and premise.slot is not None
        ):
            add(
                kind="slot_realizer_contract",
                claim=(
                    f"The realizer for slot {premise.slot!r} may disagree with "
                    "the attached matcher premise."
                ),
                observations=(
                    human_observation,
                    f"the requested binding was "
                    f"{candidate.requested_bindings.get(premise.slot)!r}",
                    f"the target result was {candidate.target_status!r}",
                ),
                attachment=attachment,
                premise=premise,
            )

    return tuple(out)
