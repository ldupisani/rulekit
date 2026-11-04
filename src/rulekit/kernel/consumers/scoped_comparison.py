"""Aggregate affine comparisons without discarding activity or ordinal scope."""

from math import isfinite

from . import consumer
from ..composition_evidence import closed_evidence, finish_batch_answer
from .indexed_path import ordinal_index
from ..affine_graph import AffineGraph, AffineError
from ..answer import Answer
from ..evaluate import evaluate
from ..model import BatchEvidence, Relation, Quantity
from ..rate_calculation import convert_calendar_duration
from ..reference_identity import reference_from_unit, constrains
from ..totals import _sign


@consumer("scoped-comparison")
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    operands = []
    anchors, links = [], []
    mode = ctx.query["operation"]
    if mode == "duration-sum":
        known = [r for r in rows if r.kind == "duration-amount"]
        relative = [r for r in rows if r.kind == "duration-relative"]
        if len(known) != 1 or len(relative) != 1 or len(rows) != 2:
            return decline(
                "a combined activity duration needs one anchor and one comparable participant"
            )
        base, edge = known[0], relative[0]
        if (
            base.verb != edge.verb
            or base.provenance.sentence >= edge.provenance.sentence
            or edge.entity_ref == base.entity_ref
            or edge.entity_ref.owner != base.entity_ref
            or edge.container_ref
            and edge.container_ref != base.entity_ref
        ):
            return decline(
                "the relative duration must identify the same activity and its preceding participant"
            )
        amount = convert_calendar_duration(
            edge.value,
            edge.measure,
            base.measure,
            ctx.reg,
            ctx.log,
            source="relative-activity-unit",
        )
        if amount is None:
            return decline("the activity durations require compatible units")
        anchors = [(base.entity_ref, base.value)]
        links = [(edge.entity_ref, base.entity_ref, 1.0, edge.sign * amount)]
        operands = [(base, [base.value]), (edge, [edge.value])]
        requested = [(base.entity_ref, 1), (edge.entity_ref, 1)]
    elif mode == "age-difference":
        relations = list(ctx.store.by_kind(Relation))
        quantities = list(ctx.store.by_kind(Quantity))
        populations = [r for r in rows if r.kind == "comparison-population"]
        reports = [r for r in rows if r.kind == "comparison-report"]
        if (
            not relations
            or len(populations) > 1
            or len(reports) > 1
            or len(rows) != len(populations) + len(reports)
            or reports
            and not populations
        ):
            return decline(
                "an age difference needs one fully read graph of compatible comparisons"
            )
        for r in relations:
            if (
                r.factor != 1
                or r.subject_offset
                or r.standard_offset
                or r.measure_qualifier
                or r.subject_ref == r.standard_ref
                or r.provenance.assumption
            ):
                return decline(
                    "age comparisons must identify distinct participants and the same dimension"
                )
            value = convert_calendar_duration(
                r.offset,
                r.measure,
                ctx.query["measure"],
                ctx.reg,
                ctx.log,
                source="relative-age-unit",
            )
            if value is None:
                return decline("age differences need convertible duration units")
            links.append((r.subject_ref, r.standard_ref, 1.0, value))
            operands.append((r, [abs(r.offset)]))
        nodes = {node for a, b, _, _ in links for node in (a, b)}
        if populations and (
            populations[0].value != len(nodes)
            or any(not node.resolved for node in nodes)
        ):
            return decline("the stated population must match the compared participants")
        if populations:
            operands.append((populations[0], [populations[0].value]))
        for q in quantities:
            if q.entity_ref not in nodes or not ctx.reg.word_in_category(
                q.measure, "age_measure"
            ):
                return decline("an additional quantity lies outside the compared ages")
            value = convert_calendar_duration(
                q.value,
                q.measure,
                ctx.query["measure"],
                ctx.reg,
                ctx.log,
                source="observed-age-unit",
            )
            if value is None:
                return decline("observed ages need compatible units")
            anchors.append((q.entity_ref, value))
            if q.provenance.source != "synth/relation":
                operands.append((q, [q.value]))
        rows += relations + quantities
        a = reference_from_unit(ctx.match.slots["a"])
        b = reference_from_unit(ctx.match.slots["b"])
        if a == b:
            return decline("an age difference needs two distinct resolved participants")
        sign = _sign(ctx.query["direction"], ctx.reg, strict=True)
        if sign not in (-1, 1):
            return decline("the directed comparison needs an explicit age direction")
        requested = [(a, sign), (b, -sign)]
    elif mode == "indexed-mean":
        participants = [r for r in rows if r.kind == "indexed-participants"]
        ranges = [r for r in rows if r.kind == "indexed-range"]
        uniform = [r for r in rows if r.kind == "indexed-uniform"]
        relations = [r for r in rows if r.kind == "indexed-relation"]
        if (
            len(ranges) != 1
            or len(uniform) != 1
            or len(participants) > 1
            or not relations
            or len(rows) != len(participants) + 2 + len(relations)
        ):
            return decline(
                "an indexed average needs an exhaustive range, baseline and one comparison per position"
            )
        span, base = ranges[0], uniform[0]
        n = span.value
        if not isfinite(n) or n <= 0 or not float(n).is_integer():
            return decline("the indexed range must be a positive whole count")
        n = int(n)
        if (
            span.measure != ctx.query["period"]
            or base.marker != span.measure
            or len(relations) != n
            or any(r.marker != span.measure for r in relations)
        ):
            return decline(
                "the comparisons and requested average must cover the same complete period range"
            )

        def measure(row):
            mapped = (
                row.verb
                if ctx.reg.word_in_category(row.verb, "self_named_count_action")
                else None
            )
            return (
                mapped
                if ctx.reg.word_in_category(row.measure, "repetition_alias_unit")
                else row.measure
            )

        if measure(base) != ctx.query["measure"] or any(
            measure(r) != ctx.query["measure"] for r in relations
        ):
            return decline("all performances need the requested activity count unit")
        target = reference_from_unit(ctx.match.slots["who"])
        pair = {target, base.entity_ref}
        if len(pair) != 2 or any(
            {r.entity_ref, r.container_ref} != pair for r in relations
        ):
            return decline(
                "the indexed comparisons must identify the same two participants"
            )
        if participants and (
            {participants[0].container, participants[0].acquisition}
            != {ref.head for ref in pair}
            or not constrains(span.entity_ref, participants[0].entity_ref)
        ):
            return decline("the activity participants must match the comparison graph")
        positions = []
        for r in relations:
            index = ordinal_index(r.attribute, ctx.reg)
            if ctx.reg.word_in_category(r.attribute, "holder_terminal_order"):
                index = n
            positions.append(index)
            links.append(
                (
                    (r.entity_ref, index),
                    (r.container_ref, index),
                    r.fraction,
                    r.value * r.sign,
                )
            )
            operands.append((r, [r.value if r.sign else r.fraction]))
        if set(positions) != set(range(1, n + 1)):
            return decline("each indexed position needs exactly one comparison")
        anchors = [((base.entity_ref, i), base.value) for i in range(1, n + 1)]
        operands += [(span, [span.value]), (base, [base.value])]
        requested = [((target, i), 1.0 / n) for i in range(1, n + 1)]
    else:
        return decline("the comparison aggregation is not declared")
    if (
        any(r.provenance.assumption for r in rows if not isinstance(r, Quantity))
        and mode != "indexed-mean"
    ):
        return decline("the comparisons must be asserted in the supplied account")
    if not closed_evidence(ctx, rows, operands):
        return decline(
            "every amount, participant and comparison condition must belong to the account"
        )
    try:
        graph = AffineGraph(anchors, links, ctx.log)
        if mode != "age-difference":
            for node in graph.forms:
                value = graph.value(node)
                if (
                    value < 0
                    or mode == "indexed-mean"
                    and not float(value).is_integer()
                ):
                    return decline(
                        "computed amounts must be nonnegative, with whole discrete performances"
                    )
        value = graph.linear(requested)
    except AffineError as error:
        return decline(str(error))
    if value < 0:
        return decline("the requested directed difference has the opposite direction")
    return finish_batch_answer(
        ctx,
        rows,
        value,
        "resolve the scoped comparisons before applying the requested aggregate",
    )
