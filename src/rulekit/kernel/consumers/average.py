"""`average` — The mean over the combined holders.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("average", time_scoped=True)
def average(ctx: ConsumerContext):
    from ..answer import Answer
    from ..evaluate import evaluate
    from ..answer import _combined_holder_totals

    # "what is/was the average number/amount of ITEM (that) they VERB?"
    # (mining candidate average-asks): the SAME holder enumeration the
    # 'combined' consumer uses (Σ over every holder of the resolved
    # measure, >=2-holders-or-decline, same state/event-verb fallback),
    # divided by the holder count. No new fact kind, no new decline
    # surface beyond what 'combined' already has.
    holders = _combined_holder_totals(ctx.store, ctx.reg, ctx.query, ctx.log)
    if isinstance(holders, Answer):
        return holders
    entities, totals = holders
    combined = evaluate(" + ".join(str(t) for t in totals), {}, ctx.log, source="combined")
    average = evaluate(
        f"({combined}) / {len(entities)}", {}, ctx.log, source="average"
    )
    return Answer("number", average, f"({combined}) ÷ {len(entities)} over {entities}")
