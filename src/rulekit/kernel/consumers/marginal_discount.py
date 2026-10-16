"""Price threshold discounts with explicit marginal or whole-purchase scope."""

from collections import Counter, defaultdict
from dataclasses import replace
from math import isfinite
from . import consumer
from ..answer import Answer
from ..model import BatchEvidence, Price, Discount, Quantity
from ..evaluate import evaluate
from ..pricing import purchase_total_expression
from ..numeric_evidence import audit_numeric_mentions
from ..source_coverage import uncovered_units, price_source_units, quantity_source_units


_DISCOUNT_KINDS = frozenset({
    "marginal-discount", "marginal-discount-policy", "all-units-discount-policy"
})


@consumer(
    "marginal-discount-cost",
    applicable=lambda s: any(
        b.kind in _DISCOUNT_KINDS for b in s.by_kind(BatchEvidence)
    ),
)
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    prices = list(ctx.store.by_kind(Price))
    if (
        len(rows) != 1
        or rows[0].kind not in _DISCOUNT_KINDS
        or len(prices) != 1
        or ctx.store.collisions
        or ctx.store.quarantined
    ):
        return decline(
            "one purchase, one unit price and one threshold discount are required"
        )
    b = rows[0]
    p = prices[0]
    purchase = None
    if b.kind != "marginal-discount":
        purchases = list(ctx.store.by_kind(Quantity))
        if len(purchases) != 1:
            return decline("a threshold discount policy needs one explicit purchase")
        purchase = purchases[0]
        if (
            not ctx.reg.word_in_category(purchase.verb, "purchase")
            or purchase.measure != b.measure
            or purchase.provenance.assumption
            or purchase.qualifier
            or purchase.owner
        ):
            return decline("the policy must identify the purchased item")
        b = replace(b, entity=purchase.entity, value=purchase.value)
    if (
        b.entity != ctx.query["entity"]
        or b.measure != p.item
        or ctx.query.get("item", b.measure) != b.measure
        or b.attribute != b.measure
        or b.provenance.assumption
        or p.provenance.assumption
        or (purchase is None and p.provenance.sentence >= b.provenance.sentence)
        or not all(
            isfinite(v) and v >= 0 for v in (b.value, b.subtotal, b.fraction, p.value)
        )
        or not float(b.value).is_integer()
        or not float(b.subtotal).is_integer()
        or b.fraction > 1
    ):
        return decline(
            "the discounted units must belong to this purchase and its price"
        )
    discounts = list(ctx.store.by_kind(Discount))
    if any(
        d.provenance.sentence != b.provenance.sentence
        or d.value != b.fraction
        or not d.percent
        for d in discounts
    ):
        return decline("an additional discount cannot be assigned to this threshold")
    expected = defaultdict(Counter)
    expected[p.provenance.sentence].update([p.value])
    expected[b.provenance.sentence].update([b.fraction, b.subtotal])
    expected[(purchase or b).provenance.sentence].update([b.value])
    if any(
        uncovered_units(
            r,
            (
                ctx.match.consumed
                if r is ctx.question
                else (*price_source_units(r, p, ctx.reg),
                      *(quantity_source_units(r, purchase, ctx.reg) if purchase else ()))
            ),
        )
        for r in (*ctx.premises, ctx.question)
    ) or audit_numeric_mentions(
        (*ctx.premises, ctx.question),
        expected,
        missing="missing",
        duplicate="duplicate",
    ):
        return decline(
            "every price, purchase and discount condition must be accounted for"
        )
    if b.kind == "all-units-discount-policy":
        discounted = b.value if b.value > b.subtotal else 0
    else:
        discounted = max(0, b.value - b.subtotal)
    regular = b.value - discounted
    reduced = evaluate(
        "price * (1 - fraction)",
        {"price": p.value, "fraction": b.fraction},
        ctx.log,
        source="marginal-unit-price",
    )
    value = evaluate(
        purchase_total_expression([(regular, p.value), (discounted, reduced)]),
        {},
        ctx.log,
        source="marginal-purchase-total",
    )
    output = ctx.query.get("output", "total")
    if output != "total":
        if b.value == 0:
            return decline("a paid per-unit price needs a positive purchased quantity")
        if output == "unit":
            if regular and discounted and p.value != reduced:
                return decline("the purchase has different unit prices; an explicit average is required")
            value = reduced if discounted else p.value
        elif output == "average-unit":
            value = evaluate(
                "total / count", {"total": value, "count": b.value}, ctx.log,
                source="average-purchase-unit-price",
            )
        else:
            return decline("unsupported threshold-price output")
    ctx.log.consumed_batch_keys.add(rows[0].key())
    return Answer(
        "number",
        value,
        f"{regular:g} units at full price and {discounted:g} units at the discounted price.",
    )
