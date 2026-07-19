"""`vector` — Magnitude and dot product over a spaced tuple.

Moved out of `answer.py` UNCHANGED (the extraction increment). Every branch,
message and computation is the original; the only edits are `query`/`reg`/
`question`/`log` becoming `ctx.` lookups.

This tier reads the QUESTION READING as well as the query — these consumers
take the question's whole number list rather than bound slots — which is why
`ConsumerContext` carries it. Pinned across the move by the consumer golden
master and by all eight corpus slices being byte-neutral.
"""

from __future__ import annotations

from ..evaluate import evaluate
from . import ConsumerContext, consumer


@consumer("vector")
def vector(ctx: ConsumerContext):
    from ..answer import Answer

    # The difg vector domain: "the magnitude of the vector (3, 4)" -> 5, "the
    # dot product of (1, 2, 3) and (4, 5, 6)" -> 32. A SPACED tuple is just
    # loose number tokens (the parens are dropped at tokenization), so this
    # reads the question's whole number list exactly as `list-statistic`
    # does — and is therefore arity-free. The operation arrives as a
    # structural opcode from the ask (rules/vector-ops.yaml); no English word
    # appears here (constitution rule 1).
    import math

    op = ctx.query.get("op", "")
    nums = [
        float(u.features["value"])
        for u in ctx.question.units
        if u.features.get("value_kind") == "count"
    ]
    if not nums:
        return Answer("decline", None, f"no components to take the {op!r} of")
    # Register every operand in the arithmetic log — they ARE all inputs, so
    # value-accounting must see them consumed (the `list-statistic` lesson:
    # otherwise it vetoes the commit for "stated count reached no fact").
    evaluate(" + ".join(f"{x:g}" for x in nums), {}, ctx.log, source="vector")
    if op == "magnitude":
        result = math.sqrt(sum(x * x for x in nums))
    elif op == "dot":
        # The two vectors are concatenated in the number list, so they split
        # down the middle. Definitive-or-decline: an ODD count cannot be two
        # equal-length vectors, so it declines rather than guessing a split.
        if len(nums) % 2:
            return Answer("decline", None, "a dot product needs two equal-length vectors")
        half = len(nums) // 2
        result = sum(a * b for a, b in zip(nums[:half], nums[half:]))
    else:
        return Answer("decline", None, f"unsupported operation {op!r}")
    return Answer("number", float(result), f"vector: {op} = {result}")
