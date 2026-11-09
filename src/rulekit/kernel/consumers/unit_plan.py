"""Compose explicitly scoped package, capacity and per-component requirements."""

from dataclasses import replace
from . import consumer
from ..answer import Answer, AnswerAssumption
from ..model import BatchEvidence
from ..quantity_ratios import quantity_through_ratios
from ..affine_graph import AffineError
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..reference_identity import reference_from_unit, constrains
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
    actor = reference_from_unit(ctx.match.slots["who"])
    if not actor.resolved or any(
        r.entity_ref is not None and r.entity_ref != actor for r in rows
    ):
        return fail("the plan and question must identify the same participant")
    links = [r for r in rows if r.kind == "unit-plan-link"]
    anchors = [r for r in rows if r.kind == "unit-plan-anchor"]
    objects = [r for r in rows if r.kind == "unit-plan-object"]
    extras = [r for r in rows if r.kind == "unit-plan-supplement"]
    exact = [r for r in rows if r.kind == "unit-plan-exact"]
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
    if any(r.marker == "capacity" for r in links) and mode != "capacity" and not exact:
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
                    in {"unit-plan-link", "unit-plan-anchor", "unit-plan-supplement"}
                    else []
                ),
            )
        )
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
    elif "span_value" in ctx.query and mode == "capacity":
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
