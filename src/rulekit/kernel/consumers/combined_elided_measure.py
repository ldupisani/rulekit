"""`combined-elided-measure` — A combined total whose measure is elided.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("combined-elided-measure", time_scoped=True)
def combined_elided_measure(ctx: ConsumerContext):
    from ..answer import Answer
    from ..evaluate import evaluate
    from ..model import Quantity
    from ..totals import _combined_holder_totals

    # mining candidate plural-np-totality-asks: the named-pair sibling
    # of `single-entity-elided-measure` above — "how many do Tom and
    # Jerry have combined?" has NO item slot at all. Mirrors that
    # branch's unique-measure-in-play discipline, but BILATERAL: the
    # elided measure is the ONE measure BOTH named holders share (set
    # intersection of what each holds), never guessed when zero or
    # more than one measure is common to both. Once resolved, this
    # reuses `_combined_holder_totals` exactly as ask/how-many-
    # combined-named does — a/b bound, so it sums exactly those two,
    # never the enumerate-all-holders fallback.
    a, b = ctx.query["a"], ctx.query["b"]
    cand_a = {q.measure for q in ctx.store.by_kind(Quantity) if q.entity == a}
    cand_b = {q.measure for q in ctx.store.by_kind(Quantity) if q.entity == b}
    common = sorted(cand_a & cand_b)
    if len(common) != 1:
        return Answer(
            "decline", None,
            f"{a!r} and {b!r} share {len(common)} measures — an "
            "elided-measure combined ask needs exactly one",
        )
    holders = _combined_holder_totals(ctx.store, ctx.reg, dict(ctx.query, measure=common[0]), ctx.log)
    if isinstance(holders, Answer):
        return holders
    entities, totals = holders
    combined = evaluate(" + ".join(str(t) for t in totals), {}, ctx.log, source="combined")
    return Answer("number", combined, f"Σ over {entities}")
