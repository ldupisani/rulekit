"""Compose a geometric capacity with ordered changes to its actual contents."""

from collections import Counter, defaultdict
from math import isfinite
from . import consumer
from ..affine_graph import AffineError, dependency_graph
from ..composition_evidence import finish_batch_answer
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
from ..reference_identity import (
    ReferenceIdentity, attributed_occurrences, constrains, distinct_references, reference_from_unit,
)
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
    openings = [r for r in rows if r.kind in {"content-opening-fraction", "content-opening-amount"}]
    measured = len(openings) == 1 and openings[0].kind == "content-opening-amount"
    dimensions = [r for r in rows if r.kind == "content-container-dimension"]
    axes = {_axis(ctx.reg, r.marker): r for r in dimensions}
    transitions = [r for r in rows if r.kind == "content-container-transition"]
    disturbances = [r for r in rows if r.kind == "content-container-disturbance"]
    if (
        len(contexts) > 1
        or len(openings) != 1
        or len(dimensions) != (0 if measured else 3)
        or not changes
        or len(rows)
        != len(contexts) + len(openings) + len(dimensions) + len(transitions) + len(disturbances)
        or len(ctx.store.facts) != len(rows) + len(changes) + len(mirrors)
        or ctx.store.collisions
        or ctx.store.quarantined
    ):
        return decline(
            "one complete measured container, fill and change stream is required"
        )
    opening = openings[0]
    context = contexts[0] if contexts else None
    identity = opening.container_ref or (context.container_ref if context else None)
    container = ctx.query_reference("container") or (ReferenceIdentity(identity.head) if identity else None)
    materials = {c.content for c in changes}
    content = ctx.query.get("content") or opening.attribute or (next(iter(materials)) if len(materials) == 1 else None)
    if (
        identity is None
        or not constrains(container, identity)
        or any(r.container_ref is None or not r.container_ref.resolved
               or not distinct_references(identity, r.container_ref) for r in disturbances)
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
        or not measured and set(axes) != AXIS_CATEGORIES.keys()
        or opening.attribute and opening.attribute != content
        or any(
            c.container != container.head or c.content != content
            for c in changes
        )
        or any(c.provenance.sentence <= opening.provenance.sentence for c in changes)
        or any(not isfinite(r.value) or r.value <= 0 for r in dimensions)
        or not isfinite(opening.value) or opening.value < 0
        or not measured and opening.value > 1
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
        targets = {
            reference_from_unit(u)
            for u in reading.units
            if u.sense() == "noun"
            and u.features.get("lemma") == change.container
            and ctx.reg.word_in_category(
                u.features.get("lemma", ""), "volumetric_container"
            )
        }
        if not targets:
            targets = {
                ref
                for u in reading.units
                if u.sense() == "pronoun"
                and (ref := reference_from_unit(u)).head == change.container
            }
        target = next(iter(targets)) if len(targets) == 1 else None
        if (
            target is None
            or not target.resolved
            or not (
                constrains(identity, target) or constrains(target, identity)
            )
        ):
            return decline("each content change needs the same identified container")
        container_refs.extend(targets)
    expected = defaultdict(Counter)
    if measured:
        expected[opening.provenance.sentence][opening.value] += 1
    for row in dimensions:
        expected[row.provenance.sentence][row.value] += 1
    for change in changes:
        if change.operation in {"remove_fraction", "remove_quantity", "add_quantity"} or change.explicit_factor:
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
    if measured:
        unit = ctx.query.get("unit") or opening.measure
        factor = conversion_factor(ctx.reg, opening.measure, unit, category="volume_measure")
        if factor is None:
            return decline("the opening and requested units must measure compatible volumes")
        amount = evaluate("opening * factor", {"opening": opening.value, "factor": factor},
                          ctx.log, source="content-opening-amount")
        outcome = _apply_changes(ctx, amount, changes, unit=unit, capacity=amount)
        if isinstance(outcome, Answer):
            return outcome
        amount, selected = outcome
        return finish_batch_answer(
            ctx, rows, amount,
            "apply the stated changes in order and select losses by their recorded attribution"
            if selected else f"apply the stated changes to the opening amount in {unit}s",
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
            output_unit=ctx.query.get("unit") or ctx.reg.formula_units.get("length"),
        ).value
    except (AffineError, PropertyError) as error:
        return decline(str(error))
    amount = evaluate(
        "capacity * share",
        {"capacity": capacity, "share": opening.value},
        ctx.log,
        source="fractional-capacity-fill",
    )
    outcome = _apply_changes(ctx, amount, changes, capacity=capacity)
    if isinstance(outcome, Answer):
        return outcome
    amount, selected = outcome
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    reason = (
        "apply the stated changes in order and select losses by their recorded attribution"
        if selected else
        "calculate the stated shape’s capacity, fill the stated fraction, then apply each change to current contents"
    )
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


def _apply_changes(ctx, amount, changes, *, unit=None, capacity=None):
    def decline(reason):
        return Answer("decline", None, reason)

    loss_events = [c for c in changes if c.operation in {"remove_fraction", "remove_quantity"}]
    actor_query = ctx.query_reference("actor")
    reason_query = ctx.query_reference("reason")
    selected = None
    if actor_query is not None:
        predicate = ctx.query.get("predicate")
        loss_events = [
            change for change in loss_events
            if change.provenance.attribution is None
            or change.provenance.attribution.predicate == predicate
        ]
        matches = attributed_occurrences(actor_query, [c.provenance.attribution for c in loss_events])
        if matches is None:
            return decline("the requested actor must uniquely identify one participant")
        selected = {loss_events[index].key() for index in matches}
    elif reason_query is not None:
        causes = [c.provenance.attribution.reason_entities if c.provenance.attribution else ()
                  for c in loss_events]
        if any(not refs or any(not ref.resolved for ref in refs) for refs in causes):
            return decline("the relevant loss events need explicitly identified causes")
        selected = {c.key() for c, refs in zip(loss_events, causes, strict=True)
                    if any(constrains(reason_query, ref) for ref in refs)}
    if selected == set():
        return decline("no measured losses have the requested attribution")

    losses = []
    for change in sorted(changes, key=lambda c: (c.provenance.sentence, c.occurrence or 0)):
        if change.provenance.assumption or not isfinite(change.value) or change.value < 0:
            return decline("content changes must be actual, finite and nonnegative")
        previous = amount
        if change.operation == "remove_fraction" and change.value <= 1:
            amount = evaluate("amount * (1 - share)", {"amount": amount, "share": change.value},
                              ctx.log, source="spill-current-contents")
        elif change.operation == "multiply_total":
            amount = evaluate("amount * factor", {"amount": amount, "factor": change.value},
                              ctx.log, source="scale-current-contents")
        elif change.operation in {"remove_quantity", "add_quantity"} and unit and change.measure:
            factor = conversion_factor(ctx.reg, change.measure, unit, category="volume_measure")
            if factor is None:
                return decline("each change needs a compatible volume unit")
            expression = "amount - value * factor" if change.operation == "remove_quantity" else "amount + value * factor"
            amount = evaluate(expression, {"amount": amount, "value": change.value, "factor": factor},
                              ctx.log, source="measured-content-change")
        else:
            return decline("the content operation needs an explicitly supported scope")
        if not isfinite(amount) or amount < 0:
            return decline("a content change cannot leave a negative or non-finite amount")
        if capacity is not None and amount > capacity:
            return decline("the resulting contents exceed capacity; overflow behavior is unspecified")
        if selected is not None and change.key() in selected:
            losses.append(evaluate("before - after", {"before": previous, "after": amount},
                                   ctx.log, source="attributed-content-loss"))
    if selected is not None:
        amount = float(len(losses)) if ctx.query.get("mode") == "event-count" else sum(losses)
    return amount, selected is not None
