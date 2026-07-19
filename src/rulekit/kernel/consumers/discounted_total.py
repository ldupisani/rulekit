"""`discounted-total` — A price adjusted by a discount and a tax.

Moved out of `answer.py` UNCHANGED (the extraction increment). Every branch,
message and computation is the original; the only edits are `query`/`reg`
becoming `ctx.` lookups. Pinned across the move by the consumer golden master
and by all eight corpus slices being byte-neutral.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("discounted-total")
def discounted_total(ctx: ConsumerContext):
    from ..answer import Answer

    # total = base x [qty] x (1 - discount) x (1 + tax). The ORDER is
    # semantic: tax applies to the DISCOUNTED price, which is what the
    # question says and what every jurisdiction does. Fixed here rather
    # than left to slot arrival, because the other order is a different
    # number.
    def _opt(key):
        raw = ctx.query.get(key)
        if raw in (None, ""):
            return None
        return float(raw)

    try:
        total = float(ctx.query.get("base"))
        qty = _opt("qty")
        discount = _opt("discount")
        tax = _opt("tax")
    except (TypeError, ValueError):
        return Answer("decline", None, "discounted-total needs a numeric base")
    if qty is not None:
        total *= qty
    if discount is not None:
        if not 0.0 <= discount < 1.0:
            # a discount of 100% or more is not a price reduction, and a
            # negative one is a surcharge wearing the wrong word --
            # decline rather than return a zero or negative total
            return Answer("decline", None, f"{discount!r} is not a usable discount")
        total *= 1.0 - discount
    if tax is not None:
        if tax < 0.0:
            return Answer("decline", None, f"{tax!r} is not a usable tax rate")
        total *= 1.0 + tax
    return Answer(
        "number", total,
        f"discounted-total: base x qty={qty} discount={discount} tax={tax}",
    )
