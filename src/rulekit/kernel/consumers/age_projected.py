"""`age-projected` — Age N years from now, from the stated age.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("age-projected", time_scoped=True)
def age_projected(ctx: ConsumerContext):
    from ..answer import Answer
    from ..evaluate import evaluate
    from ..totals import _entity_total

    # mining candidate relation-standard-frames: "How old will X be in/
    # after N years?" / "...N years from now?" — a PROJECTED age ask,
    # sibling of ask/how-old-is: the SAME current-age quantity
    # (_entity_total, measure read from `query["measure"]` — constitution
    # rule 1, never a hardcoded 'year' literal; the ask's own `resolves:`
    # block commits `measure: year` exactly as ask/how-old-is does)
    # plus the stated offset named IN THE QUESTION ITSELF, added rather
    # than compared. Gated on this ask id alone (via the `consumer`
    # key), never a widening of `single-entity`'s own state-ask branch:
    # a projected ask's offset is not a measure/entity slot that
    # branch's owner/qualifier machinery could even express.
    entity, measure = ctx.query["entity"], ctx.query["measure"]
    offset_raw = ctx.query.get("offset")
    if offset_raw is None:
        return Answer(
            "decline", None, "projected age ask has no stated year offset",
        )
    offset = evaluate(str(offset_raw), {}, ctx.log, source="age-projected-offset")
    base = _entity_total(ctx.store, ctx.reg, entity, measure, ctx.log)
    if base is None:
        return Answer(
            "decline", None, f"no {measure} quantity known for {entity!r}",
        )
    return Answer(
        "number", base + offset,
        f"{entity!r}'s current {measure} {base} + stated offset {offset}",
    )
