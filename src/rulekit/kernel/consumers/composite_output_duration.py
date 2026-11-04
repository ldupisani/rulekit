"""Invert an output rate after expanding explicitly uniform product extents."""

from collections import Counter
from math import isfinite
from . import consumer
from ..answer import Answer
from ..model import Rate
from ..reference_identity import ReferenceIdentity, reference_from_unit
from ..numeric_evidence import audit_numeric_mentions
from ..source_coverage import uncovered_units
from ..learn import simple_rate_evidence_units
from ..predicate_compatibility import predicates_compatible
from ..rate_calculation import apply_rate, rate_operands, convert_duration
from ..evaluate import evaluate


@consumer("composite-output-duration")
def consume(ctx):
    rates = ctx.store.by_kind(Rate)
    if (
        len(rates) != 1
        or len(ctx.store.facts) != 1
        or ctx.store.collisions
        or ctx.store.quarantined
    ):
        return Answer("decline", None, "one unambiguous output rate is required")
    rate = rates[0]
    count, extent = float(ctx.query["count"]), float(ctx.query["extent"])
    if (
        ctx.query_reference() != ReferenceIdentity(rate.entity)
        or rate.measure != ctx.query["measure"]
        or not predicates_compatible(
            rate.verb, ctx.query["verb"], rate.measure, ctx.reg
        )
        or not ctx.reg.measure_applies_to_holder(
            ctx.query["measure"], ctx.query["item"]
        )
        or not ctx.reg.word_in_category(rate.per, "duration_measure")
        or rate.value <= 0
        or any(not isfinite(v) or v < 0 for v in (count, extent))
        or not count.is_integer()
    ):
        return Answer(
            "decline",
            None,
            "the explicit product extent must match this actor’s output rate",
        )
    expected = {
        rate.provenance.sentence: Counter(rate_operands(rate)),
        ctx.question.sentence_index: Counter([count, extent]),
    }
    covered = {
        reading.sentence_index: simple_rate_evidence_units(reading, rate, ctx.reg)
        for reading in ctx.premises
        if reading.sentence_index == rate.provenance.sentence
    }
    if (
        any(
            reference_from_unit(unit).described
            for reading in ctx.premises
            for unit in reading.units
            if unit.sense() in ("noun", "name", "pronoun")
        )
        or any(
            uncovered_units(
                reading,
                (
                    ctx.match.consumed
                    if reading is ctx.question
                    else covered.get(reading.sentence_index, ())
                ),
            )
            for reading in (*ctx.premises, ctx.question)
        )
        or audit_numeric_mentions(
            (*ctx.premises, ctx.question),
            expected,
            missing="missing output operand",
            duplicate="repeated output operand",
        )
    ):
        return Answer("decline", None, "every rate, product and condition must be read")
    total = evaluate(
        "count * extent",
        dict(count=count, extent=extent),
        ctx.log,
        source="explicit-product-output",
    )
    value = apply_rate(
        rate, total, ctx.log, source="composite-output-duration", inverse=True
    )
    if ctx.query.get("unit"):
        value = convert_duration(
            value,
            rate.per,
            ctx.query["unit"],
            ctx.reg,
            ctx.log,
            source="composite-duration-unit",
        )
        if value is None:
            return Answer(
                "decline", None, "the requested duration unit is incompatible"
            )
    return Answer(
        "number",
        value,
        f"{value:g} {ctx.query.get("unit", rate.per)}; at the stated constant output rate",
    )
