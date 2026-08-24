"""Exact activity total over an explicitly enumerated set of periods."""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("event-period-total", time_scoped=True)
def event_period_total(ctx: ConsumerContext):
    """Sum one entity's event quantities in every and only named period.

    The ask consumes the complete period enumeration, so the ordinary
    single-time origo deliberately has nothing left to arbitrate. This
    consumer therefore owns the list boundary: every requested period must
    have direct event evidence, untimed events do not qualify, and activity
    outside the requested periods is ignored.
    """

    from ..answer import Answer
    from ..evaluate import evaluate
    from ..measures import _resolve_measure
    from ..model import Quantity

    entity = ctx.query["entity"]
    measure = ctx.query["measure"]
    verb = ctx.query["verb"]
    raw_periods = ctx.query.get("periods")
    if (
        not isinstance(raw_periods, list)
        or len(raw_periods) < 2
        or not all(
            isinstance(period, str) and period for period in raw_periods
        )
        or len(set(raw_periods)) != len(raw_periods)
    ):
        return Answer(
            "decline",
            None,
            "an event-period total needs two or more distinct named periods",
        )

    singular = _resolve_measure(
        measure,
        ctx.store,
        ctx.reg,
        journal=ctx.log.journal,
    )
    if singular is None:
        return Answer(
            "decline",
            None,
            f"measure {measure!r} is ambiguous across the facts",
        )

    periods = set(raw_periods)
    matching = [
        quantity
        for quantity in ctx.store.by_kind(Quantity)
        if quantity.entity == entity
        and quantity.measure == singular
        and quantity.verb == verb
        and quantity.time in periods
    ]
    if any(quantity.is_state for quantity in matching):
        return Answer(
            "decline",
            None,
            "a period activity total requires event evidence, not snapshots",
        )

    evidenced = {quantity.time for quantity in matching}
    missing = [period for period in raw_periods if period not in evidenced]
    if missing:
        return Answer(
            "decline",
            None,
            "no direct event evidence for requested period(s): "
            + ", ".join(missing),
        )

    value = evaluate(
        " + ".join(str(quantity.value) for quantity in matching),
        {},
        ctx.log,
        source="event-period-total",
    )
    return Answer(
        "number",
        value,
        f"Σ {verb!r} events for {entity!r}/{singular!r} over {raw_periods}",
    )
