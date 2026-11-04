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
from ..pricing import resolve_unit_quotes, consume_unit_quotes


@consumer("capacity", time_scoped=True)
def capacity(ctx: ConsumerContext):
    from ..answer import Answer
    from ..evaluate import evaluate
    from ..model import Price, Quantity
    from ..totals import _purchase_total

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
    price = resolve_unit_quotes(prices, ctx.reg, ctx.log)
    if price is None:
        return Answer(
            "decline", None,
            f"{len(prices)} price facts known for {item!r} — a capacity "
            "ask needs exactly one",
        )
    from math import isfinite
    from ..monetary import canonical_currency, canonical_price, convert_money
    unit_price = canonical_price(price, ctx.reg, ctx.log)
    if unit_price is None:
        return Answer("decline", None, "capacity needs a positive price in a declared currency unit")
    from ..account_totals import AccountTotal, has_resource_account, resolve_account
    if has_resource_account(ctx.store):
        if len(prices) != 1:
            return Answer("decline", None, "a scoped account requires one explicit unit-price source")
        from ..learn import price_quote_evidence
        if ctx.query.get("budget_value") is not None:
            return Answer("decline", None, "an additional asked budget cannot replace the stated account")
        if not isfinite(price.value) or price.value <= 0:
            return Answer("decline", None, "an account purchase needs a positive finite unit price")
        readings = [r for r in ctx.premises if r.sentence_index == price.provenance.sentence]
        quote = price_quote_evidence(readings[0], price, ctx.reg) if len(readings) == 1 else None
        if quote is None or price.qualifier or any(
            u.uid not in quote[1] and u.sense() not in {"article", "punct"}
            for u in readings[0].units
        ):
            return Answer("decline", None, "affordability needs one complete unqualified unit-price statement")
        account = resolve_account(ctx, extra_evidence=(price,))
        if not isinstance(account, AccountTotal):
            return account
        account_price = convert_money(price.value, quote[0], account.opening.measure, ctx.reg, ctx.log)
        if account_price is None or account_price <= 0:
            return Answer("decline", None, "the unit price and resource account use unrelated currencies")
        count = evaluate(f"round({account.value} / {account_price}, 6) // 1", {}, ctx.log,
                         source="account-capacity")
        return Answer("number", count,
                      f"floor({account.value:g} remaining in {account.opening.account} / "
                      f"{account_price:g} per {item})")
    consume_unit_quotes(prices, ctx.log)
    budget_raw = ctx.query.get("budget_value")
    if budget_raw is not None:
        budget = evaluate(str(budget_raw), {}, ctx.log, source="capacity-budget")
        budget_unit = ctx.query.get("budget_measure")
        if not budget_unit:
            return Answer("decline", None, "the budget needs a concrete currency unit")
        budget = convert_money(budget, budget_unit, canonical_currency(ctx.reg), ctx.reg, ctx.log)
    else:
        holdings = [
            q for q in ctx.store.by_kind(Quantity)
            if q.entity == entity and q.is_state
            and (q.measure == "currency" or ctx.reg.word_in_category(q.measure, "currency_unit"))
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
        holding_unit = (canonical_currency(ctx.reg) if holdings[0].measure == "currency"
                        else holdings[0].measure)
        budget = convert_money(budget, holding_unit, canonical_currency(ctx.reg), ctx.reg, ctx.log)
    if budget is None or not isfinite(budget) or budget < 0:
        return Answer("decline", None, "capacity needs a nonnegative budget in a declared currency unit")
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
        f"round({budget} / {unit_price}, 6) // 1", {}, ctx.log, source="capacity"
    )
    return Answer(
        "number", count,
        f"floor({budget} / {unit_price}) — budget ÷ unit price of {item!r}",
    )
