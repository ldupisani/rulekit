"""`measure-cost` — Cost of a geometric measure at a unit rate.

Moved out of `answer.py` UNCHANGED (the extraction increment). Every branch,
message and computation is the original; the only edits are `query`/`reg`
becoming `ctx.` lookups. Pinned across the move by the consumer golden master
and by all eight corpus slices being byte-neutral.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("measure-cost")
def measure_cost(ctx: ConsumerContext):
    from ..answer import Answer

    # cost = (a geometric measure of a W-by-H rectangle) x (a unit rate),
    # optionally taxed. The operation arrives as a structural OPCODE the
    # ask named (rules/measure-cost.yaml); no operation WORD reaches here,
    # and the ask's own rate-unit shape has already cross-checked it.
    op = ctx.query.get("op", "")
    try:
        d1 = float(ctx.query.get("d1"))
        d2 = float(ctx.query.get("d2"))
        rate = float(ctx.query.get("rate"))
    except (TypeError, ValueError):
        return Answer("decline", None, "measure-cost needs two measures and a rate")
    if d1 <= 0 or d2 <= 0:
        # a rectangle with a non-positive side is not a shape; decline
        # rather than return a zero or negative cost
        return Answer("decline", None, "a measure must be positive")
    if op == "area":
        measure = d1 * d2
    elif op == "perimeter":
        measure = 2.0 * (d1 + d2)
    else:
        return Answer("decline", None, f"unsupported measure operation {op!r}")
    total = measure * rate
    raw_tax = ctx.query.get("tax")
    if raw_tax not in (None, ""):
        try:
            total *= 1.0 + float(raw_tax)
        except (TypeError, ValueError):
            # the ask BOUND a tax and the consumer cannot read it -- decline
            # rather than silently answering the untaxed total, which is a
            # confident wrong answer to a question that stated a tax
            return Answer("decline", None, f"unreadable tax rate {raw_tax!r}")
    return Answer(
        "number", total,
        f"measure-cost: {op} {measure} x {rate}"
        + (f" +{raw_tax} tax" if raw_tax not in (None, "") else ""),
    )
