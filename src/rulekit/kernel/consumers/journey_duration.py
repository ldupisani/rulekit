"""Sum explicit return-journey schedules, preserving modes and routes."""

from collections import Counter, defaultdict
from math import isfinite

from . import consumer
from ..model import JourneyLeg, JourneySchedule
from ..source_coverage import uncovered_document_units
from ..numeric_evidence import audit_numeric_mentions
from ..rate_calculation import apply_rate, convert_duration
from ..resource_equations import resource_residual


@consumer("journey-duration")
def consume(ctx):
    from ..answer import Answer, AnswerAssumption, AnswerProof, ProofStep, SemanticNode

    def decline(reason):
        return Answer("decline", None, reason)

    legs = list(ctx.store.by_kind(JourneyLeg))
    schedules = list(ctx.store.by_kind(JourneySchedule))
    modes = {ctx.query["first_mode"], ctx.query["second_mode"]}
    if len(modes) != 2 or len(legs) != len(schedules) or len(schedules) != len(modes):
        return decline("each requested mode needs one one-way duration and one return schedule")
    if ({f.mode for f in legs} != modes or {f.mode for f in schedules} != modes
            or any(f.entity != ctx.query["entity"] or f.destination != ctx.query["destination"]
                   or f.provenance.assumption for f in (*legs, *schedules))):
        return decline("journeys must identify the same participant, destination and requested modes")
    if any(not isfinite(f.value) or f.value <= 0 for f in (*legs, *schedules)):
        return decline("journey durations and frequencies must be positive")
    if any(s.legs != 2 or not float(s.value).is_integer()
           or s.period != ctx.query["period"] for s in schedules):
        return decline("the return counts must be whole and explicitly cover the requested period")
    expected = defaultdict(Counter)
    for fact in (*legs, *schedules):
        expected[fact.provenance.sentence][fact.value] += 1
    if uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed):
        return decline("a journey has an unread route, event, or condition")
    error = audit_numeric_mentions((*ctx.premises, ctx.question), expected,
                                   missing="a stated amount lies outside the journey schedules",
                                   duplicate="journey evidence repeats a source amount")
    if error:
        return decline(error)
    totals = []
    details = []
    for schedule in schedules:
        leg = next(f for f in legs if f.mode == schedule.mode)
        if not ctx.reg.word_in_category(leg.unit, "duration_measure"):
            return decline("a one-way journey needs a duration unit")
        occurrences = apply_rate(schedule, schedule.legs, ctx.log, source="journey-directions")
        elapsed = apply_rate(leg, occurrences, ctx.log, source="repeated-journey-duration")
        converted = convert_duration(elapsed, leg.unit, ctx.query["unit"], ctx.reg, ctx.log,
                                     source="journey-duration-unit")
        if converted is None:
            return decline("the journey duration cannot be converted to the asked unit")
        totals.append(converted)
        details.append(f"{schedule.mode}: {occurrences:g} one-way legs, {converted:g} {ctx.query['unit']}")
    total = resource_residual(totals, [], ctx.log, source="combined-journey-duration")
    ctx.log.consumed_journey_keys.update(f.key() for f in (*legs, *schedules))
    detail = "; ".join(details) + ". Uses each stated one-way duration for both legs of its explicit return trip."
    node = SemanticNode("journey-duration", (("entity", ctx.query["entity"]),
                         ("destination", ctx.query["destination"]), ("period", ctx.query["period"]),
                         ("unit", ctx.query["unit"])))
    return Answer("number", total, detail, proof=AnswerProof(node, (
        ProofStep("mode-scoped-return-schedules", node, tuple(legs + schedules), detail),)),
        assumptions=(AnswerAssumption("equal-return-leg-duration",
            "Each stated one-way duration applies to both legs of its return trip.",
            tuple(sorted({r.provenance.sentence for r in legs}))),))
