"""`combined` — The combined total across holders.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("combined", time_scoped=True)
def combined(ctx: ConsumerContext):
    from ..answer import Answer
    from ..evaluate import evaluate
    from ..answer import _combined_holder_totals

    # `exclude_entity` (mining candidate entityless-total-recut): bound
    # ONLY by ask/how-many-there-combined (`exclude_entity: world` in
    # its own resolves block) — see `_combined_holder_totals`'s
    # docstring for why that ask alone needs an entity dropped.
    holders = _combined_holder_totals(
        ctx.store, ctx.reg, ctx.query, ctx.log,
        exclude_entity=ctx.query.get("exclude_entity"),
    )
    if isinstance(holders, Answer):
        return holders
    entities, totals = holders
    # `holder_count` is checked inside `_combined_holder_totals`
    # itself (see that function's own comment) — shared by this
    # branch and 'average' below.
    combined = evaluate(" + ".join(str(t) for t in totals), {}, ctx.log, source="combined")
    return Answer("number", combined, f"Σ over {entities}")
