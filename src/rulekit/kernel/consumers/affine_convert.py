"""`affine-convert` — Scale conversion with a zero point (temperature).

Moved out of `answer.py` UNCHANGED (the extraction increment). Every branch,
message and computation is the original; the only edits are `query`/`reg`
becoming `ctx.` lookups. Pinned across the move by the consumer golden master
and by all eight corpus slices being byte-neutral.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("affine-convert")
def affine_convert(ctx: ConsumerContext):
    from ..answer import Answer

    # A scale with its own ZERO POINT: to = (from + offset) * factor. The
    # scale names arrive as slot lemmas and the pair is looked up as DATA
    # (rulekit/affine-conversions@1) -- no scale is named here, so a pair
    # the table does not hold declines rather than being approximated by a
    # bare factor, which is the whole reason this is not `conversions@1`.
    src, dst = ctx.query.get("from", ""), ctx.query.get("to", "")
    try:
        value = float(ctx.query.get("value"))
    except (TypeError, ValueError):
        return Answer("decline", None, "a conversion needs a numeric quantity")
    if src == dst:
        return Answer("decline", None, f"{src!r} is already the target scale")
    pair = ctx.reg.affine_scales.get((src, dst))
    if pair is None:
        return Answer("decline", None, f"no known scale conversion from {src!r} to {dst!r}")
    offset, factor = pair
    result = (value + offset) * factor
    return Answer(
        "number", float(result),
        f"affine-convert: {value} {src} -> {dst} = {result}",
    )
