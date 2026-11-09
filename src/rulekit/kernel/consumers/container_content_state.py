"""Compose a geometric capacity with ordered changes to its actual contents."""

from collections import Counter, defaultdict
from math import isfinite
from . import consumer
from ..affine_graph import AffineError, dependency_graph
from ..answer import (
    Answer,
    AnswerAssumption,
    ClarificationOption,
    ClarificationRequest,
    SemanticNode,
)
from ..dimensions import conversion_factor
from ..evaluate import evaluate
from ..model import BatchEvidence, MeasuredContentChange, ContainerContent
from ..numeric_evidence import audit_numeric_mentions
from ..properties import Measurement, evaluate_property
from ...data.properties import PropertyError
from ..reference_identity import reference_from_unit, constrains
from ..source_coverage import uncovered_document_units


AXIS_CATEGORIES = {
    "length": "length_dimension_adjective",
    "width": "width_dimension_adjective",
    "height": "height_dimension_adjective",
}


def _axis(reg, adjective):
    if adjective in AXIS_CATEGORIES:
        return adjective
    return next(
        (axis for axis, category in AXIS_CATEGORIES.items()
         if reg.word_in_category(adjective, category)),
        None,
    )


@consumer("container-content-state")
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    changes = list(ctx.store.by_kind(MeasuredContentChange))
    mirrors = list(ctx.store.by_kind(ContainerContent))
    if any(
        not any(
            c.container == m.container
            and c.content == m.content
            and c.operation == m.operation
            and c.occurrence == m.occurrence
            for c in changes
        )
        for m in mirrors
    ):
        return decline("an additional content stream lies outside the changes")
    contexts = [r for r in rows if r.kind == "content-container-context"]
    openings = [r for r in rows if r.kind == "content-opening-fraction"]
    dimensions = [r for r in rows if r.kind == "content-container-dimension"]
    axes = {_axis(ctx.reg, r.marker): r for r in dimensions}
    transitions = [r for r in rows if r.kind == "content-container-transition"]
    if (
        len(contexts) > 1
        or len(openings) != 1
        or len(dimensions) != 3
        or not changes
        or len(rows)
        != len(contexts) + len(openings) + len(dimensions) + len(transitions)
        or len(ctx.store.facts) != len(rows) + len(changes) + len(mirrors)
        or ctx.store.collisions
        or ctx.store.quarantined
    ):
        return decline(
            "one complete measured container, fill and change stream is required"
        )
    opening = openings[0]
    context = contexts[0] if contexts else None
    container = reference_from_unit(ctx.match.slots["container"])
    identity = opening.container_ref or (context.container_ref if context else None)
    if (
        identity is None
        or not constrains(container, identity)
        or context is not None
        and (
            opening.entity_ref != context.entity_ref
            or not constrains(context.container_ref, identity)
            or opening.provenance.sentence <= context.provenance.sentence
        )
        or any(
            r.entity_ref != opening.entity_ref
            or not opening.provenance.sentence
            < r.provenance.sentence
            < min(c.provenance.sentence for c in changes)
            for r in transitions
        )
        or any(
            not constrains(container, r.container_ref)
            or not (
                constrains(identity, r.container_ref)
                or constrains(r.container_ref, identity)
            )
            for r in dimensions
        )
        or set(axes) != AXIS_CATEGORIES.keys()
        or any(
            c.container != container.head or c.content != ctx.query["content"]
            for c in changes
        )
        or any(c.provenance.sentence <= opening.provenance.sentence for c in changes)
        or any(not isfinite(r.value) or r.value <= 0 for r in dimensions)
        or not 0 <= opening.value <= 1
    ):
        return decline(
            "all dimensions and ordered changes must belong to the same container and contents"
        )
    container_refs = [
        identity,
        container,
        *(r.container_ref for r in dimensions),
    ]
    for change in changes:
        reading = next(
            r for r in ctx.premises if r.sentence_index == change.provenance.sentence
        )
        targets = [
            reference_from_unit(u)
            for u in reading.units
            if u.sense() == "noun"
            and u.features.get("lemma") == change.container
            and ctx.reg.word_in_category(
                u.features.get("lemma", ""), "volumetric_container"
            )
        ]
        if not targets:
            targets = [
                ref
                for u in reading.units
                if u.sense() == "pronoun"
                and (ref := reference_from_unit(u)).head == change.container
            ]
        if (
            len(targets) != 1
            or not targets[0].resolved
            or not (
                constrains(identity, targets[0]) or constrains(targets[0], identity)
            )
        ):
            return decline("each content change needs the same identified container")
        container_refs.extend(targets)
    expected = defaultdict(Counter)
    for row in dimensions:
        expected[row.provenance.sentence][row.value] += 1
    for change in changes:
        if change.operation == "remove_fraction" or change.explicit_factor:
            expected[change.provenance.sentence][change.value] += 1
    if uncovered_document_units(
        ctx.premises, ctx.question, ctx.match.consumed
    ) or audit_numeric_mentions(
        (*ctx.premises, ctx.question),
        expected,
        missing="missing",
        duplicate="duplicate",
    ):
        return decline(
            "every container dimension, fill, spill and subsequent change must be read"
        )
    descriptors = {q for ref in container_refs for q in ref.qualifiers}
    explicit = bool(descriptors) and all(
        ctx.reg.word_in_category(q, "rectangular_attribute") for q in descriptors
    )
    if descriptors and not explicit and ctx.interpretation != "rectangular-container":
        return Answer(
            "decline",
            None,
            "the container shape is needed to calculate capacity",
            clarification=ClarificationRequest(
                "Does the described container have a rectangular-prism capacity?",
                (
                    ClarificationOption(
                        "rectangular-container",
                        "Rectangular container",
                        "Use the stated dimensions as a rectangular prism.",
                        SemanticNode(
                            "container-shape", (("shape", dimensions[0].acquisition),)
                        ),
                    ),
                ),
            ),
        )
    measurements = {
        axis: Measurement(row.value, row.measure)
        for axis, row in axes.items()
        if row.measure
    }
    relative = [
        (axis, _axis(ctx.reg, row.attribute), row.value, 0)
        for axis, row in axes.items()
        if not row.measure
    ]
    try:
        if relative:
            unit = ctx.reg.formula_units.get("length")
            if unit is None:
                return decline("relative dimensions need a declared length unit")
            category = ctx.reg.formula_unit_categories.get("length")
            anchors = []
            for axis, measurement in measurements.items():
                factor = conversion_factor(ctx.reg, measurement.unit, unit, category=category)
                if factor is None:
                    return decline("relative dimensions need compatible length units")
                anchors.append((axis, evaluate(
                    "value * factor",
                    {"value": measurement.value, "factor": factor},
                    ctx.log,
                    source="relative-dimension-unit-conversion",
                )))
            graph = dependency_graph(anchors, relative, ctx.log)
            measurements = {axis: Measurement(graph.value(axis), unit) for axis in axes}
        capacity = evaluate_property(
            ctx.reg,
            dimensions[0].acquisition,
            "volume",
            measurements,
            ctx.log,
            output_unit=ctx.query["unit"],
        ).value
    except (AffineError, PropertyError) as error:
        return decline(str(error))
    amount = evaluate(
        "capacity * share",
        {"capacity": capacity, "share": opening.value},
        ctx.log,
        source="fractional-capacity-fill",
    )
    for change in sorted(
        changes, key=lambda c: (c.provenance.sentence, c.occurrence or 0)
    ):
        if not isfinite(change.value) or change.value < 0:
            return decline("content changes must be finite and nonnegative")
        if change.operation == "remove_fraction" and change.value <= 1:
            amount = evaluate(
                "amount * (1 - share)",
                {"amount": amount, "share": change.value},
                ctx.log,
                source="spill-current-contents",
            )
        elif change.operation == "multiply_total":
            amount = evaluate(
                "amount * factor",
                {"amount": amount, "factor": change.value},
                ctx.log,
                source="scale-current-contents",
            )
        else:
            return decline("the content operation needs an explicitly supported scope")
        if amount > capacity:
            return decline(
                "the resulting contents exceed capacity; overflow behavior is unspecified"
            )
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    reason = "calculate the stated shape’s capacity, fill the stated fraction, then apply each change to current contents"
    if not explicit:
        reason += "; interpreting the complete length, width and height as a rectangular prism"
    return Answer(
        "number",
        amount,
        reason,
        assumptions=(
            ()
            if explicit or ctx.interpretation == "rectangular-container"
            else (
                AnswerAssumption(
                    "rectangular-container",
                    "The stated length, width and height describe a rectangular prism.",
                    tuple(sorted({r.provenance.sentence for r in dimensions})),
                ),
            )
        ),
    )
