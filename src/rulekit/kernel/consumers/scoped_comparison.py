"""Aggregate affine comparisons without discarding activity or ordinal scope."""

from math import isfinite

from . import consumer
from ..composition_evidence import closed_evidence, finish_batch_answer
from .indexed_path import ordinal_index
from ..affine_graph import AffineGraph, AffineError
from ..answer import Answer
from ..evaluate import evaluate
from ..model import BatchEvidence, Relation, Quantity, VerbalRelation
from ..predicate_compatibility import predicate_concepts
from ..rate_calculation import convert_calendar_duration, convert_exact_duration
from ..reference_identity import reference_from_unit, constrains
from ..source_coverage import covered_temporal_annotation
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
        for q in ctx.store.by_kind(Quantity):
            if (q.time or q.measure_qualifier or q.provenance.assumption
                    or not ctx.reg.word_in_category(q.measure, "duration_measure")
                    or not ctx.reg.word_in_category(q.verb, "accumulated_activity_verb")):
                return decline("each quantity must be an asserted duration of the activity")
            rows.append(q)
        if len(rows) != 2:
            return decline("combined experience needs a duration for each of two participants")
        base, other = sorted(rows, key=lambda r: r.provenance.sentence)
        relative = isinstance(other, BatchEvidence) and other.kind == "duration-relative"
        if (
            isinstance(base, BatchEvidence) and base.kind != "duration-amount"
            or isinstance(other, BatchEvidence) and other.kind not in {"duration-amount", "duration-relative"}
            or not base.entity_ref.resolved
            or not other.entity_ref.resolved
            or base.entity_ref == other.entity_ref
        ):
            return decline("combined experience needs two distinct participants and an initial duration")
        if relative and (
            base.provenance.sentence >= other.provenance.sentence
            or (other.container_ref or other.entity_ref.owner) != base.entity_ref
        ):
            return decline("the relative duration must identify its preceding comparison participant")
        # A gerund can be read separately or inside the experience noun phrase.
        # Both representations must constrain the same comparison.
        experience = ctx.match.slots.get("experience")
        qualifiers = reference_from_unit(experience).qualifiers if experience else ()
        activity = ctx.query.get("activity")
        if qualifiers:
            if (
                activity or len(qualifiers) != 1
                or not ctx.reg.word_in_category(qualifiers[0], "accumulated_activity_verb")
            ):
                return decline("the experience description needs one identifiable activity")
            activity = ctx.reg.verb_lemmas.get(qualifiers[0], qualifiers[0])
        activities = [r.attribute if isinstance(r, BatchEvidence) and r.attribute else r.verb for r in rows]
        if activity:
            activities.append(activity)
        meanings = [
            predicate_concepts(term, ctx.query.get("experience", ""), ctx.reg, fallback_to_verb=True)
            for term in activities
        ]
        if not frozenset.intersection(*meanings):
            return decline("both durations must describe the requested activity")
        unit = ctx.query.get("unit") or base.measure
        initial = convert_exact_duration(
            base.value, base.measure, unit, ctx.reg, ctx.log, source="anchor-activity-unit"
        )
        amount = convert_exact_duration(
            other.value, other.measure, unit, ctx.reg, ctx.log, source="compared-activity-unit"
        )
        if initial is None or amount is None:
            return decline("both activity durations must convert to the requested unit")
        anchors = [(base.entity_ref, initial)]
        if relative:
            links.append((other.entity_ref, base.entity_ref, 1.0, other.sign * amount))
        else:
            anchors.append((other.entity_ref, amount))
        operands = [(r, [r.value]) for r in rows]
        requested = [(r.entity_ref, 1) for r in rows]
        rows += [
            fact for fact in ctx.store.by_kind(VerbalRelation)
            if fact.role == "temporal-duration" and any(
                fact.verb == r.verb and covered_temporal_annotation(
                    fact, ctx.premises, r.entity, {(r.provenance.sentence, r.measure)}
                ) for r in (base, other)
            )
        ]
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
        performance = ctx.match.slots.get("complete")
        if performance:
            verb = reference_from_unit(performance).head
            if ctx.reg.word_in_category(verb, "self_named_count_action") and verb != ctx.query["measure"]:
                return decline("the requested activity must agree with the counted performance")
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
