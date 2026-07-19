"""`geometry` — a (shape, quantity) formula from the declarative table.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`log`
becoming `ctx.` lookups.

⚠ FINDING THE BLOCK'S END IS NOT "the next `if consumer ==`". `answer()` has
SHARED code between consumer branches — the temporal origo sits just below this
one — so a boundary drawn to the next branch would have swallowed it and moved
code that must run for every consumer into a single one. The boundary is the
first line that is not indented into the branch.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("geometry")
def geometry(ctx: ConsumerContext):
    from ..answer import Answer
    from ..evaluate import evaluate

    # Formula-selection (difg geometry domain): "what is the AREA of a CIRCLE
    # with RADIUS 5?" -> look up the (shape, quantity) formula in the pack's
    # declarative table, bind the named dimensions from the ask, evaluate.
    # NO per-domain Python (constitution): the formulas are DATA, this branch
    # is the generic evaluator. Definitive-or-decline: a formula whose named
    # dimensions are not all bound (wrong/missing dimension for the shape)
    # evaluates to a NameError and declines rather than guess.
    shape, quantity = ctx.query.get("shape"), ctx.query.get("quantity")
    expr = ctx.reg.geometry_formulas.get((shape, quantity))
    if expr is None:
        return Answer(
            "decline", None,
            f"no geometry formula for {quantity!r} of a {shape!r}",
        )
    env = {"pi": 3.141592653589793}
    for d, v in ((ctx.query.get("dim1"), ctx.query.get("val1")),
                 (ctx.query.get("dim2"), ctx.query.get("val2"))):
        if d and v not in (None, ""):
            env[d] = float(v)
    try:
        value = evaluate(expr, env, ctx.log, source="geometry")
    except Exception:
        return Answer(
            "decline", None,
            f"{quantity!r} of a {shape!r} needs dimensions its given ones "
            "do not supply",
        )
    # A pi-bearing area/volume is irrational; present it to 2 decimals, the
    # conventional precision for a geometry answer (and difg's own gold
    # rounding). Exact integer results (rectangle area 24, cube volume 27)
    # are unchanged by the round.
    return Answer(
        "number", round(value, 2), f"geometry: {quantity} of {shape} = {expr}"
    )
