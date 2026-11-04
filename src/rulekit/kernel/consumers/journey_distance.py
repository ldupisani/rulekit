"""Repeat one-way distances, add complete journeys, then invert a rate."""

from collections import Counter, defaultdict
from math import isfinite

from . import consumer
from ..model import JourneyLeg, JourneySchedule, JourneyExtra, JourneyPace
from ..source_coverage import uncovered_document_units
from ..numeric_evidence import audit_numeric_mentions
from ..rate_calculation import apply_rate, convert_duration, convert_units
from ..resource_equations import resource_residual


@consumer("journey-distance-duration")
def consume(ctx):
    from ..answer import Answer, AnswerAssumption, AnswerProof, ProofStep, SemanticNode

    def decline(reason):
        return Answer("decline", None, reason)

    legs = list(ctx.store.by_kind(JourneyLeg))
    schedules = list(ctx.store.by_kind(JourneySchedule))
    extras = list(ctx.store.by_kind(JourneyExtra))
    rates = list(ctx.store.by_kind(JourneyPace))
    if len(legs) != 1 or len(schedules) != 1 or len(rates) != 1:
        return decline("travel time needs one exact route, one return schedule and one speed")
    leg, schedule, rate = legs[0], schedules[0], rates[0]
    entity, mode, period = ctx.query["entity"], ctx.query["mode"], ctx.query["period"]
    if (any(f.entity != entity or f.provenance.assumption for f in (*legs, *schedules, *extras))
            or leg.destination != schedule.destination or leg.mode not in ("", mode)
            or leg.destination_owner != entity
            or any(f.mode != mode or f.period != period for f in (schedule, *extras))
            or rate.entity != entity or rate.mode != mode
            or not rate.provenance.assumption):
        return decline("the route, schedule, extra journeys and assumed speed must share the asked scope")
    if (schedule.legs != 2 or not float(schedule.value).is_integer()
            or any(not isfinite(f.value) or f.value <= 0 for f in (leg, schedule, rate))
            or any(not isfinite(f.value) or f.value < 0 for f in extras)
            or not ctx.reg.word_in_category(rate.measure, "journey_distance_measure")
            or not ctx.reg.word_in_category(rate.per, "duration_measure")):
        return decline("travel needs positive distances, a positive speed and whole return counts")
    evidence = (*legs, *schedules, *extras, *rates)
    expected = defaultdict(Counter)
    for fact in evidence:
        expected[fact.provenance.sentence][fact.value] += 1
    if uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed):
        return decline("travel has an unread route, event, or condition")
    error = audit_numeric_mentions((*ctx.premises, ctx.question), expected,
                                   missing="a stated amount lies outside the travel calculation",
                                   duplicate="journey evidence repeats a source amount")
    if error:
        return decline(error)
    converted = []
    for distance in (leg, *extras):
        if not ctx.reg.word_in_category(distance.unit, "journey_distance_measure"):
            return decline("every route amount must be a distance")
        value = convert_units(distance.value, distance.unit, rate.measure, ctx.reg, ctx.log,
                              source="journey-distance-unit")
        if value is None:
            return decline("a journey distance cannot be converted to the speed's distance unit")
        converted.append(value)
    leg_count = apply_rate(schedule, schedule.legs, ctx.log, source="journey-directions")
    # A converted leg is not another fact or source number; log its
    # repetition separately from the raw quoted distance and frequency.
    from ..evaluate import evaluate
    commute = evaluate("distance * legs", {"distance": converted[0], "legs": leg_count},
                       ctx.log, source="scheduled-travel-distance")
    total_distance = resource_residual([commute, *converted[1:]], [], ctx.log,
                                      source="complete-travel-distance")
    elapsed = apply_rate(rate, total_distance, ctx.log, source="travel-speed-inverse", inverse=True)
    total = convert_duration(elapsed, rate.per, ctx.query["unit"], ctx.reg, ctx.log,
                             source="travel-time-unit")
    if total is None:
        return decline("the speed's time unit cannot reach the requested output unit")
    ctx.log.consumed_journey_keys.update(f.key() for f in evidence)
    detail = (f"{schedule.value:g} explicit return journeys ({leg_count:g} one-way legs), "
              f"plus {len(extras)} complete additional journeys: {total_distance:g} {rate.measure}. "
              f"At the assumed speed, {total:g} {ctx.query['unit']}. "
              "Uses the supplied working-day set as one weekly schedule and the stated route distance "
              "for both legs; no working-day count is inferred.")
    node = SemanticNode("journey-distance-duration", (("entity", entity), ("mode", mode),
                         ("period", period), ("unit", ctx.query["unit"])))
    return Answer("number", total, detail, proof=AnswerProof(node, (
        ProofStep("scoped-distance-schedule-rate", node, evidence, detail),)),
        assumptions=(
            AnswerAssumption("weekly-working-day-schedule",
                "The supplied working-day set describes one weekly schedule.",
                (schedule.provenance.sentence,)),
            AnswerAssumption("equal-return-leg-distance",
                "The stated route distance applies to both legs of each return trip.",
                (leg.provenance.sentence,)),
        ))
