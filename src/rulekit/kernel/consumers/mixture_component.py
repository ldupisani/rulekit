"""Dimension-aware component accounting and explicitly licensed processes."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math

from . import ConsumerContext, consumer
from ..reference_identity import ReferenceIdentity, constrains, distinct_references, flat_reference


@dataclass
class _Sample:
    entity: str
    source: str
    total: float | None
    component: float
    measure: str
    dimension: str
    solvent: str
    entity_reference: ReferenceIdentity | None = None
    source_reference: ReferenceIdentity | None = None
    uniform: bool = False
    combined: bool = False


# Semantic dimensions, not vocabulary. Unit and basis membership live in packs.
_DIMENSIONS = (
    ("mass", "mass_measure", "mixture_mass_basis"),
    ("volume", "volume_measure", "mixture_volume_basis"),
    ("amount", "mixture_mole_measure", "mixture_mole_basis"),
    ("count", "mixture_count_measure", "mixture_count_basis"),
)
_NUMERIC_KINDS = {"sample", "share", "add", "withdraw", "selective-remove"}


@consumer("mixture-component")
def mixture_component(ctx: ConsumerContext):
    from ..answer import Answer, _ACCOUNTED_VALUE_KINDS
    from ..evaluate import evaluate
    from ..model import MixtureEvidence

    class Unsupported(ValueError):
        pass

    def require(ok, reason):
        if not ok:
            raise Unsupported(reason)

    def dimension(word, basis=False):
        matches = [name for name, unit_cat, basis_cat in _DIMENSIONS
                   if ctx.reg.word_in_category(word, basis_cat if basis else unit_cat)]
        require(len(matches) == 1, "mixture quantity needs an unambiguous measurement basis")
        return matches[0]

    def convert(value, unit, sample):
        require(dimension(unit) == sample.dimension, "mixture quantities have incompatible dimensions")
        factor = 1.0 if unit == sample.measure else ctx.reg.conversions.get((unit, sample.measure))
        require(factor is not None, "no compatible mixture unit conversion is declared")
        converted = value * factor
        require(math.isfinite(converted), "mixture conversion is not finite")
        return converted

    evidence = list(ctx.store.by_kind(MixtureEvidence))
    target_component = ctx.query.get("component")
    try:
        require(bool(evidence), "component amount needs measured mixture evidence")
        require(all(math.isfinite(e.value) and e.value >= 0 for e in evidence),
                "invalid mixture amount or fraction")
        samples = [e for e in evidence if e.kind == "sample"]
        shares = [e for e in evidence if e.kind == "share"]
        require(samples and len(samples) == len(shares), "each sample needs exactly one component share")
        def reference(row, role):
            return getattr(row, role + "_reference") or flat_reference(getattr(row, role))

        require(all(distinct_references(reference(a, "entity"), reference(b, "entity")) or
                    distinct_references(reference(a, "source"), reference(b, "source"))
                    for i, a in enumerate(samples) for b in samples[i + 1:]),
                "repeated material and holder do not identify distinct samples")
        expected = Counter((e.provenance.sentence, float(e.value)) for e in evidence if e.kind in _NUMERIC_KINDS)
        actual = Counter((r.sentence_index, float(u.features["value"]))
                         for r in (*ctx.premises, ctx.question) for u in r.units
                         if u.features.get("value_kind") in _ACCOUNTED_VALUE_KINDS)
        require(actual == expected, "a stated amount is outside the mixture calculation")
        evidence_sentences = {e.provenance.sentence for e in evidence}
        require(not any(r.sentence_index > min(evidence_sentences) and r.sentence_index not in evidence_sentences
                        for r in ctx.premises), "additional narration after mixture evidence needs an explicit update")

        def solvent_alias(sample, word):
            return ((sample.solvent and word == sample.solvent) or
                    (ctx.reg.word_in_category(sample.source, "aqueous_mixture") and
                     ctx.reg.word_in_category(word, "aqueous_solvent")))

        state = []
        used_shares = set()
        for sample in samples:
            candidates = [s for s in shares if (not s.entity or constrains(reference(s, "entity"), reference(sample, "entity")))
                          and (constrains(reference(s, "source"), reference(sample, "source")) or
                               (s.provenance.sentence > sample.provenance.sentence and solvent_alias(sample, s.source)))]
            require(len(candidates) == 1, "composition does not uniquely identify a measured sample")
            share = candidates[0]
            require(share.key() not in used_shares, "one composition cannot silently describe multiple samples")
            used_shares.add(share.key())
            require(share.component == target_component, "the requested component has no stated share")
            require(0 <= share.value <= 1, "invalid component percentage")
            dim = dimension(sample.measure)
            require(not share.basis or dimension(share.basis, True) == dim,
                    "component percentage and sample amount have incompatible bases")
            if dim == "count":
                require(ctx.reg.word_in_category(target_component, "discrete_mixture_component"),
                        "count basis needs a discrete component")
                require(float(sample.value).is_integer() and (sample.value * share.value).is_integer(),
                        "discrete mixture counts must be whole numbers")
            state.append(_Sample(sample.entity, sample.source, sample.value,
                                 sample.value * share.value, sample.measure, dim, sample.solvent,
                                 reference(sample, "entity"), reference(sample, "source")))
        require(len(used_shares) == len(shares), "unused mixture composition")
        last_initial = max(e.provenance.sentence for e in (*samples, *shares))

        def locate(source, entity="", source_ref=None, entity_ref=None):
            found = [s for s in state if (not entity or constrains(entity_ref or flat_reference(entity), s.entity_reference))
                     and (constrains(source_ref or flat_reference(source), s.source_reference) or (s.combined and
                          ctx.reg.word_in_category(source, "mixture_result_noun") and
                          not (source_ref or flat_reference(source)).described and
                          (source_ref or flat_reference(source)).resolved))]
            require(len(found) == 1, "process or question does not identify one active sample")
            return found[0]

        events = sorted((e for e in evidence if e.kind not in {"sample", "share"}),
                        key=lambda e: e.provenance.sentence)
        if ctx.query.get("result") == "recovered-amount":
            require(any(e.kind == "recover" and e.retained == target_component for e in events),
                    "the requested component needs an explicit recovery event")
        require(len({e.provenance.sentence for e in events}) == len(events), "process order is ambiguous")
        additive_volumes = False
        for event in events:
            require(event.provenance.sentence > last_initial,
                    "composition and sample measurements must precede supported process updates")
            if event.kind == "additive":
                additive_volumes = True
                continue
            sample = locate(event.source, event.entity, event.source_reference, event.entity_reference)
            if event.kind == "uniform":
                sample.uniform = True
            elif event.kind == "blend":
                other = locate(event.other_source, event.other_entity, event.other_source_reference, event.other_entity_reference)
                require(other is not sample, "a sample cannot be blended with itself")
                require(sample.total is not None and other.total is not None, "mixture total is unknown after separation")
                require(sample.dimension != "volume" or additive_volumes, "blending volumes needs explicit volume-additivity evidence")
                sample.component += convert(other.component, other.measure, sample)
                sample.total += convert(other.total, other.measure, sample)
                # No destination or uniformity is inferred merely from combination.
                sample.entity = ""
                sample.entity_reference = flat_reference("")
                sample.source = ""
                sample.source_reference = flat_reference("")
                sample.solvent = ""
                sample.combined = True
                sample.uniform = False
                state.remove(other)
            elif event.kind == "add":
                require(sample.total is not None, "mixture total is unknown after separation")
                require(sample.dimension != "volume" or additive_volumes, "adding volumes needs explicit volume-additivity evidence")
                amount = convert(event.value, event.measure, sample)
                sample.total += amount
                if event.component == target_component:
                    sample.component += amount
                sample.uniform = False
            elif event.kind == "withdraw":
                require(sample.uniform, "proportional withdrawal needs explicit uniform mixing")
                require(sample.total is not None and sample.total > 0, "withdrawal needs a positive known total")
                amount = convert(event.value, event.measure, sample)
                require(amount <= sample.total, "withdrawal exceeds the sample")
                sample.component *= (sample.total - amount) / sample.total
                sample.total -= amount
            elif event.kind == "recover":
                require(event.retained == target_component and event.component != target_component,
                        "separation needs explicit retention of the requested component")
                require(solvent_alias(sample, event.component), "removed solvent is not identified in this sample")
                # Component conservation is known, but other residue can remain.
                sample.total = None
                sample.uniform = False
            elif event.kind == "selective-remove":
                require(event.retained == target_component and event.component != target_component,
                        "selective removal needs explicit retention of the requested component")
                require(solvent_alias(sample, event.component), "removed solvent is not identified in this sample")
                require(sample.dimension != "volume" or additive_volumes, "selective volume removal needs volume-additivity evidence")
                require(sample.total is not None, "mixture total is unknown after separation")
                amount = convert(event.value, event.measure, sample)
                require(amount <= sample.total - sample.component,
                        "selective removal exceeds the available non-target material")
                sample.total -= amount
                sample.uniform = False
            else:
                raise Unsupported("unsupported mixture process")
            require(math.isfinite(sample.component) and
                    (sample.total is None or math.isfinite(sample.total)),
                    "mixture process result is not finite")
            if sample.dimension == "count":
                require(sample.component.is_integer() and (sample.total is None or sample.total.is_integer()),
                        "discrete mixture processes must preserve whole counts")
        require(len(state) == 1, "multiple samples need an explicit combination")
        sample = state[0]
        require(not ctx.query.get("required_dimension") or ctx.query["required_dimension"] == sample.dimension,
                "question has an incompatible measurement basis")
        if sample.dimension == "count":
            require(sample.component.is_integer() and (sample.total is None or sample.total.is_integer()),
                    "discrete mixture processes must preserve whole counts")
        if ctx.query.get("source"):
            refs = [ReferenceIdentity.from_dict(ctx.query[k]) if ctx.query.get(k) else None
                    for k in ("source_reference", "entity_reference")]
            require(locate(ctx.query["source"], ctx.query.get("entity", ""), *refs) is sample,
                    "the requested material is not the active sample")
        elif ctx.query.get("entity"):
            raw = ctx.query.get("entity_reference")
            query_ref = ReferenceIdentity.from_dict(raw) if raw else flat_reference(ctx.query["entity"])
            require(constrains(query_ref, sample.entity_reference), "the requested holder does not own the sample")
        if ctx.query.get("process"):
            removed = ctx.query.get("solvent")
            require(solvent_alias(sample, removed) and removed != target_component,
                    "the removed solvent is not identified or is the requested component")
            if ctx.query["process"] == "explicit-recovery":
                require(ctx.query.get("retained") == target_component,
                        "the question does not establish retention of the requested component")
            else:
                require(ctx.reg.word_in_category(sample.source, "aqueous_mixture") and
                        ctx.reg.word_in_category(target_component, "aqueous_evaporation_retained_component"),
                        "this evaporation process has no declared component-retention rule")
        if ctx.query.get("quantity_basis"):
            require(dimension(ctx.query["quantity_basis"], True) == sample.dimension,
                    "requested quantity has an incompatible basis")
        if ctx.query.get("result") == "percentage":
            require(sample.total is not None and sample.total > 0, "percentage needs a positive known mixture total")
            value = evaluate(f"100 * {sample.component} / {sample.total}", {}, ctx.log, source="mixture-component")
            explanation = f"{sample.component:g} / {sample.total:g} × 100 = {value:g}% ({sample.dimension})"
        else:
            unit = ctx.query.get("target_measure") or sample.measure
            require(dimension(unit) == sample.dimension, "requested quantity has an incompatible dimension")
            factor = 1.0 if unit == sample.measure else ctx.reg.conversions.get((sample.measure, unit))
            require(factor is not None, "no compatible mixture unit conversion is declared")
            value = evaluate(f"{sample.component} * {factor}", {}, ctx.log, source="mixture-component")
            explanation = f"{sample.component:g} {sample.measure} × {factor:g} = {value:g} {unit}"
        require(math.isfinite(value), "mixture calculation is not finite")
        ctx.log.consumed_mixture_keys.update(e.key() for e in evidence)
        convention = "" if all(s.basis for s in shares) else "; unspecified percentage uses the elementary sample-unit convention"
        from ..answer import AnswerAssumption
        assumptions = []
        if convention:
            assumptions.append(AnswerAssumption(
                "mixture-same-dimension-percentage",
                "An unspecified percentage uses the same measurement basis as the stated sample.",
                tuple(sorted({s.provenance.sentence for s in shares if not s.basis})),
            ))
        if ctx.query.get("process") and ctx.query["process"] != "explicit-recovery":
            assumptions.append(AnswerAssumption(
                "aqueous-component-retention",
                "The declared aqueous evaporation convention retains the requested component completely.",
                (ctx.question.sentence_index,),
            ))
        return Answer("number", float(value), explanation + convention,
                      assumptions=tuple(assumptions))
    except Unsupported as exc:
        return Answer("decline", None, str(exc))
