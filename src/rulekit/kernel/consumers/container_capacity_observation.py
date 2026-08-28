"""Capacity established by complete-fit or full-container remainder evidence."""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("container-capacity-observation")
def container_capacity_observation(ctx: ConsumerContext):
    from ..answer import Answer
    from ..evaluate import EvaluationError, evaluate
    from ..model import ContainerCapacityInquiry, ContainerCapacityObservation
    from ..totals import _entity_total

    container = ctx.query["container"]
    measure = ctx.query["measure"]
    inquiries = [
        fact
        for fact in ctx.store.by_kind(ContainerCapacityInquiry)
        if fact.container == container
        and (fact.content is None or fact.content == measure)
    ]
    if len(inquiries) != 1:
        return Answer(
            "decline",
            None,
            f"capacity needs one compatible inquiry context; found {len(inquiries)}",
        )
    inquiry = inquiries[0]

    observations = [
        fact
        for fact in ctx.store.by_kind(ContainerCapacityObservation)
        if fact.content == measure
        and (fact.container is None or fact.container == container)
    ]
    if len(observations) != 1:
        return Answer(
            "decline",
            None,
            f"capacity needs one compatible fill observation; found {len(observations)}",
        )
    observation = observations[0]

    available = _entity_total(
        ctx.store,
        ctx.reg,
        inquiry.seeker,
        measure,
        ctx.log,
    )
    if available is None:
        return Answer(
            "decline",
            None,
            f"no complete available total for {inquiry.seeker!r}/{measure!r}",
        )

    if observation.mode == "all_available_fit":
        if ctx.query.get("allow_confirmed_fit") != "true":
            return Answer(
                "decline",
                None,
                "all-fit evidence establishes a confirmed amount, not exact capacity",
            )
        return Answer(
            "number",
            available,
            f"all {available:g} available {measure} fit in {container!r}",
        )

    if observation.mode != "remainder_after_fill":
        return Answer(
            "decline",
            None,
            f"unsupported capacity observation {observation.mode!r}",
        )
    if observation.value < 0 or observation.value > available:
        return Answer(
            "decline",
            None,
            f"remainder {observation.value:g} is outside available total {available:g}",
        )
    try:
        capacity = evaluate(
            f"{available} - {observation.value}",
            {},
            ctx.log,
            source="container-capacity-remainder",
        )
    except EvaluationError as exc:  # defensive: both operands are finite facts
        return Answer("decline", None, f"capacity arithmetic failed: {exc}")
    return Answer(
        "number",
        capacity,
        f"{available:g} available {measure} minus {observation.value:g} left outside",
    )
