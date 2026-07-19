"""`unit-price-from-total` — The unit price implied by a total.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("unit-price-from-total", time_scoped=True)
def unit_price_from_total(ctx: ConsumerContext):
    from ..answer import Answer
    from ..evaluate import evaluate
    from ..answer import _unit_price_from_total

    # "how much does/did each ITEM cost?" / "what is the cost of N
    # ITEM?" (mining candidate unit-price-from-total, re-cut of the
    # batch-47 review kill): the per-unit price is never stated —
    # `_unit_price_from_total` recovers it from a stated GRAND TOTAL
    # minus every other already-priced line item, divided by the
    # asked item's own purchased count (definitive-or-decline, the
    # increment-10 discipline traveling through `_purchase_total`
    # unchanged). The ask's own stated quantity (`qty_value`, when
    # present — "cost of N ITEM") multiplies the recovered unit price;
    # a bare "each ITEM" ask (no stated quantity) leaves it at 1.
    item = ctx.reg.plural_to_singular.get(ctx.query["item"], ctx.query["item"])
    resolved = _unit_price_from_total(ctx.store, ctx.reg, item, ctx.log)
    if resolved is None:
        return Answer(
            "decline", None,
            f"no resolvable grand-total residual for {item!r} — needs "
            "exactly one buyer, one owned grand total, and every "
            "other purchased item priced",
        )
    entity, unit_price, _count = resolved
    qty_raw = ctx.query.get("qty_value")
    if qty_raw is None:
        return Answer(
            "number", unit_price,
            f"{entity!r}'s grand total minus other priced purchases, "
            f"divided by {item!r}'s purchased count",
        )
    qty = evaluate(str(qty_raw), {}, ctx.log, source="unit-price-from-total-qty")
    total = evaluate(
        f"{qty} * {unit_price}", {}, ctx.log, source="unit-price-from-total"
    )
    return Answer(
        "number", total,
        f"{qty} * {unit_price} — question qty x recovered unit price "
        f"of {item!r}",
    )
