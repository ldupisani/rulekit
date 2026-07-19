"""`trigonometry` — Trig functions over an angle in degrees.

Moved out of `answer.py` UNCHANGED (the extraction increment). Every branch,
message and computation is the original; the only edits are `query`/`reg`
becoming `ctx.` lookups. Pinned across the move by the consumer golden master
and by all eight corpus slices being byte-neutral.
"""

from __future__ import annotations

import math

from . import ConsumerContext, consumer


@consumer("trigonometry")
def trigonometry(ctx: ConsumerContext):
    from ..answer import Answer

    # The difg `trigonometry` domain: a NAMED trig function applied to one
    # angle — "What is the sine of 30 degrees?", "the tangent of 45 degrees".
    # The function was chosen by the ask (rules/trig-ops.yaml) and arrives as
    # a structural opcode in query['op']; this branch holds only the general
    # FUNCTIONS, no English word (constitution rule 1).
    #
    # The operand is ALWAYS in degrees: the ask gates it on the
    # `angle_degrees` category (categories/trig.yaml), which admits the
    # degree unit and nothing else, so the conversion below is unconditional
    # and safe. A radian operand never reaches here — it declines at the ask.
    op = ctx.query.get("op", "")
    try:
        deg = float(ctx.query.get("x"))
    except (TypeError, ValueError):
        return Answer("decline", None, f"{op!r} needs a numeric angle")
    rad = math.radians(deg)
    if op == "sin":
        result = math.sin(rad)
    elif op == "cos":
        result = math.cos(rad)
    elif op == "tan":
        # tan is UNDEFINED at 90 + 180k degrees, and math.tan does not raise
        # there — float error leaves cos(rad) at ~6.1e-17 instead of 0, so
        # math.tan(math.radians(90)) returns 1.633123935319537e+16.
        # Definitive-or-decline (constitution rule 4): a question with no
        # answer gets no commit. The guard tests the COSINE rather than
        # `deg % 180 == 90` so an operand that is numerically at the pole
        # (89.99999999999999) declines too, not just a literal 90.
        result = math.tan(rad) if abs(math.cos(rad)) > 1e-12 else None
    else:
        return Answer("decline", None, f"unsupported operation {op!r}")
    if result is None:
        return Answer("decline", None, f"{op!r} not defined for the given inputs")
    return Answer("number", float(result), f"trigonometry: {op} = {result}")
