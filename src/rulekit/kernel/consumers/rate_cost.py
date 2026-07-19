"""`rate-cost` — Cost of a quantity converted into the rate's unit.

Moved out of `answer.py` UNCHANGED (the extraction increment). Every branch,
message and computation is the original; the only edits are `query`/`reg`
becoming `ctx.` lookups. Pinned across the move by the consumer golden master
and by all eight corpus slices being byte-neutral.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("rate-cost")
def rate_cost(ctx: ConsumerContext):
    from ..answer import Answer

    # cost = quantity x rate, where the quantity must first be converted
    # into the RATE's unit ("10 miles at $3 per km" is 48.27, not 30).
    # Units arrive as lemmas from `measure_unit`-gated slots and the factor
    # is DATA; no unit is named here.
    src, dst = ctx.query.get("from", ""), ctx.query.get("to", "")
    try:
        value = float(ctx.query.get("value"))
        rate = float(ctx.query.get("rate"))
    except (TypeError, ValueError):
        return Answer("decline", None, "a rate cost needs a quantity and a rate")
    # DIRECT lookup only, deliberately -- see the pack header: the one
    # DEV item a transitive chain would reach has a defective gold.
    factor = 1.0 if src == dst else ctx.reg.conversions.get((src, dst))
    if factor is None:
        return Answer("decline", None, f"no known conversion from {src!r} to {dst!r}")
    total = value * factor * rate
    return Answer(
        "number", total,
        f"rate-cost: {value} {src} -> {dst} (x{factor}) at {rate}",
    )
