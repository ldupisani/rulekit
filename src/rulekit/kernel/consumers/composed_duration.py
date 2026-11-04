"""Explicit schedules and exhaustive successive rate segments.

Both calculations audit source operands and complete language coverage before
using the shared arithmetic and unit-conversion machinery.
"""
from math import isfinite

from . import consumer
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..answer import Answer
from ..evaluate import evaluate
from ..model import BatchEvidence, Rate
from ..predicate_compatibility import predicates_compatible
from ..rate_calculation import apply_rate, convert_duration, rate_operands


@consumer('scheduled-activity-duration')
def scheduled(ctx):
    durations = ctx.store.by_kind(BatchEvidence)
    rates = list(ctx.store.by_kind(Rate))
    rows = [*durations, *rates]
    if len(durations) > 1 or any(r.kind != 'activity-duration' for r in durations):
        return Answer('decline', None, 'one explicit activity schedule is required')
    operands = [(r, rate_operands(r)) for r in rates]
    operands += [(r, [r.value, r.fraction]) for r in durations]
    if (not rows or not closed_evidence(ctx, rows, operands, additional_kinds=('attributive_count',))
            or any(r.entity != ctx.query['entity'] or not predicates_compatible(
                r.verb, ctx.query['verb'], r.measure, ctx.reg) for r in rows)):
        return Answer('decline', None, 'all stated rates must belong to the requested activity and participant')
    if durations:
        duration = durations[0]
        value = evaluate('base * (1 + factor)',
                         dict(base=duration.value, factor=duration.fraction),
                         ctx.log, source='scheduled-activity-duration')
        unit, period = duration.measure, duration.marker
    else:
        roots = [r for r in rates if not any(other.per == r.measure for other in rates)]
        if len(roots) != 1:
            return Answer('decline', None, 'the schedule needs a unique starting duration rate')
        root = roots[0]
        value = apply_rate(root, 1, ctx.log, source='scheduled-duration-rate')
        unit, period = root.measure, root.per
        rates.remove(root)
    while rates:
        following = [r for r in rates if r.measure == period]
        if len(following) != 1:
            return Answer('decline', None, 'cadences must form one complete chain')
        rate = following[0]
        maximum = ctx.reg.conversions.get((rate.per, rate.measure))
        if (rate.value <= 0 or not float(rate.value).is_integer()
                or maximum is not None and rate.value > maximum):
            return Answer('decline', None, 'active periods must fit their enclosing period')
        value = apply_rate(rate, value, ctx.log, source='scheduled-active-cadence')
        period = rate.per
        rates.remove(rate)
    if period != ctx.query['span']:
        return Answer('decline', None, 'the stated schedule does not reach the requested horizon')
    value = evaluate('duration * span', dict(duration=value, span=float(ctx.query['span_value'])),
                     ctx.log, source='scheduled-duration-horizon')
    value = convert_duration(value, unit, ctx.query['measure'], ctx.reg, ctx.log,
                             source='scheduled-duration-units')
    return finish_batch_answer(ctx, rows, value, 'compose the explicit duration rates and requested horizon')


@consumer('bounded-process-duration')
def bounded(ctx):
    rows = ctx.store.by_kind(BatchEvidence)
    if len(rows) != 1 or rows[0].kind != 'bounded-process':
        return Answer('decline', None, 'one exhaustive process partition is required')
    row = rows[0]
    if (row.verb != ctx.query['verb'] or row.per_member <= 0 or row.content_count <= 0
            or row.subtotal > row.value
            or not closed_evidence(ctx, rows, [(row, [row.value, row.per_member, row.subtotal, row.content_count])])):
        return Answer('decline', None, 'positive rates must cover the stated extent without gaps or overlaps')
    value = evaluate('first / rate1 + (total - first) / rate2',
                     dict(first=row.subtotal, rate1=row.per_member,
                          total=row.value, rate2=row.content_count),
                     ctx.log, source='successive-process-duration')
    value = convert_duration(value, row.container, ctx.query['measure'], ctx.reg, ctx.log,
                             source='process-duration-units')
    return finish_batch_answer(ctx, rows, value, 'add the elapsed times of the initial segment and exhaustive remainder')
