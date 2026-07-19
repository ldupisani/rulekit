"""`list-statistic` — Statistics over the question's whole number list.

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


@consumer("list-statistic")
def list_statistic(ctx: ConsumerContext):
    from ..answer import Answer

    # "What is the AVERAGE of 4, 8, 15, 16, and 42?" — read every number in
    # the question and apply the named statistic. The statistic WORDS live in
    # the statistic sub-categories (categories/statistics.yaml); this branch
    # holds only the general math OPERATIONS (mean/median/max/min/product/
    # mode), dispatched by which sub-category the word is in — no word list
    # in Python (constitution rule 1). Definitive-or-decline.
    stat = ctx.query.get("stat", "")
    nums = [
        float(u.features["value"])
        for u in ctx.question.units
        if u.features.get("value_kind") == "count"
    ]
    if not nums:
        return Answer("decline", None, f"no numbers to take the {stat!r} of")
    # register every operand in the arithmetic log — they ARE all inputs to
    # the statistic, so value-accounting must see them consumed (else it
    # vetoes the commit for "stated count reached no fact"). The sum is just
    # the logging vehicle; the actual statistic is computed below.
    evaluate(" + ".join(f"{x:g}" for x in nums), {}, ctx.log, source="list-statistic")
    if ctx.reg.word_in_category(stat, "stat_mean"):
        result = sum(nums) / len(nums)
    elif ctx.reg.word_in_category(stat, "stat_median"):
        s = sorted(nums)
        n = len(s)
        result = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    elif ctx.reg.word_in_category(stat, "stat_max"):
        result = max(nums)
    elif ctx.reg.word_in_category(stat, "stat_min"):
        result = min(nums)
    elif ctx.reg.word_in_category(stat, "stat_product"):
        result = 1.0
        for x in nums:
            result *= x
    elif ctx.reg.word_in_category(stat, "stat_mode"):
        from collections import Counter

        counts = Counter(nums)
        top = counts.most_common()
        if len(top) > 1 and top[0][1] == top[1][1]:
            return Answer("decline", None, f"{stat!r} is not unique")
        result = top[0][0]
    else:
        return Answer("decline", None, f"unsupported statistic {stat!r}")
    return Answer(
        "number", round(result, 4), f"list {stat} of {len(nums)} values"
    )
