"""`cost-of-quantity` — The cost of a stated quantity at a unit price.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("cost-of-quantity", time_scoped=True)
def cost_of_quantity(ctx: ConsumerContext):
    from ..answer import Answer
    from ..evaluate import evaluate
    from ..model import Predication, Price, Quantity

    # "how much did WHO pay/spend for/on N ITEM" (mining candidate
    # priced-quantity-cost-asks): unlike item-cost, the QUESTION itself
    # states the quantity (never an existing Quantity fact) — commit N
    # (the question's own count) times the item's UNIQUE per-unit Price
    # fact, the increment 19 exactly-one-Price discipline.
    item = ctx.reg.plural_to_singular.get(ctx.query["item"], ctx.query["item"])
    qty = evaluate(str(ctx.query["qty_value"]), {}, ctx.log, source="cost-of-quantity-qty")
    prices = [p for p in ctx.store.by_kind(Price) if p.item == item]
    # mining candidate generic-unit-price-premises: reading MORE price
    # frames (subject-side generics, floating-each relative clauses)
    # means the SAME per-unit price can now legitimately be RESTATED
    # via two different surface forms in one document ("A mug costs 8
    # dollars. Mugs are 8 dollars each.") — two Price facts that fully
    # AGREE on value are the same fact said twice, not an ambiguity;
    # facts.py's key() differs (verb/occurrence) so they never dedupe
    # at admission. Only a genuine VALUE disagreement is still the
    # increment-19 ambiguity this guard exists to catch.
    from ..monetary import price_terms
    distinct_values = {price_terms(p, ctx.reg) for p in prices}
    if len(distinct_values) != 1:
        return Answer(
            "decline", None,
            f"{len(prices)} price facts known for {item!r} — a "
            "cost-of-quantity ask needs exactly one",
        )
    price = prices[0]
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
    total = evaluate(f"{qty} * {unit_price}", {}, ctx.log, source="cost-of-quantity")
    return Answer(
        "number", total,
        f"{qty} * {unit_price} — question qty x unit price of {item!r}",
    )
