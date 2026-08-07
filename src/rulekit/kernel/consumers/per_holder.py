"""`per-holder` — one labelled total for every explicitly named holder.

This is the non-aggregating sibling of `combined`: both use the same exact
holder-list validation, measure resolution, state/event fold, and
definitive-or-decline boundary. `combined` sums the resolved values; this
consumer preserves them as an ordered series so holder identity cannot be
lost.

⚠ TIME-SCOPED: the shared total resolver has always run below the temporal
origo for `combined` and `average`. This consumer must receive that same
time-filtered store.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("per-holder", time_scoped=True)
def per_holder(ctx: ConsumerContext):
    from ..answer import Answer
    from ..totals import _combined_holder_totals

    holders = _combined_holder_totals(
        ctx.store,
        ctx.reg,
        ctx.query,
        ctx.log,
    )
    if isinstance(holders, Answer):
        return holders
    entities, totals = holders
    measure = ctx.query["measure"]
    values = [
        {"entity": entity, "measure": measure, "value": total}
        for entity, total in zip(entities, totals, strict=True)
    ]
    return Answer("series", values, f"per-holder totals for {entities}")
