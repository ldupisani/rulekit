"""`coordinate` — Distance and slope over a coordinate pair.

Moved out of `answer.py` UNCHANGED (the extraction increment). Every branch,
message and computation is the original; the only edits are `query`/`reg`
becoming `ctx.` lookups. Pinned across the move by the consumer golden master
and by all eight corpus slices being byte-neutral.
"""

from __future__ import annotations

import math

from . import ConsumerContext, consumer


@consumer("coordinate")
def coordinate(ctx: ConsumerContext):
    from ..answer import Answer

    # The difg coordinate-geometry domain: a NAMED quantity over two POINTS
    # — "the distance between (0,0) and (3,4)", "the slope between (2,3) and
    # (5,3)". The quantity was chosen by the ask (rules/coordinate-ops.yaml)
    # and arrives as a structural opcode in query['op']; this branch holds
    # only the general FUNCTIONS, no English word (constitution rule 1).
    #
    # Operands arrive as the comma-separated `components` of a `point`-typed
    # slot (numbers.py _TUPLE), because every ask template interpolates to
    # text. Splitting them here is reading a STRUCTURE the kernel already
    # recognized, not parsing English (rule 2).
    op = ctx.query.get("op", "")
    try:
        p1 = [float(c) for c in str(ctx.query.get("p1", "")).split(",")]
        p2 = [float(c) for c in str(ctx.query.get("p2", "")).split(",")]
    except (TypeError, ValueError):
        return Answer("decline", None, f"{op!r} needs numeric coordinates")
    if len(p1) != len(p2) or len(p1) < 2:
        # Definitive-or-decline: points of different arity name no distance.
        return Answer("decline", None, f"{op!r} needs two points of equal arity")
    if op == "distance":
        # n-dimensional by construction — 2D and 3D read identically.
        result = math.sqrt(sum((b - a) ** 2 for a, b in zip(p1, p2)))
    elif op == "slope":
        if len(p1) != 2:
            return Answer("decline", None, "slope is defined for 2-D points")
        dx = p2[0] - p1[0]
        # A VERTICAL line has undefined slope, and the horizontal case is
        # 0 rather than undefined — so this guards dx, never dy. Same
        # definitive-or-decline policy as the tan pole.
        result = (p2[1] - p1[1]) / dx if dx != 0 else None
    else:
        return Answer("decline", None, f"unsupported operation {op!r}")
    if result is None:
        return Answer("decline", None, f"{op!r} not defined for the given points")
    return Answer("number", float(result), f"coordinate: {op} = {result}")
