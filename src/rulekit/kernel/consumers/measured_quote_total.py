"""Price a closed list of absolute or relatively specified measured items."""

from math import isfinite
from . import consumer
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..answer import Answer
from ..model import BatchEvidence, Expenditure
from ..evaluate import evaluate
from ..rate_calculation import convert_units
from ..pricing import resolve_expenditure_prices

KINDS = {"measured-item-amount", "measured-item-relative", "order-purpose"}


@consumer(
    "measured-quote-total",
    applicable=lambda s: any(
        r.kind == "measured-item-amount" for r in s.by_kind(BatchEvidence)
    ),
)
def consume(ctx):
    rows = sorted(
        ctx.store.by_kind(BatchEvidence),
        key=lambda r: (r.provenance.sentence, r.position),
    )
    items = [r for r in rows if r.kind != "order-purpose"]
    if not items or any(r.kind not in KINDS for r in rows):
        return Answer(
            "decline", None, "one complete measured quote account is required"
        )
    purposes = [r for r in rows if r.kind == "order-purpose"]
    if len(purposes) > 1 or any(
        i.container != p.container
        and not ctx.reg.category_term_contains(p.container, i.container)
        for p in purposes
        for i in items
    ):
        return Answer(
            "decline",
            None,
            "the quoted items must belong to the stated order collection",
        )
    actor = items[0].entity_ref
    if any(r.entity_ref != actor or r.provenance.assumption for r in rows):
        return Answer(
            "decline", None, "all measured quotes must have the same resolved buyer"
        )
    operands, values, extents = [], [], []
    for r in rows:
        if r.kind == "order-purpose":
            operands.append((r, []))
            continue
        if (
            not r.container_ref
            or r.container_ref.described
            or r.per_member < 0
            or not ctx.reg.word_in_category(r.attribute, "currency_unit")
        ):
            return Answer(
                "decline", None, "the measured product and currency must be explicit"
            )
        if r.kind == "measured-item-relative":
            if len(extents) != 1 or r.fraction < 0:
                return Answer(
                    "decline",
                    None,
                    "an omitted relative standard needs one earlier measured amount",
                )
            base, prior = extents[0]
            base = convert_units(
                base,
                prior.measure,
                r.measure,
                ctx.reg,
                ctx.log,
                source="quote-relative-unit",
            )
            if (
                base is None
                or r.verb != prior.verb
                or r.container_ref == prior.container_ref
            ):
                return Answer(
                    "decline",
                    None,
                    "the relative quote needs compatible units and a distinct item",
                )
            amount = evaluate(
                "base * factor",
                dict(base=base, factor=r.fraction),
                ctx.log,
                source="relative-measured-item",
            )
            operands.append((r, [r.fraction, r.per_member]))
        else:
            amount = r.value
            operands.append((r, [r.value, r.per_member]))
        if not isfinite(amount) or amount < 0:
            return Answer(
                "decline", None, "measured amounts must be finite and nonnegative"
            )
        extents.append((amount, r))
        priced_amount = convert_units(
            amount,
            r.measure,
            r.marker,
            ctx.reg,
            ctx.log,
            source="measured-quote-denominator",
        )
        if priced_amount is None:
            return Answer(
                "decline",
                None,
                "the measured amount and quote denominator have incompatible dimensions",
            )
        resolved, error = resolve_expenditure_prices([Expenditure(
            provenance=r.provenance, entity=r.entity, item=r.container,
            verb=r.verb, measure=r.attribute, quantity=priced_amount,
            unit_price=r.per_member, basis="quote")], ctx.log)
        if error:
            return Answer("decline", None, error)
        cost = resolved[0].value
        cost = convert_units(
            cost,
            r.attribute,
            items[0].attribute,
            ctx.reg,
            ctx.log,
            source="quote-currency",
        )
        if cost is None:
            return Answer("decline", None, "quoted currencies are incompatible")
        values.append(cost)
    if not closed_evidence(ctx, rows, operands):
        return Answer(
            "decline", None, "every measured quote and condition must be explained"
        )
    total = evaluate(
        " + ".join(map(str, values)), {}, ctx.log, source="measured-quote-total"
    )
    return finish_batch_answer(
        ctx,
        rows,
        total,
        "total quoted cost of the specified measured items; a quote does not establish payment",
    )
