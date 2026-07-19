"""`partition-complement` — The remainder of a partitioned collection.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("partition-complement", time_scoped=True)
def partition_complement(ctx: ConsumerContext):
    from ..answer import Answer
    from .. import deixis
    from ..evaluate import evaluate
    from ..model import PartitionQuantity, Quantity
    from ..totals import _entity_total

    # "N of them are ADJ" premises name a subset of a collection; the
    # ask ("how many X are ADJ" / "how many X are not ADJ") either
    # reads the named subset directly or takes its EXACT complement
    # (total minus that one subset — always correct regardless of how
    # many OTHER subsets the collection has, since it is the
    # complement of THIS attribute specifically, never an
    # exhaustive-enumeration assumption).
    item = ctx.reg.plural_to_singular.get(ctx.query["item"], ctx.query["item"])
    attribute = ctx.query["attribute"]
    negated = ctx.query.get("negated") == "true"
    parts = [
        p for p in ctx.store.by_kind(PartitionQuantity)
        if p.collection == item and p.attribute == attribute and p.polarity
    ]
    if len(parts) != 1:
        return Answer(
            "decline", None,
            f"{len(parts)} partition facts known for {item!r}/{attribute!r}",
        )
    part = parts[0]
    if not negated:
        return Answer(
            "number", part.value, f"{part.value} of {item!r} are {attribute!r}"
        )
    entities = sorted(
        {q.entity for q in ctx.store.by_kind(Quantity) if q.measure == item}
    )
    # A THIRD unique-holder site the deixis.md inventory missed. Same shape, same
    # empty origo, same rule.
    if deixis.resolve(
        [deixis.Referent(dimension=deixis.PERSON, key=e) for e in entities],
        deixis.Origo(),
        deixis.constant,
        dimension=deixis.PERSON,
        journal=ctx.log.journal,
        source="answer/partition-total-holder",
    ) is None:
        return Answer(
            "decline", None,
            f"{len(entities)} entities hold {item!r} — the partition "
            "total needs exactly one",
        )
    total = _entity_total(ctx.store, ctx.reg, entities[0], item, ctx.log)
    if total is None:
        return Answer(
            "decline", None, f"{entities[0]!r} has no resolvable total for {item!r}"
        )
    return Answer(
        "number",
        evaluate(f"{total} - {part.value}", {}, ctx.log, source="partition-complement"),
        f"{total} total {item!r} minus {part.value} {attribute!r}",
    )
