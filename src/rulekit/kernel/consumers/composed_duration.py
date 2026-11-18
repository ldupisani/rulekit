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
from ..reference_bindings import anaphoric_forms_agree
from ..reference_identity import constrains


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
    if ctx.query.get('mode') == 'crew':
        return _crew_process_duration(ctx)
    rows = ctx.store.by_kind(BatchEvidence)
    processes = [row for row in rows if row.kind == 'bounded-process']
    interruptions = [row for row in rows if row.kind == 'process-interruption']
    if len(processes) != 1 or len(rows) != 1 + len(interruptions):
        return Answer('decline', None, 'one exhaustive process partition is required')
    if len(interruptions) > 1:
        return Answer('decline', None, 'multiple interruptions need evidence of distinct, nonoverlapping pauses')
    row = processes[0]
    operands = [(row, [row.value, row.per_member, row.subtotal, row.content_count])]
    operands.extend((pause, [pause.value]) for pause in interruptions)
    if (ctx.query.get('verb', row.verb) != row.verb or row.per_member <= 0 or row.content_count <= 0
            or row.subtotal > row.value
            or any(pause.provenance.assumption or pause.provenance.sentence <= row.provenance.sentence
                   or not ctx.reg.word_in_category(row.verb, 'transfer_process_verb')
                   or pause.entity != ctx.query.get('process', pause.entity)
                   for pause in interruptions)
            or not closed_evidence(ctx, rows, operands)):
        return Answer('decline', None, 'positive rates must cover the stated extent without gaps or overlaps')
    value = _successive_duration(ctx, row.value, row.subtotal, row.per_member, row.content_count)
    value = convert_duration(value, row.container, ctx.query['measure'], ctx.reg, ctx.log,
                             source='process-duration-units')
    if value is None:
        return Answer('decline', None, 'the requested unit must measure duration')
    reason = ctx.query_reference('reason')
    delays = []
    for pause in interruptions:
        attribution = pause.provenance.attribution
        if reason and (attribution is None or not attribution.reason_entities):
            return Answer('decline', None, 'all interruptions need an explicitly stated cause')
        if reason and not any(constrains(reason, ref) for ref in attribution.reason_entities):
            continue
        duration = convert_duration(pause.value, pause.measure, ctx.query['measure'], ctx.reg, ctx.log,
                                    source='process-interruption-units')
        if duration is None:
            return Answer('decline', None, 'each interruption needs a compatible duration unit')
        delays.append(duration)
    mode = ctx.query.get('mode')
    if mode == 'delay' and not delays:
        return Answer('decline', None, 'no interruption has the requested cause')
    if mode == 'delay':
        value = sum(delays)
    elif mode != 'active':
        value += sum(delays)
    return finish_batch_answer(ctx, rows, value, 'compose the measured progress segments and any requested interruption time')


def _successive_duration(ctx, total, first, rate1, rate2):
    return evaluate(
        'first / rate1 + (total - first) / rate2',
        dict(first=first, rate1=rate1, total=total, rate2=rate2),
        ctx.log, source='successive-process-duration',
    )


def _crew_process_duration(ctx):
    rows = list(ctx.store.by_kind(BatchEvidence))
    targets = [row for row in rows if row.kind == 'crew-process-target']
    expansions = [row for row in rows if row.kind == 'crew-process-expansion']
    if len(rows) != 2 or len(targets) != 1 or len(expansions) != 1:
        return Answer('decline', None, 'the process needs one stated target and one crew change')
    target, expansion = targets[0], expansions[0]
    process = ctx.query_reference('process')
    count = len(target.members)
    if (
        process is None or target.entity_ref is None or not constrains(process, target.entity_ref)
        or target.verb != ctx.query['verb']
        or count < 2 or len(set(target.members)) != count
        or not anaphoric_forms_agree([expansion.marker], 'plural', ctx.reg)
        or expansion.provenance.sentence <= target.provenance.sentence
        or any(row.provenance.assumption for row in rows)
        or not float(expansion.per_member).is_integer() or expansion.per_member <= 0
        or target.per_member <= 0 or target.value <= 0
        or not closed_evidence(
            ctx, rows, [(target, [target.value, target.per_member]), (expansion, [expansion.value, expansion.per_member])]
        )
    ):
        return Answer('decline', None, 'the rate and joining participants must describe the same complete process')
    span = convert_duration(expansion.value, expansion.measure, target.container, ctx.reg, ctx.log,
                            source='crew-phase-duration')
    if span is None or span <= 0:
        return Answer('decline', None, 'the crew change needs a compatible elapsed duration')
    opening_rate = target.per_member * count
    final_rate = target.per_member * (count + expansion.per_member)
    first = span * opening_rate
    if first >= target.value:
        return Answer('decline', None, 'the stated crew change must precede completion')
    value = _successive_duration(ctx, target.value, first, opening_rate, final_rate)
    value = convert_duration(value, target.container, ctx.query['measure'], ctx.reg, ctx.log,
                             source='crew-completion-units')
    return finish_batch_answer(ctx, rows, value, 'apply the individual rate to the crew in each phase')
