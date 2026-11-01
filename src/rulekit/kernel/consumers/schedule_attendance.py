"""Total attendance across explicitly separate participant event schedules."""
from collections import Counter, defaultdict
from math import isfinite

from . import consumer
from ..answer import Answer
from ..evaluate import evaluate
from ..model import BatchEvidence
from ..numeric_evidence import audit_numeric_mentions
from ..rate_calculation import convert_duration
from ..reference_bindings import anaphoric_forms_agree
from ..reference_identity import reference_from_unit
from ..source_coverage import uncovered_document_units


@consumer('schedule-attendance-duration')
def consume(ctx):
    def decline(reason):
        return Answer('decline', None, reason)
    rows = list(ctx.store.by_kind(BatchEvidence))
    kinds = ('scheduled-participants', 'scheduled-event-count', 'event-preparation-duration', 'scheduled-event-duration')
    if (len(rows) != 4 or len(ctx.store.facts) != 4 or ctx.store.collisions or ctx.store.quarantined
            or any(sum(row.kind == kind for row in rows) != 1 for kind in kinds)):
        return decline('one complete separate-participant schedule and both event durations are required')
    participants, events, preparation, duration = (next(row for row in rows if row.kind == kind) for kind in kinds)
    requested = reference_from_unit(ctx.match.slots['participants'])
    if (participants.entity != ctx.query['entity'] or participants.container_ref != requested
            or participants.verb != ctx.query['perform'] or preparation.verb != ctx.query['prepare']
            or participants.marker != preparation.entity
            or preparation.attribute and preparation.attribute != participants.verb
            or events.measure != preparation.container or events.measure != duration.entity
            or events.provenance.sentence != participants.provenance.sentence + 1
            or not events.provenance.sentence < preparation.provenance.sentence < duration.provenance.sentence
            or any(row.provenance.assumption for row in (participants, events, preparation))
            or duration.provenance.assumption and duration.provenance.sentence != ctx.question.sentence_index - 1
            or any(not isfinite(row.value) or row.value < 0 for row in rows)
            or not float(participants.value).is_integer() or participants.value < 1
            or not float(events.value).is_integer()
            or not anaphoric_forms_agree([events.acquisition], 'plural', ctx.reg)
            or preparation.acquisition and not anaphoric_forms_agree([preparation.acquisition], 'plural', ctx.reg)):
        return decline('participants, separate groups, activities and event references must identify the same schedule')
    expected = defaultdict(Counter)
    for row in rows:
        expected[row.provenance.sentence][row.value] += 1
    if (uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises, ctx.question), expected, missing='missing', duplicate='duplicate')):
        return decline('every participant count, duration and schedule condition must be read')
    first = convert_duration(preparation.value, preparation.measure, ctx.query['measure'], ctx.reg, ctx.log,
                              source='preparation-duration-unit')
    second = convert_duration(duration.value, duration.measure, ctx.query['measure'], ctx.reg, ctx.log,
                               source='event-duration-unit')
    if first is None or second is None:
        return decline('both durations must use compatible requested time units')
    value = evaluate('participants * events * (preparation + duration)',
                     dict(participants=participants.value, events=events.value, preparation=first, duration=second),
                     ctx.log, source='separate-schedule-attendance')
    ctx.log.consumed_batch_keys.update(row.key() for row in rows)
    return Answer('number', value, 'sum the event and preparation durations across the explicitly separate participant schedules')
