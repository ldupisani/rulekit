"""`capacity` — How many fit, from a stated capacity.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("capacity", time_scoped=True)
def capacity(ctx: ConsumerContext):
    from ..answer import Answer
    from ..evaluate import evaluate
    from ..model import Price, Quantity
    from ..answer import _purchase_total

    # "how many X can/could/... WHO buy/purchase/afford (with $B)?" —
    # budget ÷ unit price, floored (leftover money is never itself
    # part of the count). The verb/modal are structural glue only
    # (increment 14 split 'modal' from 'auxiliary' precisely so this
    # ask can claim the token factual asks now exclude); the SEMANTIC
    # gate is a Price fact for the asked item plus a UNIQUE explicit
    # budget — never a surface cue. The budget is either the ask's own
    # "with $B" tail or, absent that, the entity's single stated money
    # holding; anything else (zero, or more than one, of either) is a
    # genuine ambiguity and declines.
    entity = ctx.query["entity"]
    item = ctx.reg.plural_to_singular.get(ctx.query["item"], ctx.query["item"])
    prices = [p for p in ctx.store.by_kind(Price) if p.item == item]
    if len(prices) != 1:
        return Answer(
            "decline", None,
            f"{len(prices)} price facts known for {item!r} — a capacity "
            "ask needs exactly one",
        )
    price = prices[0]
    budget_raw = ctx.query.get("budget_value")
    if budget_raw is not None:
        budget = evaluate(str(budget_raw), {}, ctx.log, source="capacity-budget")
    else:
        holdings = [
            q for q in ctx.store.by_kind(Quantity)
            if q.entity == entity and q.is_state
            and (q.measure == "currency" or ctx.reg.word_in_category(q.measure, "currency"))
        ]
        if len(holdings) != 1:
            return Answer(
                "decline", None,
                f"{len(holdings)} money holdings known for {entity!r} — "
                "no explicit budget stated and no unique holding to use",
            )
        budget = evaluate(
            str(holdings[0].value), {}, ctx.log, source="capacity-budget"
        )
    # a budget shared across SEVERAL priced purchases needs splitting —
    # this mechanism only ever does a single floor division, so any
    # OTHER priced item this entity also has a quantity of (bought,
    # wants, holds) makes the budget ambiguous UNLESS every one of
    # those other items is itself a fully-priced, unambiguous PURCHASE
    # (a genuine "buys X for $Y" the entity already made) — in that
    # one case the remaining budget after those purchases is exactly
    # computable, so subtract it instead of declining outright.
    all_priced_items = {p2.item for p2 in ctx.store.by_kind(Price)}
    other_priced = sorted(
        {
            q.measure
            for q in ctx.store.by_kind(Quantity)
            if q.entity == entity
            and q.measure != item
            and q.measure in all_priced_items
        }
    )
    if other_priced:
        # any other-priced item held via a NON-purchase verb ("wants"/
        # "has") is not spending at all — the remaining-budget
        # subtraction below only accounts for purchase-verb quantities,
        # so such an item stays a genuine ambiguity (increment 19's
        # original decline, unchanged).
        non_purchase_other = {
            q.measure
            for q in ctx.store.by_kind(Quantity)
            if q.entity == entity
            and q.measure in other_priced
            and not ctx.reg.word_in_category(q.verb, "purchase")
        }
        if non_purchase_other:
            return Answer(
                "decline", None,
                f"{entity!r} also has priced {other_priced} — the budget "
                "would need splitting across items",
            )
        # _purchase_total already carries the increment-10 invariant
        # (any unpriced purchase, or a 'splits/shares the cost'
        # predicate on this entity, declines the WHOLE total) — reused
        # here unscoped by item, so it extends unchanged to this
        # subtraction path.
        other_total = _purchase_total(ctx.store, ctx.reg, entity, ctx.log, exclude_item=item)
        if other_total is None:
            return Answer(
                "decline", None,
                f"{entity!r} also has priced {other_priced} — the budget "
                "would need splitting across items",
            )
        remaining = evaluate(
            f"{budget} - {other_total}", {}, ctx.log, source="capacity-remaining"
        )
        if remaining < 0:
            return Answer(
                "decline", None,
                f"{entity!r}'s other purchases ({other_total}) exceed the "
                f"stated budget ({budget}) — remaining budget is negative",
            )
        budget = remaining
    count = evaluate(
        f"round({budget} / {price.value}, 6) // 1", {}, ctx.log, source="capacity"
    )
    return Answer(
        "number", count,
        f"floor({budget} / {price.value}) — budget ÷ unit price of {item!r}",
    )
