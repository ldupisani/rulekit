"""A fixed included block followed by an explicitly quoted excess rate."""

from math import isfinite

from . import consumer
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..answer import Answer
from ..evaluate import evaluate
from ..model import BatchEvidence, Rate, RateThreshold
from ..rate_calculation import (
    apply_rate,
    convert_duration,
    convert_units,
    rate_operands,
)
from ..reference_identity import reference_from_unit


@consumer("threshold-block-total")
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    bases = [r for r in rows if r.kind == "tariff-base"]
    usages = [r for r in rows if r.kind == "tariff-usage"]
    rates = list(ctx.store.by_kind(Rate))
    thresholds = list(ctx.store.by_kind(RateThreshold))
    if (
        len(bases) != 1
        or len(usages) != 1
        or len(rows) != 2
        or len(rates) != 1
        or len(thresholds) != 1
    ):
        return decline("one fixed block, excess rate and observed usage are required")
    base, usage, rate, threshold = bases[0], usages[0], rates[0], thresholds[0]
    actor = reference_from_unit(ctx.match.slots["owner"])
    if (
        base.entity_ref != actor
        or usage.entity_ref != actor
        or threshold.entity != actor.head
        or rate.entity != actor.head
        or base.container != usage.container
        or threshold.activity != base.container
        or base.marker != threshold.period
        or usage.marker != threshold.period
        or base.verb != rate.verb
        or usage.provenance.sentence <= base.provenance.sentence
        or threshold.provenance.sentence != base.provenance.sentence
        or rate.provenance.sentence != base.provenance.sentence
        or any(
            not isfinite(v) or v < 0
            for v in (base.value, usage.value, threshold.value, rate.value)
        )
    ):
        return decline(
            "the block, rate and usage must identify the same participant, activity and period"
        )
    actual = convert_duration(
        usage.value,
        usage.measure,
        threshold.unit,
        ctx.reg,
        ctx.log,
        source="threshold-usage-unit",
    )
    if actual is None or actual < threshold.value:
        return decline("usage below the fixed block needs an explicit prorating policy")
    excess = evaluate(
        "usage - included",
        dict(usage=actual, included=threshold.value),
        ctx.log,
        source="threshold-excess",
    )
    elapsed = convert_duration(
        excess,
        threshold.unit,
        rate.per,
        ctx.reg,
        ctx.log,
        source="threshold-excess-unit",
    )
    if elapsed is None:
        return decline("the threshold and excess rate need compatible duration units")
    premium = apply_rate(rate, elapsed, ctx.log, source="explicit-excess-charge")
    premium = convert_units(
        premium,
        rate.measure,
        base.measure,
        ctx.reg,
        ctx.log,
        source="threshold-currency",
    )
    if premium is None:
        return decline("the fixed block and excess rate need compatible currencies")
    facts = rows + rates + thresholds
    operands = [
        (base, [base.value]),
        (usage, [usage.value]),
        (rate, rate_operands(rate)),
        (threshold, [threshold.value]),
    ]
    if not closed_evidence(ctx, facts, operands):
        return decline(
            "every amount, rate, threshold and period condition must be accounted for"
        )
    ctx.log.consumed_rate_structure_keys.add(threshold.key())
    value = evaluate(
        "fixed + excess",
        dict(fixed=base.value, excess=premium),
        ctx.log,
        source="fixed-block-plus-excess",
    )
    return finish_batch_answer(
        ctx,
        facts,
        value,
        "fixed block plus the explicitly priced usage above its threshold",
    )
