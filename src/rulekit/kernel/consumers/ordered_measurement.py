"""Anchor measurements and event rates to ordered members of one collection."""

from math import isclose

from . import consumer
from .indexed_path import ordinal_index
from ..affine_graph import AffineError, AffineGraph
from ..answer import Answer, AnswerAssumption
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..evaluate import evaluate
from ..model import BatchEvidence
from ..rate_calculation import convert_duration, convert_units


def _member(reference, reg):
    if (reference is None or not reference.resolved or reference.owner is not None
            or reference.label is not None or len(reference.qualifiers) != 1):
        return None
    index = ordinal_index(reference.qualifiers[0], reg)
    return (reference.head, index) if index is not None and index > 0 else None


@consumer(
    "ordered-measurement",
    applicable=lambda store: any(
        row.kind in {"ordinal-material-anchor", "ordinal-event-anchor"}
        for row in store.by_kind(BatchEvidence)
    ),
)
def ordered_measurement(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    mode = ctx.query["mode"]
    kinds = {part: f"ordinal-{mode}-{part}" for part in ("context", "anchor", "relation")}
    rows = list(ctx.store.by_kind(BatchEvidence))
    contexts, anchors, relations = (
        [row for row in rows if row.kind == kind] for kind in kinds.values()
    )
    if (not anchors or not relations or len(contexts) > 1
            or len(rows) != len(contexts) + len(anchors) + len(relations)
            or any(row.provenance.assumption for row in rows)):
        return decline("one complete set of indexed measurements and comparisons is required")
    members = {row.key(): _member(row.entity_ref, ctx.reg) for row in anchors + relations}
    standards = {row.key(): _member(row.container_ref, ctx.reg) for row in relations}
    if None in members.values() or None in standards.values():
        return decline("each indexed measurement needs an explicit member identity")
    if any(members[row.key()] == standards[row.key()] for row in relations):
        return decline("relative measurements must compare distinct members")
    identities = set(members.values()) | set(standards.values())
    operands = [(row, [row.value]) for row in anchors + relations]
    assumptions = ()
    if mode == "material":
        target = _member(ctx.query_reference("target"), ctx.reg)
        actor = ctx.query_reference()
        material = ctx.query["measure"]
        if (target not in identities or actor is None or not actor.resolved
                or any(row.measure != material or row.acquisition_ref != actor
                       or row.verb != ctx.query["verb"] for row in anchors)
                or any(row.entity_ref != actor or row.measure != material
                       or row.container != target[0] for row in contexts)
                or any(head != target[0] for head, _ in identities)):
            return decline("the measurements and comparisons must describe the requested material and forms")

        def observed(row):
            return convert_units(row.value, row.container, ctx.query["unit"], ctx.reg, ctx.log,
                                 source="indexed-material-units")

        query_values = ()
        assumptions = (
            AnswerAssumption(
                "relative-extent-as-material-amount",
                "The relative sizes refer to the amounts of material used.",
                tuple(sorted({row.provenance.sentence for row in relations})),
            ),
        )
    else:
        count = float(ctx.query["count"])
        if not count.is_integer() or count <= 0 or len(identities) != count:
            return decline("the rates must cover exactly the stated group")
        group = ctx.query["group"]
        event = ctx.query["measure"]
        if (identities != {(group, index) for index in range(1, int(count) + 1)}
                or any(row.entity != group or row.verb != event or row.value != count for row in contexts)
                or any(row.verb != event for row in anchors + relations)):
            return decline("the frequencies must describe the same event for every group member")
        operands.extend((row, [row.value]) for row in contexts)
        query_values = (count,)

        def observed(row):
            span = convert_duration(float(ctx.query["span_value"]), ctx.query["span_unit"], row.container,
                                    ctx.reg, ctx.log, source="indexed-rate-time-units")
            return None if span is None else evaluate("rate * span", dict(rate=row.value, span=span),
                                                       ctx.log, source="indexed-event-projection")

    if not closed_evidence(ctx, rows, operands, question_values=query_values):
        return decline("every stated measurement and condition must belong to this calculation")
    amounts = [(members[row.key()], observed(row)) for row in anchors]
    if any(value is None or value < 0 for _, value in amounts):
        return decline("each observed amount needs compatible units and a nonnegative value")
    try:
        graph = AffineGraph(
            amounts,
            [(members[row.key()], standards[row.key()], row.value, 0) for row in relations],
            ctx.log,
        )
        values = {identity: graph.value(identity) for identity in identities}
    except AffineError as error:
        return decline(str(error))
    if mode == "material":
        value = values[target]
    else:
        if any(not isclose(value, round(value), abs_tol=1e-9, rel_tol=0) for value in values.values()):
            return decline("the interval must give whole event counts for all members")
        value = sum(round(value) for value in values.values())
    return finish_batch_answer(ctx, rows, value, "resolve the indexed comparisons from the observed amounts",
                               assumptions=assumptions)
