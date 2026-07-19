"""`unit-convert` — Unit conversion from the conversions table.

Moved out of `answer.py` UNCHANGED (the extraction increment). Every branch,
message and computation is the original; the only edits are `query`/`reg`
becoming `ctx.` lookups. Pinned across the move by the consumer golden master
and by all eight corpus slices being byte-neutral.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("unit-convert")
def unit_convert(ctx: ConsumerContext):
    from ..answer import Answer

    # The difg `unit_conversion` domain: "How many inches are in 3 feet?" —
    # multiply by the factor the CONVERSIONS TABLE already holds
    # (rulekit/conversions@1; the registry stores both directions). The unit
    # words arrive as slot lemmas from a `measure_unit`-gated ask
    # (rules/unit-convert.yaml) and are looked up as DATA — no unit is named
    # in Python (constitution rule 1), so a pair the table does not know
    # declines rather than guessing.
    src, dst = ctx.query.get("from", ""), ctx.query.get("to", "")
    try:
        value = float(ctx.query.get("value"))
    except (TypeError, ValueError):
        return Answer("decline", None, "a conversion needs a numeric quantity")
    if src == dst:
        # A unit converts to itself by 1, but the ask shape only reaches here
        # via two DISTINCT unit mentions; treat it as unread rather than
        # inventing an identity conversion.
        return Answer("decline", None, f"{src!r} is already the target unit")
    factor = ctx.reg.conversions.get((src, dst))
    if factor is None:
        return Answer("decline", None, f"no known conversion from {src!r} to {dst!r}")
    result = value * factor
    return Answer("number", float(result), f"unit-convert: {value} {src} -> {dst} = {result}")
