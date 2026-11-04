"""Close a measured partition after resolving explicit member comparisons."""

from collections import Counter, defaultdict
from math import isfinite
from . import consumer
from .indexed_path import ordinal_index
from ..answer import Answer
from ..evaluate import evaluate
from ..model import BatchEvidence, GroupTotal
from ..numeric_evidence import audit_numeric_mentions
from ..rate_calculation import convert_units
from ..reference_identity import reference_from_unit
from ..resource_equations import resource_residual
from ..source_coverage import uncovered_document_units


@consumer("participant-outcome-remainder")
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    total = [r for r in rows if r.kind == "participant-total"]
    equal = [r for r in rows if r.kind == "participant-equal"]
    known = [r for r in rows if r.kind == "participant-amount"]
    links = [r for r in rows if r.kind == "participant-relation"]
    mirrors = list(ctx.store.by_kind(GroupTotal))
    if (
        len(total) != 1
        or len(equal) != 1
        or not known
        or len(rows) != 2 + len(known) + len(links)
        or len(ctx.store.facts) != len(rows) + len(mirrors)
        or ctx.store.collisions
        or ctx.store.quarantined
    ):
        return decline(
            "one complete measured partition with an equal remainder is required"
        )
    whole, rest = total[0], equal[0]
    group = reference_from_unit(ctx.match.slots["group"])
    if (
        group.head != whole.entity_ref.head
        or rest.entity_ref.head != group.head
        or rest.value != float(ctx.query["count"])
        or rest.verb != ctx.query["verb"]
        or any(r.verb != whole.verb or r.provenance.assumption for r in rows)
        or any(m.value != whole.value or m.measure != whole.measure for m in mirrors)
    ):
        return decline("the requested participants and measured outcome must agree")
    expected = defaultdict(Counter)
    expected[whole.provenance.sentence].update([whole.value, whole.per_member])
    expected[rest.provenance.sentence][rest.value] += 1
    expected[ctx.question.sentence_index][float(ctx.query["count"])] += 1
    values = {}
    for row in known:
        if row.entity_ref.head != group.head or row.entity_ref in values:
            return decline("each known member must have one distinct ordinal identity")
        value = convert_units(
            row.value,
            row.measure,
            whole.measure,
            ctx.reg,
            ctx.log,
            source="partition-member-unit",
        )
        if value is None:
            return decline("participant quantities need compatible units")
        values[row.entity_ref] = value
        expected[row.provenance.sentence][row.value] += 1
    pending = list(links)
    while pending:
        ready = [r for r in pending if r.container_ref in values]
        if not ready:
            return decline("member comparisons contain an unresolved standard or cycle")
        for row in ready:
            if row.entity_ref in values or row.entity_ref.head != group.head:
                return decline("member comparisons must identify distinct participants")
            offset = convert_units(
                row.value,
                row.measure,
                whole.measure,
                ctx.reg,
                ctx.log,
                source="partition-comparison-unit",
            )
            if offset is None:
                return decline("the comparison needs compatible units")
            values[row.entity_ref] = evaluate(
                "base + sign * offset",
                {"base": values[row.container_ref], "sign": row.sign, "offset": offset},
                ctx.log,
                source="partition-relative-member",
            )
            expected[row.provenance.sentence][row.value] += 1
            pending.remove(row)
    positions = [
        ordinal_index(ref.qualifiers[0], ctx.reg) if len(ref.qualifiers) == 1 else None
        for ref in values
    ]
    if (
        set(positions) != set(range(1, len(values) + 1))
        or not float(whole.per_member).is_integer()
        or not float(rest.value).is_integer()
        or whole.per_member != len(values) + rest.value
        or rest.value <= 0
        or any(not isfinite(v) or v < 0 for v in values.values())
        or uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)
        or audit_numeric_mentions(
            (*ctx.premises, ctx.question),
            expected,
            missing="missing",
            duplicate="duplicate",
        )
    ):
        return decline(
            "the stated population, comparisons and equal remainder must exhaust the account"
        )
    residual = resource_residual(
        [whole.value],
        list(values.values()),
        ctx.log,
        source="participant-outcome-residual",
    )
    if residual < 0:
        return decline("known outcomes exceed the total")
    result = evaluate(
        "remainder / members",
        {"remainder": residual, "members": rest.value},
        ctx.log,
        source="equal-remaining-outcome",
    )
    result = convert_units(
        result,
        whole.measure,
        ctx.query["measure"],
        ctx.reg,
        ctx.log,
        source="partition-answer-unit",
    )
    if result is None:
        return decline("the requested unit must match the outcome dimension")
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    return Answer(
        "number",
        result,
        "subtract known and relatively stated member outcomes, then divide the remainder equally",
    )
