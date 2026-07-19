"""`change` — Change from a payment after a purchase.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("change", time_scoped=True)
def change(ctx: ConsumerContext):
    from ..answer import Answer
    from ..evaluate import evaluate
    from ..model import Predication, Quantity
    from ..answer import _purchase_total

    # "how much change does/did/will WHO get/receive/take (back)"
    # (mining candidate change-asks): the buyer's stated TENDER minus
    # its priced purchases (_purchase_total, UNCHANGED — the
    # increment-10 invariant travels with it unscoped: any unpriced
    # purchase or a cost-splitting predicate on this entity declines
    # the whole total). A tender is the general SVO fold's own plain
    # currency Quantity EVENT for a tender_verb-category verb (pay/
    # give) — no new fact kind, no learn.py change needed (see
    # packs/difg-mined/categories/semantic.yaml's tender_verb
    # docstring). Both 'pay' and 'give' are already 'lose'-tagged,
    # signed event Quantities that already participate in the
    # general money fold elsewhere unchanged — this consumer is the
    # only thing that additionally reads one as a TENDER.
    #
    # UNLIKE money-left, a change ask presupposes a purchase actually
    # happened, so "no priced purchase found" here is a structural
    # extraction gap, never evidence of zero spend (a family visiting
    # an amusement park and paying per-person ticket prices the fold
    # can't multiply out — a real dev-train shape — is exactly this
    # gap) — this consumer DECLINES rather than defaulting spend to 0
    # whenever _purchase_total has nothing to offer, for any reason.
    entity = ctx.query["entity"]
    tenders = [
        q for q in ctx.store.by_kind(Quantity)
        if q.entity == entity
        and not q.is_state
        and ctx.reg.word_in_category(q.verb, "tender_verb")
        and ctx.reg.word_in_category(q.measure, "currency")
    ]
    if len(tenders) != 1:
        return Answer(
            "decline", None,
            f"{len(tenders)} tender facts known for {entity!r} — a "
            "change ask needs exactly one stated payment amount",
        )
    tender = tenders[0]
    # A discount/tip predicate on the SAME buyer (packs/difg-mined/
    # categories/semantic.yaml's `discount` category — 'coupon'/
    # 'discount'/'tip') means the raw priced-purchase total isn't
    # necessarily the final amount owed: the increment-10 'splits the
    # cost' unconsumed-predicate discipline, generalized from one
    # specific verb (divide) to a dobj CATEGORY, since a tip/discount
    # is stated as a noun object ("gave a tip", "used a coupon"), not
    # a verb. _purchase_total has no way to see this — decline rather
    # than risk a confident-wrong change amount.
    if any(
        p.subject == entity and p.dobj is not None
        and ctx.reg.word_in_category(p.dobj, "discount")
        for p in ctx.store.by_kind(Predication)
    ):
        return Answer(
            "decline", None,
            f"{entity!r} has a discount/tip predicate — the raw "
            "purchase total is not necessarily the final amount owed",
        )
    spend = _purchase_total(ctx.store, ctx.reg, entity, ctx.log)
    if spend is None:
        return Answer(
            "decline", None,
            f"no resolvable priced-purchase total for {entity!r} — a "
            "change ask needs at least one priced purchase to subtract",
        )
    change = evaluate(f"{tender.value} - {spend}", {}, ctx.log, source="change")
    if change < 0:
        return Answer(
            "decline", None,
            f"{entity!r}'s purchases ({spend}) exceed the tendered "
            f"amount ({tender.value}) — change would be negative",
        )
    return Answer(
        "number", change,
        f"{tender.value} (tender) minus {spend} spent on priced purchases",
    )
