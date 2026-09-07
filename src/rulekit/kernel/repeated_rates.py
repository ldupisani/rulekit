"""Compose repeated durations with a base rate and an optional excess tier.

No rates or thresholds are defaults. The daily-session convention is an
explicit category-owned interpretation reported in the answer, never a time
conversion (a session does not universally equal a day).
"""

from collections import Counter
from math import isfinite

from .answer import Answer
from .evaluate import evaluate
from .model import Rate, RateThreshold, RatePremium, RepeatedActivityDuration, RateScope
from .numeric_evidence import numeric_mentions
from .rate_calculation import activity_scope_matches, apply_rate, convert_duration, rate_operands


RATE_STRUCTURE_KINDS = (RateThreshold, RatePremium, RepeatedActivityDuration)


def has_rate_structure(store):
    return any(store.by_kind(kind) for kind in RATE_STRUCTURE_KINDS)


def repeated_rate_total(ctx, rate: Rate):
    """Return None only when no structured rate evidence is present."""
    if not has_rate_structure(ctx.store):
        return None

    def decline(reason):
        return Answer("decline", None, reason)

    if any(ctx.query.get(field) for field in (
        "other_entity", "entity_owner", "entity_qualifier", "measure_qualifier",
    )):
        return decline("a qualified or multi-participant ask needs explicitly matching rate evidence")
    requested = ctx.query.get("req_unit")
    if requested and ctx.reg.plural_to_singular.get(requested, requested) != rate.measure:
        return decline("the requested currency does not match the stated rate")
    schedules = ctx.store.by_kind(RepeatedActivityDuration)
    thresholds = ctx.store.by_kind(RateThreshold)
    premiums = ctx.store.by_kind(RatePremium)
    if len(schedules) != 1 or len(thresholds) > 1 or len(premiums) > 1:
        return decline("a repeated rate needs one schedule and at most one complete tier")
    schedule = schedules[0]
    if schedule.entity != rate.entity or not ctx.reg.word_in_category(rate.verb, "wage_verb"):
        return decline("the rate and scheduled activity must belong to the same participant")
    scopes = ctx.store.by_kind(RateScope)
    if scopes and (len(scopes) != 1 or not activity_scope_matches(
        scopes[0], rate, schedule.entity, schedule.activity
    )):
        return decline("an activity-qualified wage needs a matching explicit activity duration")
    if "span_unit" in ctx.query:
        return decline("an additional asked span cannot replace the stated repeated schedule")
    if bool(thresholds) != bool(premiums):
        return decline("a threshold and its premium must both be stated")
    if len(ctx.store.by_kind(Rate)) != 1:
        return decline("a repeated rate needs one unambiguous base rate")
    if any(not isinstance(f, (*RATE_STRUCTURE_KINDS, Rate, RateScope)) for f in ctx.store.facts):
        return decline("additional facts are not explained by this rate and schedule")
    values = (rate.value, schedule.elapsed, schedule.value)
    if not all(isfinite(v) and v >= 0 for v in values) or not float(schedule.value).is_integer():
        return decline("rate, elapsed duration, and integral repetitions must be nonnegative")
    if schedule.value < 1:
        return decline("the schedule needs at least one complete repetition")
    if ((rate.numerator is None) != (rate.denominator is None)
            or (rate.denominator is not None and (not isfinite(rate.denominator) or rate.denominator <= 0))
            or not all(isfinite(v) and v >= 0 for v in rate_operands(rate))):
        return decline("a compound rate needs a nonnegative numerator and positive denominator")

    def convert(value, unit):
        return convert_duration(value, unit, rate.per, ctx.reg, ctx.log, source="repeated-rate-unit")

    duration = convert(schedule.elapsed, schedule.unit)
    if duration is None:
        return decline("the activity duration cannot be converted to the base rate unit")
    boundary, premium_fraction = duration, 0.0
    assumption = ""
    if thresholds:
        threshold, premium = thresholds[0], premiums[0]
        if (threshold.entity != rate.entity or threshold.activity != schedule.activity
                or threshold.tier != premium.tier
                or threshold.provenance.sentence != premium.provenance.sentence):
            return decline("the excess tier must be defined by this participant's policy")
        if not ctx.reg.attribute_applies_to(premium.descriptor, rate.per):
            return decline("the premium's rate unit does not match the base rate")
        if not all(isfinite(v) and v >= 0 for v in (threshold.value, premium.fraction)):
            return decline("the threshold and additive premium must be nonnegative")
        boundary = convert(threshold.value, threshold.unit)
        if boundary is None:
            return decline("the threshold cannot be converted to the base rate unit")
        if threshold.period != schedule.period:
            if not (ctx.reg.word_in_category(threshold.period, "activity_session_unit")
                    and ctx.reg.word_in_category(schedule.period, "session_recurrence_period")):
                return decline("the threshold resets on a different period from the schedule")
            assumption = f"; treating each {schedule.period}'s activity as one {threshold.period}"
        premium_fraction = premium.fraction

    # Audit the exact stated numeric multiset, sentence by sentence. A second
    # amount equal to an operand is still a second, unsupported statement.
    expected = {}
    def expect(fact, *amounts):
        expected.setdefault(fact.provenance.sentence, Counter()).update(float(v) for v in amounts)
    expect(rate, *rate_operands(rate))
    expect(schedule, schedule.elapsed, schedule.value)
    for threshold in thresholds:
        expect(threshold, threshold.value)
    for premium in premiums:
        expect(premium, premium.fraction)
    from .learn import simple_rate_evidence_units
    for reading in (*ctx.premises, ctx.question):
        actual = numeric_mentions(reading)
        if actual != expected.get(reading.sentence_index, Counter()):
            return decline("the repeated rate does not account for every stated numeric amount")
        if reading is not ctx.question and reading.sentence_index not in expected:
            return decline("an additional premise lies outside the rate and schedule")
        if reading is ctx.question:
            covered = ctx.match.consumed
        elif reading.sentence_index == rate.provenance.sentence:
            covered = simple_rate_evidence_units(reading, rate, ctx.reg)
        else:
            covered = frozenset()
        # A local match must not discard another condition, exception, or
        # complement in the rate, policy, schedule, or question itself.
        if any(u.uid not in covered and not u.features.get("pattern_consumed")
               and u.sense() not in {"article", "punct"} for u in reading.units):
            return decline("the rate, schedule, or ask has an unread condition or complement")

    regular = min(duration, boundary)
    excess = max(duration - boundary, 0.0)
    regular_amount = apply_rate(rate, regular, ctx.log, source="repeated-rate-base")
    excess_amount = apply_rate(rate, excess, ctx.log, source="repeated-rate-base")
    regular_pay = evaluate(f"{regular_amount} * {schedule.value}", {}, ctx.log,
                           source="repeated-rate-regular")
    excess_pay = evaluate(
        f"{excess_amount} * (1 + {premium_fraction}) * {schedule.value}",
        {}, ctx.log, source="repeated-rate-excess",
    )
    total = evaluate(f"{regular_pay} + {excess_pay}", {}, ctx.log, source="repeated-rate-total")
    ctx.log.consumed_rate_structure_keys.update(
        f.key() for kind in RATE_STRUCTURE_KINDS for f in ctx.store.by_kind(kind)
    )
    return Answer("number", total,
                  f"{regular_pay:g} regular + {excess_pay:g} excess-rate pay over "
                  f"{schedule.value:g} {schedule.period} periods{assumption}")
