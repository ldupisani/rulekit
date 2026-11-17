"""Compose explicitly scoped package, capacity and per-component requirements."""

from collections import Counter
from dataclasses import replace
from itertools import combinations
from math import isfinite
from . import consumer
from .indexed_path import ordinal_index
from ..affine_graph import AffineError, dependency_graph
from ..answer import Answer, AnswerAssumption
from ..model import BatchEvidence, Quantity
from ..quantity_ratios import quantity_through_ratios
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..reference_identity import ReferenceIdentity, constrains, reference_from_unit
from ..source_coverage import quantity_ledger_source_units
from ..predicate_compatibility import predicates_compatible
from ..rate_calculation import convert_units, convert_exact_duration
from ..evaluate import evaluate

KINDS = {
    "unit-plan-context",
    "unit-plan-object",
    "unit-plan-link",
    "unit-plan-anchor",
    "unit-plan-supplement",
    "unit-plan-exact",
    "unit-plan-cancellation",
}


@consumer(
    "unit-plan",
    applicable=lambda s: any(r.kind in KINDS for r in s.by_kind(BatchEvidence)),
)
def consume(ctx):
    def fail(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    if len(rows) != len(ctx.store.facts) or any(
        r.kind not in KINDS or r.provenance.assumption for r in rows
    ):
        return fail("every fact must belong to one explicit quantity plan")
    who = ctx.match.slots.get("who")
    owners = {r.entity_ref for r in rows if r.entity_ref is not None}
    actor = reference_from_unit(who) if who is not None else next(iter(owners)) if len(owners) == 1 else None
    if actor is None or not actor.resolved or any(
        r.entity_ref is not None and r.entity_ref != actor for r in rows
    ):
        return fail("the plan and question must identify the same participant")
    links = [r for r in rows if r.kind == "unit-plan-link"]
    anchors = [r for r in rows if r.kind == "unit-plan-anchor"]
    objects = [r for r in rows if r.kind == "unit-plan-object"]
    extras = [r for r in rows if r.kind == "unit-plan-supplement"]
    exact = [r for r in rows if r.kind == "unit-plan-exact"]
    cancellations = [r for r in rows if r.kind == "unit-plan-cancellation"]
    if (
        not links
        or len(anchors) + bool(objects) > 1
        or len(objects) > 1
        or len(exact) > 1
    ):
        return fail(
            "the plan needs one starting amount and a connected set of unit ratios"
        )
    mode = ctx.query["mode"]
    capacity_mode = mode in {"capacity", "capacity-loss"}
    if cancellations and not capacity_mode:
        return fail("only a scheduled capacity can account for cancellations")
    if any(r.marker == "capacity" for r in links) and not capacity_mode and not exact:
        return fail(
            "capacity is not evidence of actual usage without an explicit exact-demand statement"
        )
    operands = []
    assumptions = []
    for r in rows:
        if (
            r.kind in {"unit-plan-link", "unit-plan-anchor"}
            and any(
                ctx.reg.word_in_category(r.measure, category)
                for category in (
                    "quantity_container",
                    "allocation_recipient",
                    "scheduled_event",
                )
            )
            and not float(r.value).is_integer()
        ):
            return fail(
                "container, recipient and operation counts must be whole numbers"
            )
        operands.append(
            (
                r,
                (
                    ([r.value] + ([r.per_member] if r.per_member else []))
                    if r.kind
                    in {"unit-plan-link", "unit-plan-anchor", "unit-plan-supplement", "unit-plan-cancellation"}
                    else []
                ),
            )
        )
    basis = None
    periods = None
    if objects:
        obj = objects[0]
        activity = ctx.query.get("verb")
        if (
            not activity
            or any(r.verb != activity for r in links + extras)
            or (obj.verb and obj.verb != activity)
        ):
            return fail("component requirements must describe the requested activity")
        first = links[0]
        part = first.container
        plural = ctx.reg.singular_to_plural.get(part, part)
        attribute = ctx.reg.part_counts.get(
            part, ctx.reg.part_counts.get(plural, plural)
        )
        count = ctx.reg.attribute_value(obj.measure, attribute)
        if count is None or count < 0 or not float(count).is_integer():
            return fail("the object has no known count for the requested component")
        start = (part, obj.measure)
        value = count
        for r in extras:
            if r.container_ref is not None:
                stated = r.container_ref
                if not predicates_compatible(
                    stated.head, obj.measure, obj.measure, ctx.reg
                ) or not constrains(
                    replace(stated, head=obj.container_ref.head), obj.container_ref
                ):
                    return fail("the additional requirement names another object")
        assumptions.append(
            AnswerAssumption(
                "ordinary-component-count",
                f"Use the ordinary {count:g} {plural} of the stated {obj.measure}; no missing or additional components are stated.",
                (obj.provenance.sentence,),
            )
        )
    elif anchors:
        start = (anchors[0].measure, anchors[0].attribute)
        value = anchors[0].value
    elif mode == "capacity-loss" or mode == "capacity" and "span_value" in ctx.query:
        basis = next(
            (
                r
                for r in links
                if ctx.reg.word_in_category(r.container, "duration_measure")
            ),
            None,
        )
        if basis is None:
            return fail("the carrying capacity needs a stated schedule period")
        if mode == "capacity-loss":
            if not cancellations:
                return fail("a lost capacity needs an explicit cancellation")
            start = (basis.container, basis.acquisition)
            value = 0.0
        else:
            duration = convert_exact_duration(
                float(ctx.query["span_value"]),
                ctx.query["span_unit"],
                basis.container,
                ctx.reg,
                ctx.log,
                source="capacity-complete-periods",
            )
            if duration is None:
                return fail(
                    "the capacity horizon and schedule need compatible duration units"
                )
            periods = duration / (basis.per_member or 1)
            if periods <= 0 or not float(periods).is_integer():
                return fail(
                    "the capacity horizon must contain complete stated schedule periods"
                )
            start = (basis.container, ctx.query["basis_resource"])
            value = duration
    else:
        return fail("a stated starting quantity or capacity horizon is required")
    target = (
        ctx.query.get("measure") or links[-1].measure,
        ctx.query.get("resource") or links[-1].attribute,
    )
    if exact and (
        exact[0].measure != target[1]
        or any(r.measure != target[1] for r in rows if r.kind == "unit-plan-context")
    ):
        return fail(
            "the plan context, exact use and question must name the same application"
        )
    resources = {r.attribute for r in links} | {r.acquisition for r in links}
    if any(
        r.kind == "unit-plan-context"
        and r.attribute == "limited-resource"
        and r.container not in resources
        for r in rows
    ):
        return fail("the limited resource and quantity plan must agree")
    if objects and objects[0].attribute and objects[0].attribute != target[1]:
        return fail("the object assessment and requirement name different materials")
    if objects and ctx.query.get("scope"):
        stated = ctx.query_reference("scope")
        obj = objects[0]
        if not predicates_compatible(
            stated.head, obj.measure, obj.measure, ctx.reg
        ) or not constrains(
            replace(stated, head=obj.container_ref.head), obj.container_ref
        ):
            return fail("the question asks about another object")
    ratios = []
    for r in links:
        source_resource = r.acquisition or (objects[0].measure if objects else "")
        ratios.append(
            (
                (r.measure, r.attribute),
                (r.container, source_resource),
                r.value,
                r.per_member or 1,
            )
        )
    try:
        result = quantity_through_ratios(value, start, target, ratios, ctx.reg, ctx.log)
        if cancellations:
            if basis is None or (basis.per_member or 1) != 1:
                return fail("each cancellation must identify one complete scheduled period")
            by_period = Counter()
            selected = []
            reason = ctx.query_reference("reason")
            for row in cancellations:
                index = ordinal_index(row.marker, ctx.reg)
                if (row.measure != basis.measure or row.container != basis.container
                        or index is None or index < 1 or periods is not None and index > periods
                        or index in by_period
                        or row.value <= 0 or not float(row.value).is_integer()
                        or row.provenance.sentence <= basis.provenance.sentence):
                    return fail("each cancellation must identify counted operations in the schedule")
                by_period[index] += row.value
                attribution = row.provenance.attribution
                if reason is None or attribution is not None and any(
                    constrains(reason, cause) for cause in attribution.reason_entities
                ):
                    selected.append(row.value)
            if any(count > basis.value for count in by_period.values()) or not selected:
                return fail("cancellations must fit the schedule and identify the requested cause")
            loss = quantity_through_ratios(
                sum(selected), (basis.measure, basis.attribute), target, ratios, ctx.reg, ctx.log,
            )
            result = loss if mode == "capacity-loss" else result - loss
    except AffineError as error:
        return fail(str(error))
    for r in extras:
        if r.attribute != target[1]:
            return fail("additional requirements name another resource")
        amount = convert_units(
            r.value,
            r.measure,
            target[0],
            ctx.reg,
            ctx.log,
            source="additional-plan-unit",
        )
        if amount is None:
            return fail("additional requirements need compatible units")
        result = evaluate(
            "required + extra",
            dict(required=result, extra=amount),
            ctx.log,
            source="additional-plan-amount",
        )
    if (
        not ctx.reg.word_in_category(target[0], "measure_unit")
        and not float(result).is_integer()
    ):
        return fail("the plan does not determine a whole count of discrete outputs")
    if mode == "capacity":
        assumptions.append(
            AnswerAssumption(
                "full-capacity-plan",
                "The answer uses all stated supply or carrying capacity; a stated schedule repeats over the requested complete periods.",
                tuple(sorted({r.provenance.sentence for r in links})),
            )
        )
    if not closed_evidence(ctx, rows, operands):
        return fail("every unit ratio, amount, object and condition must be read")
    return finish_batch_answer(
        ctx,
        rows,
        result,
        "compose the stated unit ratios, then add separate requirements",
        assumptions=assumptions,
    )


@consumer(
    "per-item-requirement",
    applicable=lambda s: any(r.kind == "unit-plan-item-exception" for r in s.by_kind(BatchEvidence)),
)
def per_item_requirement(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    rates = [row for row in rows if row.kind == "unit-plan-item-exception"]
    if len(rates) != 1:
        return decline("the plan needs one default requirement and one exception")
    rate = rates[0]
    if rate.measure != ctx.query["measure"] or rate.marker and rate.attribute != rate.measure:
        return decline("the default, exception and question must use the same resource")

    quantities = list(ctx.store.by_kind(Quantity))
    dispatch = [row for row in rows if row is not rate]
    population = [*dispatch, *quantities]
    actors = {row.entity_ref for row in population}
    actor = ctx.query_reference()
    if "entity" not in ctx.query and len(actors) == 1:
        actor = next(iter(actors))
    if (actor is None or not actor.resolved or actors != {actor}
            or any(row.provenance.assumption or row.provenance.sentence >= rate.provenance.sentence
                   for row in population)):
        return decline("the counts and requirement must describe one previously established plan")

    if dispatch and quantities:
        return decline("mailing counts and separate holdings do not establish one item population")
    if dispatch:
        result = _dispatch_population(ctx, dispatch, rate)
        if isinstance(result, Answer):
            return result
        counts, operands = result
        covered = {}
    else:
        result = _held_population(ctx, quantities)
        if isinstance(result, Answer):
            return result
        counts, covered = result
        operands = [(row, [row.value]) for row in quantities]

    exception = rate.container_ref
    if exception is None or not exception.resolved:
        return decline("the exception must refer to one item in the plan")
    scope = rate.acquisition or (exception.head if not dispatch else None)
    if scope and any(ref.head != scope for ref, _ in counts):
        return decline("the stated item class must cover the whole plan")
    if any(not isfinite(value) or value < 0 or not float(value).is_integer()
           for value in [rate.value, rate.subtotal, *(count for _, count in counts)]):
        return decline("item counts and resource requirements must be nonnegative whole numbers")

    matching = [count for ref, count in counts if constrains(exception, ref) and count > 0]
    if not matching or not rate.per_member and matching != [1]:
        return decline("the exception must identify exactly one item")
    operands.append((rate, [rate.value, rate.subtotal] + ([rate.per_member] if rate.per_member else [])))
    evidence = [*rows, *quantities]
    if not closed_evidence(ctx, evidence, operands, covered=covered):
        return decline("all item counts and resource requirements must be read")

    value = evaluate("(items - 1) * standard + exception",
                     dict(items=sum(count for _, count in counts), standard=rate.value, exception=rate.subtotal),
                     ctx.log, source="per-item-requirement-with-exception")
    return finish_batch_answer(ctx, evidence, value, "apply the default to each item and replace the stated exception")


def _held_population(ctx, quantities):
    if not quantities or len({row.provenance.sentence for row in quantities}) != 1:
        return Answer("decline", None, "one stated count or coordinated count list must establish the items")
    if any(not row.is_state or row.time or row.provenance.distributive or row.content_ref
           or not ctx.reg.word_in_category(row.verb, "plain_have_state")
           for row in quantities):
        return Answer("decline", None, "the plan needs held items with an explicit count")

    counts = [
        (row.measure_ref or ReferenceIdentity(
            row.measure.split("[", 1)[0], qualifiers=(row.measure_qualifier,) if row.measure_qualifier else (),
        ), row.value)
        for row in quantities
    ]
    if any(not ref.resolved for ref, _ in counts) or any(
        constrains(first, second) or constrains(second, first)
        for (first, _), (second, _) in combinations(counts, 2)
    ):
        return Answer("decline", None, "overlapping item counts do not establish a single population")

    sentence = quantities[0].provenance.sentence
    reading = next((reading for reading in ctx.premises if reading.sentence_index == sentence), None)
    covered = {sentence: quantity_ledger_source_units(reading, quantities, ctx.reg)} if reading is not None else {}
    return counts, covered


def _dispatch_population(ctx, rows, rate):
    grouped = {
        kind: [row for row in rows if row.kind == "unit-plan-dispatch-" + kind]
        for kind in ("context", "recipients", "document", "relation")
    }
    contexts, recipients, documents, relations = grouped.values()
    if (len(rows) != sum(map(len, grouped.values())) or len(contexts) > 1
            or any(row.measure != rate.measure for row in contexts)):
        return Answer("decline", None, "mailing evidence must belong to one complete plan for the requested resource")

    totals = Counter(row.measure for row in documents)
    identities = [row.container_ref for row in documents]
    if any(ref is None or not ref.resolved for ref in identities) or len(set(identities)) != len(identities):
        return Answer("decline", None, "separate documents need distinct identities")
    for row in recipients:
        if row.measure in totals or not row.members or len(set(row.members)) != len(row.members):
            return Answer("decline", None, "recipient lists must identify distinct documents")
        totals[row.measure] = len(row.members)
    targets = [row.measure for row in relations]
    if len(set(targets)) != len(targets) or set(targets) & totals.keys():
        return Answer("decline", None, "every relative document count must be unique")
    for row in relations:
        if (row.container_ref is None or row.container_ref.owner or row.container_ref.label
                or row.container not in totals and row.container not in targets):
            return Answer("decline", None, "the comparative standard must identify a known document class")
    try:
        graph = dependency_graph(
            totals.items(),
            [(row.measure, row.container, row.fraction, row.sign * row.value) for row in relations],
            ctx.log,
        )
        other_classes = [row.measure for row in recipients] + targets
        counts = [(ref, 1) for ref in identities]
        counts.extend((ReferenceIdentity(item), graph.value(item)) for item in other_classes)
    except AffineError as error:
        return Answer("decline", None, str(error))
    operands = [(row, [row.value] if row.sign else [row.fraction]) for row in relations]
    return counts, operands
