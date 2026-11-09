"""Complete finite calendar windows with direct and relative daily quantities."""

from .affine_graph import dependency_graph, AffineError
from .answer import Answer, AnswerAssumption
from .composition_evidence import closed_evidence, finish_batch_answer
from .evaluate import evaluate
from .predicate_compatibility import predicates_compatible
from .reference_identity import reference_from_unit


def explicit_calendar_total(ctx):
    from .model import BatchEvidence

    rows = list(ctx.store.by_kind(BatchEvidence))

    def fail(s):
        return Answer("decline", None, s)

    contexts = [r for r in rows if r.kind == "calendar-quantity-context"]
    direct = [r for r in rows if r.kind == "calendar-quantity-direct"]
    groups = [r for r in rows if r.kind == "calendar-quantity-group"]
    periods = [r for r in rows if r.kind == "calendar-quantity-period"]
    relative = [r for r in rows if r.kind == "calendar-quantity-relative"]
    if len(contexts) > 1 or len(rows) != len(contexts) + len(direct) + len(
        groups
    ) + len(periods) + len(relative):
        return fail("one complete, consistently scoped calendar account is required")
    site = reference_from_unit(ctx.match.slots["who"])
    contextual_units = (
        {
            q
            for q in contexts[0].container_ref.qualifiers
            if ctx.reg.word_in_category(q, "flowing_countable")
        }
        if contexts
        else set()
    )
    if contexts and (
        contexts[0].entity_ref != site or contextual_units != {ctx.query["measure"]}
    ):
        return fail("the question must identify the stated location and resource")
    if any(r.entity_ref is not None and r.entity_ref != site for r in rows):
        return fail("calendar quantities name different locations")
    indices = sorted(
        {a["weekday_index"] for a in ctx.reg.attrs.values() if "weekday_index" in a}
    )
    first = ctx.reg.attribute_value(ctx.query["first"], "weekday_index")
    last = ctx.reg.attribute_value(ctx.query["last"], "weekday_index")
    if first not in indices or last not in indices:
        return fail("the calendar window is not known")
    window = [
        (first + i) % len(indices)
        for i in range(int((last - first) % len(indices)) + 1)
    ]
    anchors = []
    edges = []
    defined = []
    operands = [(r, []) for r in contexts]
    approx = []
    maxima = []
    for r in direct + groups + periods + relative:
        if r.provenance.assumption or r.measure and r.measure != ctx.query["measure"]:
            return fail("all daily quantities must use the same resource")
        if r.verb and not predicates_compatible(
            r.verb, ctx.query["verb"], ctx.query["measure"], ctx.reg
        ):
            return fail("daily quantities describe another activity")
        marker = ctx.reg.attribute_value(r.marker, "weekday_index")
        if r in periods:
            start = ctx.reg.attribute_value(r.marker, "weekday_start")
            end = ctx.reg.attribute_value(r.marker, "weekday_end")
            if start not in indices or end not in indices:
                return fail("the named calendar group has no declared day boundaries")
            days = [
                (start + i) % len(indices)
                for i in range(int((end - start) % len(indices)) + 1)
            ]
            if ctx.reg.attribute_value(r.container, "calendar_day_unit") != 1:
                return fail("a grouped daily amount needs a day basis")
        else:
            days = [marker]
            if r in groups:
                days.append(ctx.reg.attribute_value(r.container, "weekday_index"))
        if any(day not in window for day in days) or len(set(days)) != len(days):
            return fail("each stated day must belong once to the requested window")
        defined.extend(days)
        operands.append((r, [r.value]))
        if r in relative:
            base = ctx.reg.attribute_value(r.acquisition, "weekday_index")
            if base not in window:
                return fail("a relative day references a day outside the window")
            factor = 1
            offset = r.value * r.sign
            if r.attribute == "fraction":
                factor = evaluate(
                    "1 + sign * fraction",
                    dict(sign=r.sign, fraction=r.value),
                    ctx.log,
                    source="calendar-relative-factor",
                )
                offset = 0
            edges.append((marker, base, factor, offset))
        else:
            anchors.extend((day, r.value) for day in days)
        if ctx.reg.word_in_category(r.attribute, "approximation_marker"):
            approx.append(r.provenance.sentence)
        if r.attribute == "maximum":
            maxima.extend(days)
    if sorted(defined) != sorted(window):
        return fail(
            "daily evidence must exhaust the requested window without gaps or overlaps"
        )
    try:
        graph = dependency_graph(anchors, edges, ctx.log)
        values = {day: graph.value(day) for day in window}
    except AffineError as error:
        return fail(str(error))
    if any(v < 0 or not float(v).is_integer() for v in values.values()):
        return fail("daily counts must be nonnegative whole numbers")
    if any(values[day] < max(values.values()) for day in maxima):
        return fail("the stated maximum day contradicts another daily amount")
    from .source_coverage import covered_temporal_annotation

    metadata = [f for f in ctx.store.facts if f not in rows]
    dates = {(r.provenance.sentence, r.marker) for r in direct + groups + relative}
    dates.update((r.provenance.sentence, r.container) for r in groups)
    if any(
        not covered_temporal_annotation(f, ctx.premises, site.head, dates)
        for f in metadata
    ):
        return fail("an additional event lies outside the calendar account")
    if not closed_evidence(ctx, [*rows, *metadata], operands):
        return fail("every daily amount, comparison and qualifier must be read")
    total = evaluate(
        " + ".join(str(v) for v in values.values()),
        {},
        ctx.log,
        source="finite-calendar-total",
    )
    assumptions = (
        (
            AnswerAssumption(
                "approximate-calendar-total",
                "This is an estimate using the stated approximate daily counts.",
                tuple(sorted(set(approx))),
            ),
        )
        if approx
        else ()
    )
    return finish_batch_answer(
        ctx,
        rows,
        total,
        ("Approximate total; " if approx else "")
        + "sum every day in the inclusive calendar window",
        assumptions=assumptions,
    )
