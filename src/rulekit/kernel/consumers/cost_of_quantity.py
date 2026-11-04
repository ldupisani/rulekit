"""`cost-of-quantity` — The cost of a stated quantity at a unit price.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer
from ..pricing import resolve_unit_quotes, consume_unit_quotes


@consumer("cost-of-quantity", time_scoped=True)
def cost_of_quantity(ctx: ConsumerContext):
    from ..answer import Answer
    from ..evaluate import evaluate
    from ..model import Predication, Price, Quantity

    # "how much did WHO pay/spend for/on N ITEM": the QUESTION itself
    # states the quantity (never an existing Quantity fact) — commit N
    # (the question's own count) times the item's agreed per-unit price.
    item = ctx.reg.plural_to_singular.get(ctx.query["item"], ctx.query["item"])
    qty = evaluate(str(ctx.query["qty_value"]), {}, ctx.log, source="cost-of-quantity-qty")
    prices = [p for p in ctx.store.by_kind(Price) if p.item == item]
    price = resolve_unit_quotes(prices, ctx.reg, ctx.log)
    if price is None:
        return Answer(
            "decline", None,
            f"{len(prices)} price facts known for {item!r} — a "
            "cost-of-quantity ask needs exactly one",
        )
    entity = ctx.query["entity"]
    # increment 10's invariant, reused verbatim: a buyer who
    # splits/shares the cost with someone else means the raw qty *
    # price is not necessarily what they themselves paid.
    if any(
        p.subject == entity and ctx.reg.word_in_category(p.verb, "divide")
        for p in ctx.store.by_kind(Predication)
    ):
        return Answer(
            "decline", None,
            f"{entity!r} has a cost-splitting predicate — the raw "
            "total is not necessarily what they paid",
        )
    # the SAME buyer already holding/having bought this item elsewhere
    # in the text is a genuine ambiguity between two possible
    # quantities (the premise's own and the question's stated one) —
    # decline rather than silently prefer the question's count.
    if any(
        q.entity == entity and q.measure == item for q in ctx.store.by_kind(Quantity)
    ):
        return Answer(
            "decline", None,
            f"{entity!r} already has a quantity of {item!r} known — "
            "ambiguous against the question's own count",
        )
    from ..monetary import canonical_price
    unit_price = canonical_price(price, ctx.reg, ctx.log)
    if unit_price is None:
        return Answer("decline", None, "the price needs a concrete convertible denomination")
    consume_unit_quotes(prices, ctx.log)
    total = evaluate(f"{qty} * {unit_price}", {}, ctx.log, source="cost-of-quantity")
    return Answer(
        "number", total,
        f"{qty} * {unit_price} — question qty x unit price of {item!r}",
    )
