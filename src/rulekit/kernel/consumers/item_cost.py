"""`item-cost` — The cost of one item from a stated price.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("item-cost", time_scoped=True)
def item_cost(ctx: ConsumerContext):
    from ..answer import Answer
    from ..evaluate import evaluate
    from ..model import Price, Quantity

    # "how much do/does/did ITEM cost" — the item-subject cost ask
    # (mining candidate item-cost-asks). The unique Price fact for the
    # asked item, times its unique purchased/held Quantity, gives the
    # TOTAL cost ("Tom buys 3 shirts at $5 each. How much do the shirts
    # cost?" -> 15); with no such Quantity in play the bare unit price
    # itself answers ("A jacket costs $50. How much does the jacket
    # cost?" -> 50). Either more than one Price fact for the item (two
    # competing prices in the text) or more than one Quantity fact
    # (which holding does the question mean?) is a genuine ambiguity —
    # decline rather than guess, the increment 19/30 discipline.
    item = ctx.reg.plural_to_singular.get(ctx.query["item"], ctx.query["item"])
    prices = [p for p in ctx.store.by_kind(Price) if p.item == item]
    if len(prices) != 1:
        return Answer(
            "decline", None,
            f"{len(prices)} price facts known for {item!r} — an "
            "item-cost ask needs exactly one",
        )
    price = prices[0]
    quantities = [q for q in ctx.store.by_kind(Quantity) if q.measure == item]
    if not quantities:
        bare = evaluate(str(price.value), {}, ctx.log, source="item-cost")
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
    total = evaluate(
        f"{qty.value} * {price.value}", {}, ctx.log, source="item-cost"
    )
    return Answer(
        "number", total,
        f"{qty.value} * {price.value} — qty x unit price of {item!r}",
    )
