"""Shared rate arithmetic and activity identity, without vocabulary defaults."""

from .evaluate import evaluate


def rate_operands(rate):
    return ((rate.numerator, rate.denominator) if rate.numerator is not None
            and rate.denominator is not None else (rate.value,))


def apply_rate(rate, amount, log, *, source, inverse=False):
    """Keep source numerator/denominator visible in either direction."""
    if len(rate_operands(rate)) == 2:
        expression = (f"{amount} * {rate.denominator} / {rate.numerator}" if inverse
                      else f"{rate.numerator} * {amount} / {rate.denominator}")
    else:
        expression = f"{amount} / {rate.value}" if inverse else f"{rate.value} * {amount}"
    return evaluate(expression, {}, log, source=source)


def convert_duration(value, unit, target, reg, log, *, source, allow_cadence=False, record=True):
    if unit == target:
        return value
    factor = reg.conversions.get((unit, target))
    if factor is None and allow_cadence:
        factor = reg.cadence_conversions.get((unit, target))
    if factor is None:
        return None
    if not record:
        return value * factor
    return evaluate(f"{value} * {factor}", {}, log, source=source)


def activity_scope_matches(scope, rate, participant, activity):
    return (scope.participant == rate.entity == participant
            and scope.verb == rate.verb and scope.activity == activity)
