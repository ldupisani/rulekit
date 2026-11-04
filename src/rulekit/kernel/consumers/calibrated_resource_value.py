"""Compose a measured input/output calibration, observations and a unit quote."""

from . import consumer
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..answer import Answer
from ..model import BatchEvidence
from ..reference_identity import constrains
from ..source_coverage import covered_temporal_annotation
from ..rate_calculation import apply_ratio, convert_units
from ..evaluate import evaluate


@consumer("calibrated-resource-value")
def consume(ctx):
    rows = list(ctx.store.by_kind(BatchEvidence))
    cal = [r for r in rows if r.kind == "measured-calibration"]
    inputs = [r for r in rows if r.kind == "calibration-input"]
    quotes = [r for r in rows if r.kind == "calibration-price"]
    contexts = [r for r in rows if r.kind == "calibration-context"]

    def fail(s):
        return Answer("decline", None, s)

    if (
        len(cal) != 1
        or len(quotes) != 1
        or not inputs
        or len(contexts) > 1
        or len(rows) != len(inputs) + 2 + len(contexts)
    ):
        return fail(
            "one calibration, complete input observations and one price are required"
        )
    cal, quote = cal[0], quotes[0]
    if (
        not constrains(ctx.query_reference(), cal.entity_ref)
        or quote.entity_ref != cal.entity_ref
        or quote.container != ctx.query["item"]
        or any(r.entity_ref != cal.entity_ref for r in contexts)
        or len({r.marker for r in inputs}) != len(inputs)
        or any(r.provenance.assumption for r in rows)
    ):
        return fail(
            "the calibrated collection, distinct input periods and sale must agree"
        )
    if (
        cal.acquisition
        and cal.acquisition != quote.container
        or not cal.acquisition
        and not ctx.reg.word_in_category(quote.container, "precipitation_output")
    ):
        return fail("the sale must identify the calibrated output substance")
    amounts = []
    for r in inputs:
        value = convert_units(
            r.value,
            r.measure,
            cal.measure,
            ctx.reg,
            ctx.log,
            source="calibration-input-unit",
        )
        if value is None:
            return fail("an observed input has an incompatible dimension")
        # A lexical weather predicate names the calibrated input substance.
        if r.attribute:
            if r.attribute != cal.attribute or r.entity_ref != cal.entity_ref:
                return fail(
                    "input observations must identify the calibrated resource and participant"
                )
        elif not ctx.reg.word_in_category(
            cal.attribute, "precipitation_resource"
        ) or not ctx.reg.word_in_category(r.verb, "weather_quantity_verb"):
            return fail("input observations must measure the calibrated resource")
        amounts.append(value)
    total = apply_ratio(cal.per_member, cal.value, sum(amounts), ctx.log,
                        source="calibrated-resource-output")
    if total is None:
        return fail("the calibration needs a positive basis and nonnegative amounts")
    total = convert_units(
        total,
        cal.container,
        quote.attribute,
        ctx.reg,
        ctx.log,
        source="calibrated-sale-unit",
    )
    if total is None:
        return fail("the output quantity and sale quote have incompatible dimensions")
    operands = [
        (cal, [cal.per_member]),
        (quote, [quote.value]),
        *((r, [r.value]) for r in inputs),
        *((r, []) for r in contexts),
    ]
    metadata = [f for f in ctx.store.facts if f not in rows]
    periods = {(r.provenance.sentence, r.marker) for r in inputs}
    if any(
        not covered_temporal_annotation(f, ctx.premises, cal.entity, periods)
        for f in metadata
    ):
        return fail("an additional event lies outside the calibrated account")
    if not closed_evidence(ctx, [*rows, *metadata], operands):
        return fail("every input, calibration, price and condition must be read")
    value = evaluate(
        "quantity * price",
        dict(quantity=total, price=quote.value),
        ctx.log,
        source="calibrated-resource-value",
    )
    return finish_batch_answer(
        ctx,
        rows,
        value,
        "apply the explicit calibration to all observations, then the unit price to the stated sale of all output",
    )
