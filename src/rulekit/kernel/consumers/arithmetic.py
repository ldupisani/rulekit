"""`arithmetic` — Direct binary/unary arithmetic operations.

Moved out of `answer.py` UNCHANGED (the extraction increment). Every branch,
message and computation is the original; the only edits are `query`/`reg`
becoming `ctx.` lookups. Pinned across the move by the consumer golden master
and by all eight corpus slices being byte-neutral.
"""

from __future__ import annotations

import math

from . import ConsumerContext, consumer


@consumer("arithmetic")
def arithmetic(ctx: ConsumerContext):
    from ..answer import Answer

    # The difg `arithmetic` domain: a NAMED operator applied to one or two
    # literal operands — "25 plus 17", "7 times 8", "2 to the power of 10",
    # "the square root of 144", "17 percent of 240". The operator was chosen
    # by the ask (rules/arithmetic-ops.yaml) and arrives as a structural
    # opcode in query['op']; this branch holds only the general FUNCTIONS, no
    # English word (constitution rule 1 — the operator words are YAML literals,
    # never enumerated here). Definitive-or-decline: divide-by-zero and the
    # square root of a negative decline rather than error.
    op = ctx.query.get("op", "")
    try:
        x = float(ctx.query.get("x"))
        y_raw = ctx.query.get("y")
        y = float(y_raw) if y_raw not in (None, "") else None
    except (TypeError, ValueError):
        return Answer("decline", None, f"{op!r} needs numeric inputs")
    if op == "add":
        result = x + y if y is not None else None
    elif op == "subtract":
        result = x - y if y is not None else None
    elif op == "multiply":
        result = x * y if y is not None else None
    elif op == "divide":
        result = x / y if y not in (None, 0.0) else None
    elif op == "power":
        result = x ** y if y is not None else None
    elif op == "sqrt":
        result = math.sqrt(x) if x >= 0 else None
    elif op == "percent":
        result = x * y if y is not None else None
    elif op == "percent_change":
        # SIGNED relative change from x to y, as a percentage. One formula
        # serves both directions -- an 'increase' and a 'decrease' ask
        # differ only in which sign the answer comes out with, so there is
        # no second opcode and no English word in this branch. x == 0 has
        # no relative change to report and declines (None) rather than
        # dividing.
        result = (y - x) / x * 100.0 if y is not None and x != 0.0 else None
    else:
        return Answer("decline", None, f"unsupported operation {op!r}")
    if result is None:
        return Answer("decline", None, f"{op!r} not defined for the given inputs")
    return Answer("number", float(result), f"arithmetic: {op} = {result}")
