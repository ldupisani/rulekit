"""A requested fraction of unfinished progress through a measured product."""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("content-progress-remainder-fraction")
def content_progress_remainder_fraction(ctx: ConsumerContext):
    """Capacity minus completed matching events, scaled by one fraction.

    The ask supplies every semantic category and predicate used here.  This
    consumer owns only the reusable arithmetic and the refusal boundaries: one
    linked product, one capacity, a genuinely future target, and a nonnegative
    remainder.
    """

    from ..answer import Answer
    from ..evaluate import evaluate
    from ..facts import FactStore
    from ..measures import _resolve_measure
    from ..model import Predication, Quantity, Relation
    from ..totals import _verb_total

    entity = ctx.query["entity"]
    measure = ctx.query["measure"]
    verb = ctx.query["verb"]
    product_category = ctx.query["product_category"]
    capacity_verb = ctx.query["capacity_verb"]

    try:
        fraction = float(ctx.query["fraction"])
    except (KeyError, TypeError, ValueError):
        return Answer("decline", None, "the requested remainder fraction is unreadable")
    if not 0 < fraction <= 1:
        return Answer(
            "decline", None,
            f"requested remainder fraction {fraction} is outside one whole",
        )

    target_time = ctx.query.get("target_time")
    target_offset = ctx.reg.temporal_offsets.get(target_time)
    if target_offset is None or target_offset <= 0:
        return Answer(
            "decline", None,
            "the planned progress target needs one declared future marker",
        )

    singular = _resolve_measure(
        measure, ctx.store, ctx.reg, journal=ctx.log.journal
    )
    if singular is None:
        return Answer(
            "decline", None,
            f"measure {measure!r} is ambiguous across the facts",
        )

    products = [
        fact.dobj
        for fact in ctx.store.by_kind(Predication)
        if fact.subject == entity
        and fact.verb == verb
        and fact.polarity
        and fact.dobj is not None
        and ctx.reg.word_in_category(fact.dobj, product_category)
    ]
    products = list(dict.fromkeys(products))
    if len(products) != 1:
        return Answer(
            "decline", None,
            f"{len(products)} measured products link {entity!r} to {verb!r}; "
            "the remaining capacity needs exactly one",
        )
    product = products[0]

    capacities = [
        quantity
        for quantity in ctx.store.by_kind(Quantity)
        if quantity.entity == product
        and quantity.measure == singular
        and quantity.verb == capacity_verb
        and quantity.is_state
    ]
    if len(capacities) != 1:
        return Answer(
            "decline", None,
            f"{len(capacities)} capacities known for {product!r}/{singular!r}; "
            "the remainder needs exactly one",
        )

    # A known future event is planned evidence, not completed progress at the
    # question's present origo. Opaque past labels (for example a qualified
    # period) remain usable; only pack-declared positive offsets are excluded.
    completed_store = FactStore(facts=[
        fact
        for fact in ctx.store.facts
        if not (
            isinstance(fact, Quantity)
            and fact.entity == entity
            and fact.measure == singular
            and fact.verb == verb
            and fact.time in ctx.reg.temporal_offsets
            and ctx.reg.temporal_offsets[fact.time] > 0
        )
    ])
    matching_progress = [
        fact
        for fact in completed_store.by_kind(Quantity)
        if fact.entity == entity
        and fact.measure == singular
        and fact.verb == verb
    ]
    unresolved_progress_relations = [
        relation
        for relation in completed_store.by_kind(Relation)
        if relation.subject == entity
        and relation.measure == singular
        and relation.verb == verb
        and not any(
            quantity.provenance.source.startswith("synth/relation")
            and quantity.provenance.sentence == relation.provenance.sentence
            for quantity in matching_progress
        )
    ]
    if unresolved_progress_relations:
        return Answer(
            "decline", None,
            f"completed {verb!r} progress has an unresolved proportional event",
        )
    completed = _verb_total(
        completed_store, entity, singular, verb, ctx.log
    )
    if completed is None:
        return Answer(
            "decline", None,
            f"completed {verb!r} progress is not uniquely determined for "
            f"{entity!r}/{singular!r}",
        )

    capacity = capacities[0].value
    remaining = evaluate(
        f"{capacity} - {completed}", {}, ctx.log,
        source="content-progress-remainder",
    )
    if remaining < 0:
        return Answer(
            "decline", None,
            f"completed progress {completed} exceeds capacity {capacity}",
        )
    planned = evaluate(
        f"{remaining} * {fraction}", {}, ctx.log,
        source="content-progress-remainder-fraction",
    )
    return Answer(
        "number", planned,
        f"({capacity} capacity - {completed} completed) × {fraction}",
    )
