"""Reconstruct opening stock or a completed-activity counter in one period."""

from math import isfinite

from . import consumer
from ..answer import Answer, AnswerAssumption
from ..model import ActivityAccountEvidence, Rate
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..reference_identity import reference_from_unit
from ..reference_bindings import referenced_forms_agree
from ..rate_query import rate_subject_reference
from ..rate_calculation import apply_rate, convert_units, rate_operands
from ..reporting_periods import reporting_period, reporting_duration, period_annotation
from ..evaluate import evaluate
from ..resource_equations import resource_residual
from ..source_coverage import covered_temporal_annotation

KINDS = {
    "activity-account-context",
    "activity-account-duration",
    "activity-account-removal",
    "activity-account-closing",
}


@consumer(
    "activity-account-opening",
    applicable=lambda s: any(
        r.kind in KINDS for r in s.by_kind(ActivityAccountEvidence)
    ),
)
def consume(ctx):
    def fail(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(ActivityAccountEvidence))
    rates = list(ctx.store.by_kind(Rate))
    contexts = [r for r in rows if r.kind == "activity-account-context"]
    spans = [r for r in rows if r.kind == "activity-account-duration"]
    removals = [r for r in rows if r.kind == "activity-account-removal"]
    closings = [r for r in rows if r.kind == "activity-account-closing"]
    if (
        len(contexts) != 1
        or len(closings) != 1
        or len(rates) != 1
        or not spans
        or any(r.kind not in KINDS for r in rows)
    ):
        return fail(
            "one account, applicable rate, complete intervals and closing count are required"
        )
    context, closing, rate = contexts[0], closings[0], rates[0]
    window = reporting_period(context.reporting_period_ref, ctx.reg)
    requested = reporting_period(
        reference_from_unit(ctx.match.slots["period"]), ctx.reg
    )
    observed = reporting_period(closing.reporting_period_ref, ctx.reg)
    if window is None or window.offset > 0 or requested != window or observed != window:
        return fail(
            "the context, closing observation and question need the same established reporting period"
        )
    if context.prior_period:
        prior = reporting_period(context.prior_period_ref, ctx.reg)
        if prior is None or not prior.precedes(window):
            return fail(
                "the earlier period must precede this reporting period at the same grain; dates are needed across grains"
            )
    for row in spans + removals:
        if (
            row.reporting_period
            and reporting_period(row.reporting_period_ref, ctx.reg) != window
        ):
            return fail(
                "every stated interval and adjustment must belong to the reporting period"
            )
    actor = reference_from_unit(ctx.match.slots["who"])
    progress = bool(ctx.query.get("activity"))
    if (
        not actor.resolved
        or context.entity_ref != actor
        or rate_subject_reference(rate, ctx.premises, ctx.reg) != actor
        or closing.measure != rate.measure
        or ctx.query["measure"] != rate.measure
        or context.container_ref is None
        or not context.container_ref.resolved
        or any(r.entity_ref != actor for r in spans + removals)
        or not referenced_forms_agree((*ctx.premises, ctx.question), actor, ctx.reg)
        or any(r.provenance.assumption for r in rows)
        or rate.provenance.assumption
        or context.verb
        and context.verb != rate.verb
    ):
        return fail("the actor, account, quantity and activity must agree throughout")
    if (
        progress
        and (
            closing.entity_ref != actor
            or closing.verb != rate.verb
            or ctx.query["activity"] != rate.verb
        )
        or not progress
        and (closing.entity_ref != context.container_ref or closing.verb)
    ):
        return fail("completed work and physical stock are different counters")
    if progress:
        effect = 1
        if removals:
            return fail(
                "physical removals do not undo completed work; a counter adjustment must be explicit"
            )
    else:
        effect = ctx.reg.attribute_value(rate.verb, "account_stock_effect")
        if effect not in {-1, 1}:
            return fail(
                "this activity does not establish a change in physical stock; ask for completed work explicitly"
            )
    if (
        not isfinite(rate.value)
        or rate.value < 0
        or not isfinite(closing.value)
        or closing.value < 0
        or not float(closing.value).is_integer()
    ):
        return fail(
            "a counted account needs a nonnegative rate and whole closing count"
        )
    order = lambda r: (r.provenance.sentence, r.position)
    if any(not order(context) < order(r) < order(closing) for r in spans + removals):
        return fail(
            "all reported intervals and adjustments must precede the closing observation"
        )
    operands = [
        (context, []),
        (closing, [closing.value]),
        (rate, list(rate_operands(rate))),
    ]
    elapsed = []
    amounts = []
    corrections = []
    assumptions = []
    for row in spans:
        if row.verb != rate.verb or not isfinite(row.value) or row.value < 0:
            return fail("each interval must use the same stated activity rate")
        duration = reporting_duration(
            row.value,
            row.measure,
            rate.per,
            ctx.reg,
            ctx.log,
            source="account-activity-duration",
        )
        if duration is None:
            return fail(
                "the elapsed time and rate denominator need an exact declared conversion"
            )
        amount = apply_rate(rate, duration, ctx.log, source="account-activity-amount")
        if not isfinite(amount) or amount < 0 or not float(amount).is_integer():
            return fail(
                "each observed activity interval must account for whole counted units"
            )
        elapsed.append(duration)
        amounts.append(amount)
        operands.append((row, [row.value]))
        if row.marker == "additional-duration":
            assumptions.append(
                AnswerAssumption(
                    "additional-activity-duration",
                    "The continuation duration is additional work time, not a comparison with the previous session.",
                    (row.provenance.sentence,),
                )
            )
    budget = reporting_duration(
        1, window.unit, rate.per, ctx.reg, ctx.log, source="account-reporting-window"
    )
    if budget is not None and sum(elapsed) > budget + 1e-9:
        return fail("the reported working intervals exceed the reporting window")
    for row in removals:
        amount = convert_units(
            row.value,
            row.measure,
            rate.measure,
            ctx.reg,
            ctx.log,
            source="account-correction-unit",
        )
        if amount is None or amount < 0 or not float(amount).is_integer():
            return fail("adjustments must remove whole units of the same resource")
        if row.attribute and row.attribute != rate.verb:
            return fail("the correction refers to another activity")
        if row.marker == "required-correction":
            if effect != 1:
                return fail(
                    "correcting a depletion needs an explicit adjustment direction"
                )
            assumptions.append(
                AnswerAssumption(
                    "required-correction-completed",
                    "The required correction was carried out before the closing count.",
                    (row.provenance.sentence,),
                )
            )
        corrections.append(amount)
        operands.append((row, [row.value]))
    incoming = amounts if effect == 1 else []
    outgoing = amounts if effect == -1 else []
    value = resource_residual(
        [closing.value, *corrections, *outgoing],
        incoming,
        ctx.log,
        source="reconstruct-opening-account",
    )
    if value < 0 or not float(value).is_integer():
        return fail("the opening count must be a nonnegative whole number")
    changes = [(row, effect * v) for row, v in zip(spans, amounts)]
    changes.extend((row, -v) for row, v in zip(removals, corrections))
    balance = value
    for row, change in sorted(changes, key=lambda pair: order(pair[0])):
        balance = evaluate(
            "balance + change",
            dict(balance=balance, change=change),
            ctx.log,
            source="account-activity-occurrence",
        )
        if balance < 0:
            return fail("an adjustment cannot remove units that do not yet exist")
    annotations = []
    for row in rows:
        if row.reporting_period_ref:
            annotations.append(
                (
                    row.entity,
                    {
                        (
                            row.provenance.sentence,
                            period_annotation(row.reporting_period_ref),
                        )
                    },
                )
            )
        if row.prior_period_ref:
            annotations.append(
                (
                    row.entity,
                    {
                        (
                            row.provenance.sentence,
                            period_annotation(row.prior_period_ref),
                        )
                    },
                )
            )
    metadata = [f for f in ctx.store.facts if f not in rows and f not in rates]
    if any(
        not any(
            covered_temporal_annotation(f, ctx.premises, entity, periods)
            for entity, periods in annotations
        )
        for f in metadata
    ):
        return fail("an additional event lies outside this activity account")
    if not closed_evidence(ctx, [*rows, *rates, *metadata], operands):
        return fail("every interval, rate, adjustment and condition must be read")
    ctx.log.consumed_rate_keys.add((rate.entity, rate.measure))
    assumptions.append(
        AnswerAssumption(
            "constant-stated-output-rate",
            "The stated activity rate applies throughout the reported intervals.",
            (rate.provenance.sentence,),
        )
    )
    return finish_batch_answer(
        ctx,
        rows,
        value,
        "opening count = closing count − increases + decreases in the same reporting period",
        assumptions=assumptions,
    )
