"""Shared rate arithmetic and activity identity, without vocabulary defaults."""

from .dimensions import conversion_factor
from .evaluate import evaluate
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class _Ratio:
    numerator: float
    denominator: float


def apply_ratio(numerator, denominator, amount, log, *, source):
    """Apply an explicit input/output ratio without losing its raw operands.

    The caller validates resource identities, unit conversion, scope and the
    permission to reuse a ratio. This operation supplies only the arithmetic.
    """
    if (not all(isfinite(v) for v in (numerator, denominator, amount))
            or numerator < 0 or denominator <= 0 or amount < 0):
        return None
    return apply_rate(_Ratio(numerator, denominator), amount, log, source=source)


def convert_calendar_duration(value, source_unit, target_unit, reg, log, *, source):
    """Convert counts of calendar units without assigning months a day length."""
    before = reg.attribute_value(source_unit, 'calendar_months')
    after = reg.attribute_value(target_unit, 'calendar_months')
    if before is not None and after is not None:
        return evaluate('value * before / after', dict(value=value, before=before, after=after),
                        log, source=source)
    return convert_duration(value, source_unit, target_unit, reg, log, source=source)


def convert_exact_duration(value, unit, target, reg, log, *, source):
    """Use exact calendar or fixed-duration conversions, including unit chains."""
    result = convert_calendar_duration(value, unit, target, reg, log, source=source)
    if result is not None:
        return result
    factor = conversion_factor(reg, unit, target, category="duration_measure")
    if factor is None:
        return None
    return evaluate(
        "value * factor", dict(value=value, factor=factor), log, source=source
    )


def rate_operands(rate):
    # Scalar per-occurrence costs and frequencies share the same arithmetic
    # protocol; only explicitly compound rates carry raw ratio operands.
    return ((rate.numerator, rate.denominator) if getattr(rate, "numerator", None) is not None
            and getattr(rate, "denominator", None) is not None else (rate.value,))


def apply_rate(rate, amount, log, *, source, inverse=False):
    """Keep source numerator/denominator visible in either direction."""
    if len(rate_operands(rate)) == 2:
        expression = (f"{amount} * {rate.denominator} / {rate.numerator}" if inverse
                      else f"{rate.numerator} * {amount} / {rate.denominator}")
    else:
        expression = f"{amount} / {rate.value}" if inverse else f"{rate.value} * {amount}"
    return evaluate(expression, {}, log, source=source)


def convert_units(value, unit, target, reg, log, *, source, allow_cadence=False, record=True):
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


def convert_duration(value, unit, target, reg, log, *, source, allow_cadence=False, record=True):
    return convert_units(value, unit, target, reg, log, source=source,
                         allow_cadence=allow_cadence, record=record)


def activity_scope_matches(scope, rate, participant, activity):
    return (scope.participant == rate.entity == participant
            and scope.verb == rate.verb and scope.activity == activity)
