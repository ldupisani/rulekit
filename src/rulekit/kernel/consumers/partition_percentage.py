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


@consumer("enumerated-category-percentage")
def enumerated_category_percentage(ctx):
    """A document-local inventory or explicit total, without closing its taxonomy."""
    from collections import Counter, defaultdict
    from math import isfinite
    from ..answer import Answer
    from ..evaluate import evaluate
    from ..model import Quantity
    from ..numeric_evidence import audit_numeric_mentions
    from ..resource_equations import resource_residual
    from ..source_coverage import quantity_source_units, uncovered_units

    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(Quantity))
    collection, subtype = ctx.query["collection"], ctx.query["subtype"]
    if (not rows or len(rows) != len(ctx.store.facts)
            or ctx.store.collisions or ctx.store.quarantined
            or not ctx.reg.word_in_category(subtype, collection)
            or collection == subtype):
        return decline("one explicit category inventory and a strict subtype are required")
    unlocated = set(ctx.query["unlocated_sources"])
    holders = {q.entity_ref for q in rows if q.provenance.source not in unlocated}
    if len(holders) > 1:
        return decline("the inventory cannot merge different holders or locations")
    expected = defaultdict(Counter)
    keyed = {}
    for row in rows:
        if (not row.is_state or row.provenance.assumption or row.time is not None
                or any((row.owner, row.qualifier, row.measure_qualifier, row.label))
                or not isfinite(row.value) or row.value < 0 or not float(row.value).is_integer()
                or row.measure in keyed
                or row.measure != collection and not ctx.reg.word_in_category(row.measure, collection)):
            return decline("counts must enumerate distinct unqualified subtypes of the same category")
        keyed[row.measure] = row.value
        expected[row.provenance.sentence][row.value] += 1
    parts = {key: value for key, value in keyed.items() if key != collection}
    if subtype not in parts:
        return decline("the selected subtype needs an explicit count")
    keys = list(parts)
    if any(ctx.reg.category_terms_overlap(a, b) for i, a in enumerate(keys) for b in keys[i + 1:]):
        return decline("overlapping subtype descriptions cannot form disjoint inventory parts")
    subtotal = resource_residual(parts.values(), [], ctx.log, source="enumerated-category-total")
    if collection in keyed:
        total = keyed[collection]
        if subtotal > total:
            return decline("the subtype counts exceed the explicit category total")
    elif len(parts) >= 2:
        total = subtotal
    else:
        return decline("a single subtype does not establish its category population")
    coverage = {r.sentence_index: set() for r in ctx.premises}
    for row in rows:
        reading = next((r for r in ctx.premises if r.sentence_index == row.provenance.sentence), None)
        if reading is not None:
            coverage[reading.sentence_index].update(quantity_source_units(reading, row, ctx.reg))
    unread = (any(uncovered_units(r, coverage[r.sentence_index]) for r in ctx.premises)
              or uncovered_units(ctx.question, ctx.match.consumed))
    if (total <= 0 or unread
            or audit_numeric_mentions((*ctx.premises, ctx.question), expected,
                                      missing="missing", duplicate="duplicate")):
        return decline("the complete inventory and every numerical condition must be read")
    selected = parts[subtype]
    if ctx.query["negated"] == "true":
        selected = resource_residual([total], [selected], ctx.log, source="category-complement")
    value = evaluate("100 * selected / total", {"selected": selected, "total": total},
                     ctx.log, source="category-population-percentage")
    return Answer("number", value, "percentage of the explicitly enumerated inventory or stated category total")
