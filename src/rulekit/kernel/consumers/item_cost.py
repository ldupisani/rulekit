"""`item-cost` — The cost of one item from a stated price.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer
from ..pricing import resolve_unit_quotes, consume_unit_quotes


@consumer("item-cost", time_scoped=True)
def item_cost(ctx: ConsumerContext):
    from ..answer import Answer
    from ..evaluate import evaluate
    from ..model import Price, Quantity

    # "how much do/does/did ITEM cost" — the item-subject cost ask.
    # Agreeing unit quotes for the asked item, times its unique Quantity, give the
    # TOTAL cost ("Tom buys 3 shirts at $5 each. How much do the shirts
    # cost?" -> 15); with no such Quantity in play the bare unit price
    # itself answers ("A jacket costs $50. How much does the jacket
    # cost?" -> 50). Conflicting quotes or more than one Quantity fact
    # (which holding does the question mean?) is a genuine ambiguity —
    # decline rather than guess.
    item = ctx.reg.plural_to_singular.get(ctx.query["item"], ctx.query["item"])
    prices = [p for p in ctx.store.by_kind(Price) if p.item == item]
    price = resolve_unit_quotes(prices, ctx.reg, ctx.log)
    if price is None:
        return Answer(
            "decline", None,
            f"{len(prices)} price facts known for {item!r} — an "
            "item-cost ask needs exactly one",
        )
    quantities = [q for q in ctx.store.by_kind(Quantity) if q.measure == item]
    if not quantities:
        bare = evaluate(str(price.value), {}, ctx.log, source="item-cost")
        consume_unit_quotes(prices, ctx.log)
        return Answer(
            "number", bare, f"bare unit price of {item!r}"
        )
    if len(quantities) > 1:
        return Answer(
            "decline", None,
            f"{len(quantities)} quantities of {item!r} known — an "
            "item-cost ask needs exactly one to total",
        )
    qty = quantities[0]
    consume_unit_quotes(prices, ctx.log)
    total = evaluate(
        f"{qty.value} * {price.value}", {}, ctx.log, source="item-cost"
    )
    return Answer(
        "number", total,
        f"{qty.value} * {price.value} — qty x unit price of {item!r}",
    )
