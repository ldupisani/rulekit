"""Project an observed measurement using a planned rate over an explicit horizon."""

from collections import Counter, defaultdict
from math import isfinite
from . import consumer
from ..answer import Answer
from ..evaluate import evaluate
from ..model import BatchEvidence
from ..numeric_evidence import audit_numeric_mentions
from ..rate_calculation import convert_duration, convert_units
from ..reference_identity import reference_from_unit
from ..source_coverage import uncovered_document_units


@consumer("projected-measured-state")
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    openings = [r for r in rows if r.kind == "forecast-opening"]
    rates = [r for r in rows if r.kind == "forecast-rate"]
    if (
        len(openings) != 1
        or len(rates) != 1
        or len(rows) != 2
        or len(ctx.store.facts) != 2
        or ctx.store.collisions
        or ctx.store.quarantined
    ):
        return decline(
            "one observed state, explicit horizon and planned change rate are required"
        )
    opening, rate = openings[0], rates[0]
    who = reference_from_unit(ctx.match.slots["who"])
    if (
        opening.entity_ref != who
        or rate.entity_ref != who
        or opening.container_ref != rate.container_ref
        or rate.container_ref != reference_from_unit(ctx.match.slots["event"])
        or opening.provenance.sentence >= rate.provenance.sentence
        or any(
            r.provenance.assumption or not isfinite(r.value) or r.value < 0
            for r in rows
        )
        or opening.per_member < 0
    ):
        return decline(
            "the observed state and planned rate must identify the same participant and deadline"
        )
    periods = convert_duration(
        opening.per_member,
        opening.acquisition,
        rate.acquisition,
        ctx.reg,
        ctx.log,
        source="forecast-duration",
    )
    unit_rate = convert_units(
        rate.value,
        rate.measure,
        opening.measure,
        ctx.reg,
        ctx.log,
        source="forecast-rate-unit",
    )
    if periods is None or unit_rate is None:
        return decline(
            "the horizon and rate need compatible temporal and measurement units"
        )
    if rate.sign not in (-1, 1):
        return decline("the planned change must have one explicit direction")
    expected = defaultdict(Counter)
    expected[opening.provenance.sentence].update([opening.value, opening.per_member])
    expected[rate.provenance.sentence][rate.value] += 1
    if uncovered_document_units(
        ctx.premises, ctx.question, ctx.match.consumed
    ) or audit_numeric_mentions(
        (*ctx.premises, ctx.question),
        expected,
        missing="missing",
        duplicate="duplicate",
    ):
        return decline("every forecast condition, amount and period must be read")
    value = evaluate(
        "opening + sign * rate * periods",
        {
            "opening": opening.value,
            "sign": rate.sign,
            "rate": unit_rate,
            "periods": periods,
        },
        ctx.log,
        source="planned-linear-change",
    )
    if value < 0:
        return decline("the planned rate crosses zero; a stopping condition is needed")
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    return Answer(
        "number",
        value,
        "project the stated rate over the explicit time to the event; this is a planned outcome",
    )
