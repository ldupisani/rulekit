"""Sum disjoint outer-container partitions, then allocate their contents equally."""

from collections import Counter, defaultdict
from math import isfinite
from . import consumer
from ..answer import Answer
from ..model import BatchEvidence
from ..evaluate import evaluate
from ..resource_equations import resource_residual
from ..numeric_evidence import audit_numeric_mentions
from ..source_coverage import uncovered_document_units


@consumer(
    "nested-content-share",
    applicable=lambda s: any(
        b.kind == "nested-total" for b in s.by_kind(BatchEvidence)
    ),
)
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    by = defaultdict(list)
    for b in rows:
        by[b.kind].append(b)
    if (
        set(by) != {"nested-population", "nested-total", "nested-subset"}
        or len(by["nested-population"]) != 1
        or len(by["nested-total"]) != 1
        or ctx.store.collisions
        or ctx.store.quarantined
        or any(b.provenance.assumption for b in rows)
    ):
        return decline("one population and a complete nested collection are required")
    pop = by["nested-population"][0]
    total = by["nested-total"][0]
    parts = by["nested-subset"]
    if (
        pop.entity != ctx.query["person"]
        or any(b.measure != ctx.query["item"] for b in rows)
        or any(
            b.entity != total.entity
            or b.provenance.sentence <= total.provenance.sentence
            for b in parts
        )
        or not all(
            isfinite(v) and v >= 0 and float(v).is_integer()
            for v in [pop.value, total.value]
            + [v for b in parts for v in (b.value, b.per_member, b.content_count)]
        )
        or pop.value <= 0
        or total.value <= 0
    ):
        return decline("recipients, items and nonnegative container counts must agree")
    remainders = [b for b in parts if b.marker == "remainder"]
    explicit = [b for b in parts if b.marker == "counted"]
    if (
        len(remainders) > 1
        or len(remainders) + len(explicit) != len(parts)
        or not explicit
    ):
        return decline("partitions need explicit counts and at most one remainder")
    remaining = resource_residual(
        [total.value],
        [b.value for b in explicit],
        ctx.log,
        source="outer-container-remainder",
    )
    if remaining < 0 or not remainders and remaining != 0:
        return decline(
            "the outer partitions must exhaust the stated collection exactly"
        )
    expected = defaultdict(Counter)
    expected[pop.provenance.sentence][pop.value] += 1
    expected[total.provenance.sentence][total.value] += 1
    values = []
    for b in parts:
        if b.marker == "counted":
            expected[b.provenance.sentence][b.value] += 1
        expected[b.provenance.sentence].update((b.per_member, b.content_count))
        values.append(
            evaluate(
                "outer * inner * contents",
                {
                    "outer": remaining if b.marker == "remainder" else b.value,
                    "inner": b.per_member,
                    "contents": b.content_count,
                },
                ctx.log,
                source="nested-subset-contents",
            )
        )
    if uncovered_document_units(
        ctx.premises, ctx.question, ctx.match.consumed
    ) or audit_numeric_mentions(
        (*ctx.premises, ctx.question),
        expected,
        missing="missing",
        duplicate="duplicate",
    ):
        return decline(
            "every nested quantity and sharing condition must be accounted for"
        )
    amount = resource_residual(values, [], ctx.log, source="nested-collection-total")
    value = evaluate(
        "contents / recipients",
        {"contents": amount, "recipients": pop.value},
        ctx.log,
        source="equal-content-share",
    )
    ctx.log.consumed_batch_keys.update(b.key() for b in rows)
    return Answer(
        "number",
        value,
        "Sum the nested container contents and divide equally without rounding.",
    )
