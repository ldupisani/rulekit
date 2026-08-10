"""Percentage occupied by one resolved partition of a finite collection."""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("partition-percentage", time_scoped=True)
def partition_percentage(ctx: ConsumerContext):
    """Return ``100 * subset / total`` for one exact partition fact.

    The premise machinery decides how the subset was formed. In particular,
    a share taken from a remainder is resolved to a count before it reaches
    this consumer. Keeping that sequencing out of the ask makes this consumer
    useful for any future partition surface with the same fact contract.
    """
    from ..answer import Answer
    from .. import deixis
    from ..evaluate import evaluate
    from ..model import PartitionQuantity, Quantity
    from ..totals import _entity_total

    collection = ctx.reg.plural_to_singular.get(
        ctx.query["collection"], ctx.query["collection"]
    )
    attribute = ctx.query["attribute"]
    parts = [
        part
        for part in ctx.store.by_kind(PartitionQuantity)
        if part.collection == collection
        and part.attribute == attribute
        and part.polarity
        and not part.is_fraction
        and not part.is_rest
    ]
    if len(parts) != 1:
        return Answer(
            "decline",
            None,
            f"resolved partition count is {len(parts)} for "
            f"{collection!r}/{attribute!r}",
        )

    entities = sorted(
        {q.entity for q in ctx.store.by_kind(Quantity) if q.measure == collection}
    )
    winner = deixis.resolve(
        [deixis.Referent(dimension=deixis.PERSON, key=entity) for entity in entities],
        deixis.Origo(),
        deixis.constant,
        dimension=deixis.PERSON,
        journal=ctx.log.journal,
        source="answer/partition-percentage-holder",
    )
    if winner is None:
        return Answer(
            "decline",
            None,
            f"partition total needs exactly one holder; found {len(entities)} "
            f"for {collection!r}",
        )

    total = _entity_total(ctx.store, ctx.reg, winner.key, collection, ctx.log)
    part = parts[0]
    if total is None or total <= 0:
        return Answer(
            "decline",
            None,
            f"partition total is not positive for {winner.key!r}/{collection!r}",
        )
    if part.value < 0 or part.value > total:
        return Answer(
            "decline",
            None,
            f"partition value {part.value} is outside the collection total {total}",
        )

    value = evaluate(
        f"100 * {part.value} / {total}",
        {},
        ctx.log,
        source="partition-percentage",
    )
    return Answer(
        "number",
        value,
        f"{part.value} {attribute!r} out of {total} total {collection!r}",
    )
