"""`number-theory` — gcd / lcm / factorial / combinations.

Moved out of `answer.py` UNCHANGED (the extraction increment). Every branch,
message and computation is the original; the only edits are `query`/`reg`
becoming `ctx.` lookups. Pinned across the move by the consumer golden master
and by all eight corpus slices being byte-neutral.
"""

from __future__ import annotations

import math

from . import ConsumerContext, consumer


@consumer("number-theory")
def number_theory(ctx: ConsumerContext):
    from ..answer import Answer

    # "What is the GCD of 24 and 36?" / "7 factorial" / "8 choose 3" — dispatch
    # on the operation sub-category to a general math function. Integer inputs;
    # both bind ask slots (value-accounting satisfied). Definitive-or-decline:
    # a binary op with no second operand, or a non-integer input, declines.
    op = ctx.query.get("op", "")
    try:
        x = int(float(ctx.query.get("x")))
        y_raw = ctx.query.get("y")
        y = int(float(y_raw)) if y_raw not in (None, "") else None
    except (TypeError, ValueError):
        return Answer("decline", None, f"{op!r} needs integer inputs")
    if ctx.reg.word_in_category(op, "op_gcd"):
        result = math.gcd(x, y) if y is not None else None
    elif ctx.reg.word_in_category(op, "op_lcm"):
        result = math.lcm(x, y) if y is not None else None
    elif ctx.reg.word_in_category(op, "op_factorial"):
        result = math.factorial(x) if x >= 0 else None
    elif ctx.reg.word_in_category(op, "op_choose"):
        result = math.comb(x, y) if (y is not None and 0 <= y <= x) else None
    else:
        return Answer("decline", None, f"unsupported operation {op!r}")
    if result is None:
        return Answer("decline", None, f"{op!r} not defined for the given inputs")
    return Answer("number", float(result), f"number-theory: {op} = {result}")
