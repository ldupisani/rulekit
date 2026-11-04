"""Resolve cross-item affine inventory comparisons within one explicit source."""

from collections import Counter, defaultdict
from math import isfinite
from . import consumer
from ..answer import Answer
from ..evaluate import evaluate
from ..model import BatchEvidence
from ..numeric_evidence import audit_numeric_mentions
from ..reference_identity import ReferenceIdentity
from ..source_coverage import uncovered_document_units


@consumer(
    "relative-item-total",
    applicable=lambda s: any(
        r.kind == "item-relation" for r in s.by_kind(BatchEvidence)
    ),
)
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    known = [r for r in rows if r.kind == "item-amount"]
    pending = [r for r in rows if r.kind == "item-relation"]
    who = (
        ReferenceIdentity.from_dict(ctx.query["evidence_entity_reference"])
        if ctx.query.get("evidence_entity_reference")
        else ReferenceIdentity(ctx.query["entity"])
    )
    if any(
        ctx.query.get(key)
        for key in ("time", "measure_qualifier", "measure_owner", "place", "unit")
    ):
        return decline(
            "the relative inventory does not establish the requested additional scope"
        )
    if (
        not known
        or not pending
        or len(rows) != len(known) + len(pending)
        or len(rows) != len(ctx.store.facts)
        or ctx.store.collisions
        or ctx.store.quarantined
        or any(
            r.entity_ref != who
            or r.verb != ctx.query["verb"]
            or r.provenance.assumption
            for r in rows
        )
    ):
        return decline(
            "one complete, actual item inventory with resolved comparisons is required"
        )
    expected = defaultdict(Counter)
    amounts = {}
    for row in known:
        if row.measure in amounts:
            return decline("an item has competing absolute counts")
        amounts[row.measure] = row.value
        expected[row.provenance.sentence][row.value] += 1
    while pending:
        ready = [r for r in pending if r.container in amounts]
        if not ready:
            return decline(
                "the item comparisons contain a cycle or an unknown standard"
            )
        for row in ready:
            if row.measure in amounts:
                return decline("an item has competing comparison counts")
            amounts[row.measure] = evaluate(
                "base * factor + delta * sign",
                {
                    "base": amounts[row.container],
                    "factor": row.fraction,
                    "delta": row.value,
                    "sign": row.sign,
                },
                ctx.log,
                source="relative-item-count",
            )
            expected[row.provenance.sentence][
                row.value if row.sign else row.fraction
            ] += 1
            pending.remove(row)
    if (
        any(
            not isfinite(v) or v < 0 or not float(v).is_integer()
            for v in amounts.values()
        )
        or uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)
        or audit_numeric_mentions(
            (*ctx.premises, ctx.question),
            expected,
            missing="missing",
            duplicate="duplicate",
        )
    ):
        return decline(
            "all item counts and comparison scopes must be read and nonnegative whole numbers"
        )
    if any(
        left != right and ctx.reg.category_term_contains(left, right)
        for left in amounts
        for right in amounts
    ):
        return decline(
            "overlapping item classes cannot be added as independent inventory components"
        )
    requested = ctx.query["measure"]
    if requested in amounts:
        selected = [amounts[requested]]
    else:
        if any(
            not ctx.reg.category_term_contains(requested, item)
            and not ctx.reg.category_terms_disjoint(requested, item)
            for item in amounts
        ):
            return decline(
                "an item outside the requested class needs an explicit disjoint classification"
            )
        selected = [
            value
            for item, value in amounts.items()
            if ctx.reg.category_term_contains(requested, item)
        ]
    if not selected:
        return decline("no counted item belongs to the requested class")
    value = evaluate(
        " + ".join(map(str, selected)),
        {},
        ctx.log,
        source="relative-inventory-class-total",
    )
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    return Answer(
        "number",
        value,
        "sum resolved item quantities belonging to the requested category",
    )
