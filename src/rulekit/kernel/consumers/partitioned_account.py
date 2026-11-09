"""Named stock/output partitions, package scaling and partition-specific valuation."""

from math import isfinite
from . import consumer
from ..answer import Answer, AnswerAssumption
from ..model import BatchEvidence, Quantity
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..resource_equations import FractionalAllocation, FractionBasis
from ..evaluate import evaluate
from ..reference_identity import reference_from_unit
from ..source_coverage import quantity_ledger_source_units
from ..rate_calculation import convert_duration, convert_units

KINDS = {
    "partition-pool",
    "partition-fraction",
    "partition-count",
    "partition-rest",
    "partition-price",
    "partition-price-offset",
    "partition-reference",
}


@consumer(
    "partitioned-account",
    applicable=lambda s: any(r.kind in KINDS for r in s.by_kind(BatchEvidence)),
)
def consume(ctx):
    def fail(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    quantities = list(ctx.store.by_kind(Quantity))
    pools = [r for r in rows if r.kind == "partition-pool"]
    shares = sorted(
        (r for r in rows if r.kind in {"partition-fraction", "partition-count"}),
        key=lambda r: (r.provenance.sentence, r.position),
    )
    rests = [r for r in rows if r.kind == "partition-rest"]
    quotes = [
        r for r in rows if r.kind in {"partition-price", "partition-price-offset"}
    ]
    references = [r for r in rows if r.kind == "partition-reference"]
    if (
        any(r.kind not in KINDS for r in rows)
        or len(rests) > 1
        or len(pools) > 1
        or not shares
    ):
        return fail("one complete partition with distinct labels is required")
    operands = []
    covered = {}
    scale = 1
    assumptions = []
    # Ordinary stated output totals retain their Quantity contract.
    if not pools:
        if len(quantities) != 1:
            return fail("the partition requires one explicit total")
        pool = quantities[0]
        if not ctx.reg.word_in_category(pool.verb, "scoped_quantity_predicate"):
            return fail("the partition total must state a holding or completed output")
        total, measure = pool.value, pool.measure
        owners = {r.acquisition_ref for r in shares if r.acquisition_ref is not None}
        if len(owners) != 1:
            return fail("owned shares must identify one holder")
        actor = next(iter(owners))
        if pool.entity_ref != actor:
            if not (
                pool.entity_ref is not None
                and not pool.entity_ref.resolved
                and ctx.reg.word_in_category(
                    pool.entity, "discourse_subject_group_pronoun"
                )
                and ctx.reg.word_in_category(actor.head, "collective_reference_holder")
            ):
                return fail("the total and partition owner disagree")
        operands.append((pool, [total]))
    else:
        pool = pools[0]
        total, measure = pool.value, pool.measure
        actor = pool.entity_ref
        operands.append((pool, [total]))
        if pool.container:
            if len(quantities) != 1:
                return fail(
                    "a per-package partition needs one matching package population"
                )
            purchase = quantities[0]
            if (
                purchase.measure != pool.container
                or purchase.content_ref is None
                or purchase.content_ref.head != measure
                or purchase.owner
                or purchase.qualifier
                or not ctx.reg.word_in_category(purchase.verb, "purchase")
                or purchase.provenance.sentence >= pool.provenance.sentence
            ):
                return fail("the package population must contain the partitioned item")
            actor = purchase.entity_ref
            scale = purchase.value
            operands.append((purchase, [purchase.value]))
        elif quantities:
            return fail("an additional quantity lies outside this partition")
        if pool.marker:
            if pool.per_member <= 0 or not pool.attribute:
                return fail("a repeated partition needs an explicit complete duration")
            scale = convert_duration(
                pool.per_member,
                pool.attribute,
                pool.marker,
                ctx.reg,
                ctx.log,
                source="partition-repetition-periods",
            )
            if scale is None or scale < 0 or not float(scale).is_integer():
                return fail("the repeated partition needs complete compatible periods")
            operands[0][1].append(pool.per_member)
            assumptions.append(
                AnswerAssumption(
                    "repeated-partition-composition",
                    "Each stated period uses the same partition and unit prices.",
                    (pool.provenance.sentence,),
                )
            )
    if actor is None or not actor.resolved:
        return fail("the partition needs one resolved owner")
    if ctx.query.get("entity") and reference_from_unit(ctx.match.slots["who"]) != actor:
        return fail("the question asks about another owner")
    labels = [(r.container_ref, r.attribute) for r in shares + rests]
    if len(labels) != len(set(labels)):
        return fail("partition labels must be distinct")
    amounts = {}
    try:
        ledger = FractionalAllocation(total, ctx.log)
    except ValueError as error:
        return fail(str(error))
    for index, row in enumerate(shares):
        if (
            row.measure != measure
            or row.acquisition_ref not in (None, actor)
            or row.entity_ref not in (None, actor)
            or row.provenance.assumption
            or not isfinite(row.value)
            or row.value < 0
        ):
            return fail("each share must name the same resource and owner")
        basis = FractionBasis.OPENING
        if row.marker:
            if not index or not ctx.reg.word_in_category(
                row.marker, "resource_remnant_attribute"
            ):
                return fail(
                    "a restricted resource share needs an established matching basis"
                )
            basis = FractionBasis.REMAINDER
        try:
            amount = (
                ledger.allocate(row.value, basis, source="partition-fraction-amount")
                if row.kind == "partition-fraction"
                else ledger.allocate_amount(row.value, source="partition-count-amount")
            )
        except ValueError as error:
            return fail(str(error))
        amounts[(row.container_ref, row.attribute)] = amount
        operands.append((row, [row.value]))
    remaining = ledger.balance
    if rests:
        rest = rests[0]
        if rest.measure and rest.measure != measure:
            return fail("the remainder names another resource")
        amounts[(rest.container_ref, rest.attribute)] = max(0, remaining)
        operands.append((rest, []))
    for row in references:
        if row.value != total or row.measure != measure:
            return fail("a repeated pool reference disagrees with its total")
        operands.append((row, [row.value]))
    if not all(
        isfinite(v) and v >= 0 and float(v).is_integer()
        for v in [total, scale, *amounts.values()]
    ):
        return fail("discrete partitions must contain whole nonnegative counts")
    operation = ctx.query.get("operation", "amount")
    if operation == "value":
        asked_item = reference_from_unit(ctx.match.slots["item"])
        if asked_item.head != measure or asked_item.described:
            return fail(
                "the expenditure question must identify the same complete item population"
            )
        if not rests or len(quotes) != len(amounts):
            return fail("every exhaustive partition needs its own unit price")
        prices = {}
        for row in sorted(quotes, key=lambda r: (r.provenance.sentence, r.position)):
            label = (row.container_ref, row.attribute)
            if label not in amounts or label in prices:
                return fail("a unit price must identify exactly one partition")
            value = row.value
            if row.kind == "partition-price-offset":
                if len(prices) != 1 or row.measure != next(iter(prices.values()))[1]:
                    return fail(
                        "a relative unit price needs one same-currency standard"
                    )
                value = evaluate(
                    "base + offset",
                    dict(base=next(iter(prices.values()))[0], offset=row.value),
                    ctx.log,
                    source="partition-relative-price",
                )
            prices[label] = (value, row.measure)
            if not isfinite(value) or value < 0:
                return fail("unit prices must be finite and nonnegative")
            operands.append((row, [row.value]))
        unit = ctx.query.get("measure") or next(iter(prices.values()))[1]
        terms = [
            convert_units(
                prices[k][0] * amount,
                prices[k][1],
                unit,
                ctx.reg,
                ctx.log,
                source="partition-price-unit",
            )
            for k, amount in amounts.items()
        ]
        if any(v is None for v in terms):
            return fail("partition prices must use compatible currencies")
        value = evaluate(
            "subtotal * periods",
            dict(subtotal=sum(terms), periods=scale),
            ctx.log,
            source="partition-valued-total",
        )
    else:
        if quotes or ctx.query["measure"] != measure:
            return fail("the requested resource must match this unvalued partition")
        scope = ctx.query_reference("scope")
        if scope is not None:
            target = (scope, "")
            amount = amounts.get(target)
        else:
            asked_item = reference_from_unit(ctx.match.slots["unit"])
            classifications = {
                q
                for q in asked_item.qualifiers
                if ctx.reg.word_in_category(q, "inventory_classification_attribute")
            }
            described = set(asked_item.qualifiers) - classifications
            known = (
                set(quantities[0].content_ref.qualifiers)
                if pools and pool.container
                else set()
            )
            if (
                asked_item.owner
                or asked_item.label
                or len(classifications) > 1
                or not described <= known
            ):
                return fail(
                    "the requested description does not match the stated item population"
                )
            amount = (
                amounts.get((None, next(iter(classifications))))
                if classifications
                else total
            )
        if amount is None:
            return fail("the requested partition label is not established")
        value = evaluate(
            "amount * population",
            dict(amount=amount, population=scale),
            ctx.log,
            source="partition-scaled-amount",
        )
    for q in quantities:
        reading = next(
            r for r in ctx.premises if r.sentence_index == q.provenance.sentence
        )
        footprint = quantity_ledger_source_units(reading, [q], ctx.reg)
        if footprint:
            covered[reading.sentence_index] = footprint
    if not closed_evidence(ctx, [*rows, *quantities], operands, covered=covered):
        return fail("every total, package, fraction, price and condition must be read")
    return finish_batch_answer(
        ctx,
        rows,
        value,
        "partition the stated total before scaling or applying each partition’s unit price",
        assumptions=assumptions,
    )
