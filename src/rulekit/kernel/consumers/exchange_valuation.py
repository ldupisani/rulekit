"""Equal-face-value exchange followed by an explicitly priced subset."""

from math import isclose
from . import consumer
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..answer import Answer
from ..model import BatchEvidence, Quantity
from ..reference_identity import constrains
from ..evaluate import evaluate
from ..rate_calculation import convert_units
from ..source_coverage import quantity_ledger_source_units, uncovered_units


@consumer("exchange-valuation")
def consume(ctx):
    rows = list(ctx.store.by_kind(BatchEvidence))
    holdings = list(ctx.store.by_kind(Quantity))
    plans = [r for r in rows if r.kind == "coin-exchange-plan"]
    completed = [r for r in rows if r.kind == "coin-exchange-completed"]
    priced = [r for r in rows if r.kind == "coin-subset-value"]

    def fail(s):
        return Answer("decline", None, s)

    if len(priced) != 1 or len(plans) + len(completed) != 1 or len(rows) != 2:
        return fail(
            "one completed equal-value exchange and one priced subset are required"
        )
    exchange = (plans or completed)[0]
    special = priced[0]
    covered = {}
    operands = []
    if plans:
        if (
            len(holdings) != 1
            or not special.entity
            or special.provenance.sentence <= exchange.provenance.sentence
        ):
            return fail(
                "an intention needs the later return-and-discovery evidence to establish completion"
            )
        old = holdings[0]
        old_coin = old.measure
        count = old.value
        reading = next(
            r for r in ctx.premises if r.sentence_index == old.provenance.sentence
        )
        footprint = quantity_ledger_source_units(reading, [old], ctx.reg)
        if (
            (not footprint and uncovered_units(reading))
            or not old.is_state
            or old.entity_ref != exchange.entity_ref
        ):
            return fail(
                "the exchange must refer to the actor’s single original coin holding"
            )
        covered[reading.sentence_index] = footprint
        operands.append((old, [count]))
        operands.append((exchange, []))
    else:
        if holdings:
            return fail("an additional holding lies outside the exchange")
        old_coin = exchange.container
        count = exchange.value
        operands.append((exchange, [count]))
    if (
        special.provenance.sentence <= exchange.provenance.sentence
        or not constrains(ctx.query_reference(), exchange.entity_ref)
        or special.entity
        and special.entity_ref != exchange.entity_ref
        or special.measure != exchange.measure
        or special.container != exchange.measure
        or not special.container_ref
        or not special.container_ref.qualifiers
        or not 0 <= special.value <= 1
        or count < 0
        or not float(count).is_integer()
    ):
        return fail(
            "the original holding, exchanged denomination and special subset must agree"
        )
    source = ctx.reg.attribute_value(old_coin, "cents")
    target = ctx.reg.attribute_value(exchange.measure, "cents")
    units = ctx.reg.category_members.get("coin_face_value_unit", ())
    if source is None or target is None or target <= 0 or len(units) != 1:
        return fail("the coin face values and their denomination must be declared")
    exchanged = evaluate(
        "count * old / new",
        dict(count=count, old=source, new=target),
        ctx.log,
        source="equal-value-coin-exchange",
    )
    subset = evaluate(
        "count * fraction",
        dict(count=exchanged, fraction=special.value),
        ctx.log,
        source="revalued-coin-subset",
    )
    if not isclose(exchanged, round(exchanged), abs_tol=1e-8) or not isclose(
        subset, round(subset), abs_tol=1e-8
    ):
        return fail("a coin exchange and subset require whole coin counts")
    ordinary = convert_units(
        (exchanged - subset) * target,
        next(iter(units)),
        special.attribute,
        ctx.reg,
        ctx.log,
        source="ordinary-coin-value",
    )
    if ordinary is None:
        return fail(
            "the special price and coin face values use incompatible currencies"
        )
    operands.append((special, [special.value, special.per_member]))
    if not closed_evidence(ctx, [*rows, *holdings], operands, covered=covered):
        return fail("every exchange, valuation and condition must be read")
    value = evaluate(
        "ordinary + count * price",
        dict(ordinary=ordinary, count=subset, price=special.per_member),
        ctx.log,
        source="exchanged-money-value",
    )
    return finish_batch_answer(
        ctx,
        rows,
        value,
        "ordinary coins retain face value; only the stated special subset receives the quoted value",
    )
