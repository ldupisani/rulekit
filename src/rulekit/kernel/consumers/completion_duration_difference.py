"""Unit-normalized gap between two exact task-completion durations."""

from __future__ import annotations

from . import ConsumerContext, consumer


def _direction(word: str, ctx: ConsumerContext) -> int | None:
    """Deepest declared polarity inside the dedicated speed scope."""

    best_depth = -1
    result = None
    for category in ctx.reg.word_categories.get(word, ()):
        chain = ctx.reg.cat_ancestors(category)
        if "task_completion_speed_comparative" not in chain:
            continue
        for depth, candidate in enumerate(reversed(chain)):
            if candidate in ctx.reg.category_polarity and depth > best_depth:
                best_depth = depth
                result = ctx.reg.category_polarity[candidate]
    return result


@consumer("completion-duration-difference")
def completion_duration_difference(ctx: ConsumerContext):
    from ..answer import Answer
    from ..evaluate import evaluate
    from ..model import TaskCompletionDuration
    from ..totals import _conversion_factor

    participant_a = ctx.query["a"]
    participant_b = ctx.query["b"]
    task = ctx.query["task"]
    requested_unit = ctx.query["unit"]
    if participant_a == participant_b:
        return Answer(
            "decline",
            None,
            "a completion-duration comparison needs two distinct participants",
        )

    direction_word = ctx.query["direction"]
    direction = _direction(direction_word, ctx)
    if direction not in (-1, 1):
        return Answer(
            "decline",
            None,
            f"completion-speed direction {direction_word!r} is not declared",
        )

    def compatible(participant: str):
        rows = []
        for fact in ctx.store.by_kind(TaskCompletionDuration):
            if fact.participant != participant or fact.task != task:
                continue
            factor = _conversion_factor(ctx.reg, fact.unit, requested_unit)
            if factor is not None:
                rows.append((fact, factor))
        return rows

    rows_a = compatible(participant_a)
    rows_b = compatible(participant_b)
    if len(rows_a) != 1 or len(rows_b) != 1:
        return Answer(
            "decline",
            None,
            "a comparison needs exactly one compatible completion duration "
            f"for each participant; found {len(rows_a)} and {len(rows_b)}",
        )

    fact_a, factor_a = rows_a[0]
    fact_b, factor_b = rows_b[0]
    if fact_a.elapsed <= 0 or fact_b.elapsed <= 0:
        return Answer(
            "decline", None, "completion durations must be strictly positive"
        )

    elapsed_a = evaluate(
        f"{fact_a.elapsed} * {factor_a}",
        {},
        ctx.log,
        source="completion-duration-convert",
    )
    elapsed_b = evaluate(
        f"{fact_b.elapsed} * {factor_b}",
        {},
        ctx.log,
        source="completion-duration-convert",
    )
    ordering = -1 if elapsed_a < elapsed_b else 1 if elapsed_a > elapsed_b else 0
    if ordering == 0:
        return Answer(
            "decline", None, "equal completion durations do not license faster or slower"
        )
    if ordering != direction:
        return Answer(
            "decline",
            None,
            f"{direction_word!r} contradicts the stated completion durations",
        )

    gap = evaluate(
        f"abs({elapsed_a} - {elapsed_b})",
        {},
        ctx.log,
        source="completion-duration-difference",
    )
    return Answer(
        "number",
        gap,
        f"absolute completion-duration gap for {task!r} in {requested_unit!r}",
    )
