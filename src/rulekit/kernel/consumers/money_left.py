"""`money-left` — How much money is left after purchases.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("money-left", time_scoped=True)
def money_left(ctx: ConsumerContext):
    from ..answer import Answer
    from ..evaluate import evaluate
    from ..model import Quantity
    from ..measures import _check_req_unit, _resolve_measure
    from ..totals import _entity_total, _purchase_total

    # "how much money does WHO have left" — the entity's general money
    # total (_entity_total: the SAME state-anchor + signed-event fold
    # the bare 'how much money does WHO have' ask already uses, so
    # "spends $14 on oranges" / "receives $50" / "saves $27 in March"
    # events it already signs by category polarity fold in exactly as
    # they would for that ask) minus its priced purchases
    # (_purchase_total, UNCHANGED — the increment-10 invariant travels
    # with it: any unpriced purchase or a 'splits/shares the cost'
    # predicate on this entity declines the WHOLE total rather than
    # risk a silently dropped term). The subtraction is safe from
    # double-counting: a priced purchase ("buys a toy for $8") never
    # emits a currency-measured Quantity at all (learn.py emits an
    # ITEM-measured Quantity plus a separate Price fact), so it is
    # invisible to _entity_total's currency fold and only ever
    # appears once, here.
    entity = ctx.query["entity"]
    from ..account_totals import AccountTotal, has_resource_account, resolve_account
    if has_resource_account(ctx.store):
        result = resolve_account(ctx)
        if not isinstance(result, AccountTotal):
            return result
        requested = ctx.query.get("req_unit")
        if requested and ctx.reg.plural_to_singular.get(requested, requested) != result.opening.measure:
            return Answer("decline", None, "the requested currency differs from the resource account")
        return Answer("number", result.value,
                      f"{result.value:g} {result.opening.measure} remains in the "
                      f"{result.opening.qualifier + ' ' if result.opening.qualifier else ''}"
                      f"{result.opening.account}; this is not a total cash holding")
    measure = ctx.query.get("measure", "currency")
    singular = _resolve_measure(measure, ctx.store, ctx.reg, journal=ctx.log.journal)
    if singular is None:
        return Answer("decline", None,
                      f"measure {measure!r} is ambiguous across the facts")
    req_unit = ctx.query.get("req_unit")
    if not _check_req_unit(req_unit, singular, ctx.store, ctx.reg, journal=ctx.log.journal):
        return Answer(
            "decline", None,
            f"asked unit {req_unit!r} does not match resolved measure {singular!r}",
        )
    base = _entity_total(ctx.store, ctx.reg, entity, singular, ctx.log)
    if base is None:
        return Answer(
            "decline", None, f"no resolvable {singular!r} total for {entity!r}"
        )
    buys_exist = any(
        q.entity == entity and ctx.reg.word_in_category(q.verb, "purchase")
        for q in ctx.store.by_kind(Quantity)
    )
    spend = _purchase_total(ctx.store, ctx.reg, entity, ctx.log)
    if spend is None:
        if buys_exist:
            return Answer(
                "decline", None,
                f"{entity!r}'s purchases don't all resolve to a safe "
                "total (unpriced item or a cost-split predicate)",
            )
        spend = 0.0
    remaining = evaluate(f"{base} - {spend}", {}, ctx.log, source="money-left")
    if remaining < 0:
        return Answer(
            "decline", None,
            f"{entity!r}'s purchases ({spend}) exceed the money total "
            f"({base}) — remaining money is negative",
        )
    return Answer(
        "number", remaining,
        f"{base} (money fold) minus {spend} spent on priced purchases",
    )
