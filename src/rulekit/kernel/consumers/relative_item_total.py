"""Resolve cross-item affine inventory comparisons within one explicit source."""

from collections import Counter, defaultdict
from math import isfinite
from . import consumer
from ..answer import Answer
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..evaluate import evaluate
from ..model import BatchEvidence, Quantity
from ..numeric_evidence import audit_numeric_mentions
from ..reference_identity import ReferenceIdentity
from ..resource_equations import resource_residual
from ..source_coverage import quantity_ledger_source_units, uncovered_document_units


@consumer(
    "relative-item-total",
    applicable=lambda s: any(
        r.kind in {"item-relation", "relative-balance-receipt"} for r in s.by_kind(BatchEvidence)
    ),
)
def consume(ctx):
    if ctx.query.get("mode") == "replenished":
        return _replenished_inventory(ctx)
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    known = [r for r in rows if r.kind == "item-amount"]
    pending = [r for r in rows if r.kind == "item-relation"]
    who = ctx.query_reference() or ReferenceIdentity(ctx.query["entity"])
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
        ready = [r for r in pending if set(r.members or (r.container,)) <= amounts.keys()]
        if not ready:
            return decline(
                "the item comparisons contain a cycle or an unknown standard"
            )
        for row in ready:
            standards = row.members or (row.container,)
            if row.measure in amounts or len(set(standards)) != len(standards):
                return decline("an item has competing comparison counts")
            base = resource_residual(
                [amounts[item] for item in standards], [], ctx.log, source="combined-inventory-standard",
            ) if row.members else amounts[row.container]
            amounts[row.measure] = evaluate(
                "base * factor + delta * sign",
                {
                    "base": base,
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


def _replenished_inventory(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    quantities = list(ctx.store.by_kind(Quantity))
    losses = [r for r in rows if r.kind == "partitive-stock-loss"]
    receipts = [r for r in rows if r.kind == "relative-balance-receipt"]
    if len(rows) != 2 or len(losses) != 1 or len(receipts) != 1 or len(quantities) != 1:
        return decline("a balance-relative receipt needs one opening, identified loss and receipt")
    opening, loss, receipt = quantities[0], losses[0], receipts[0]
    actor = ctx.query_reference()
    if (actor is None or not actor.resolved or any(r.entity_ref != actor or r.provenance.assumption
                                                    for r in [opening, *rows])
            or opening.measure != ctx.query["measure"] or opening.measure_qualifier or not opening.is_state
            or receipt.marker != loss.verb or receipt.container_ref == actor
            or not opening.provenance.sentence < loss.provenance.sentence < receipt.provenance.sentence
            or not float(opening.value).is_integer()):
        return decline("the opening, loss and receipt must belong to the same ordered stock")
    source = next(r for r in ctx.premises if r.sentence_index == opening.provenance.sentence)
    covered = {source.sentence_index: quantity_ledger_source_units(source, [opening], ctx.reg)}
    loss_mentions = [loss.value, 1] if loss.marker else [loss.value]
    operands = [(opening, [opening.value]), (loss, loss_mentions), (receipt, [receipt.value])]
    if not closed_evidence(ctx, [opening, *rows], operands, covered=covered):
        return decline("all stated stock changes must be read")
    lost = evaluate("base * fraction", dict(base=opening.value, fraction=loss.value),
                    ctx.log, source="stock-fraction-lost")
    remaining = resource_residual([opening.value], [lost], ctx.log, source="stock-after-loss")
    received = evaluate("balance * factor", dict(balance=remaining, factor=receipt.value),
                        ctx.log, source="relative-stock-receipt")
    if any(not float(v).is_integer() or not isfinite(v) for v in (lost, received)):
        return decline("a counted stock requires whole losses and receipts")
    return finish_batch_answer(ctx, rows, resource_residual(
        [remaining, received], [], ctx.log, source="replenished-stock",
    ), "apply the loss, then add the amount received using the resulting balance")
