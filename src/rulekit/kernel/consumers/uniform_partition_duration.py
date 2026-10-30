"""Project duration from one equal part and an explicit unchanged-rate policy."""

from collections import Counter, defaultdict
from dataclasses import replace
from math import isfinite

from . import consumer
from .indexed_path import ordinal_index
from ..answer import Answer, AnswerProof, ProofStep, SemanticNode
from ..dimensions import conversion_factor
from ..evaluate import evaluate
from ..model import BatchEvidence, Rate
from ..numeric_evidence import audit_numeric_mentions
from ..rate_calculation import apply_rate
from ..reference_identity import constrains, reference_from_unit
from ..source_coverage import uncovered_document_units


@consumer('uniform-partition-duration', applicable=lambda s: any(
    r.kind == 'process-population'
    for r in s.by_kind(BatchEvidence)))
def consume(ctx):
    def decline(reason, proof=None):
        return Answer('decline', None, reason, proof=proof)

    rows = list(ctx.store.by_kind(BatchEvidence))
    populations = [r for r in rows if r.kind == 'process-population']
    observations = [r for r in rows if r.kind == 'process-part-duration']
    continuations = [r for r in rows if r.kind == 'uniform-rate-continuation']
    if len(populations) != 1 or len(observations) != 1:
        return decline('a projection needs one partition and one observed part duration')
    if len(continuations) != 1:
        return decline('one timed part does not establish a constant rate for the remaining parts')
    if (len(rows) != 3 or len(ctx.store.facts) != 3
            or ctx.store.collisions or ctx.store.quarantined):
        return decline('every condition must belong to one observed part and its explicit continuation')
    population, observed, continuation = populations[0], observations[0], continuations[0]
    count = ordinal_index(population.value, ctx.reg)
    scope = ctx.query.get('scope')
    whole = population.container_ref
    asked = reference_from_unit(ctx.match.slots['whole'])
    if scope == 'whole':
        asked = replace(asked, qualifiers=tuple(
            q for q in asked.qualifiers
            if not ctx.reg.word_in_category(q, 'complete_extent_attribute')))
    if (count is None or count < 2 or ordinal_index(observed.marker, ctx.reg) != 1
            or not isfinite(observed.value) or observed.value <= 0
            or scope not in {'whole', 'remaining'}
            or population.provenance.assumption or observed.provenance.assumption
            or not population.provenance.sentence < observed.provenance.sentence < continuation.provenance.sentence
            or continuation.provenance.assumption
            and continuation.provenance.sentence != ctx.question.sentence_index - 1):
        return decline('the first part must be timed before a scoped continuation over the remaining parts')
    if (whole is None or not whole.resolved or not constrains(asked, whole)
            or observed.attribute != population.measure
            or observed.entity != population.entity or continuation.entity != population.entity
            or ctx.query.get('entity') not in ('', None, population.entity)
            or observed.container_ref is not None and not constrains(observed.container_ref, whole)
            or continuation.container_ref is None or not constrains(continuation.container_ref, whole)
            or population.verb and population.verb != continuation.verb
            or not population.verb and observed.verb != continuation.verb
            or ctx.query['verb'] != continuation.verb):
        return decline('the participant, whole, component and activity must refer to the same partition')
    expected = defaultdict(Counter)
    expected[population.provenance.sentence][population.value] += 1
    expected[observed.provenance.sentence][observed.value] += 1
    if (uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises, ctx.question), expected,
                                      missing='an amount is outside the projection',
                                      duplicate='the projection repeats an observed amount')):
        return decline('every stated condition and measurement must be read before projecting a duration')

    measure = ctx.query.get('measure') or observed.measure
    node = SemanticNode('uniform-partition-duration', (
        ('entity', population.entity), ('whole', population.container),
        ('measure', measure), ('scope', scope)))
    if not ctx.reg.word_in_category(population.attribute, 'equal_part_size_attribute'):
        part_label = ctx.reg.singular_to_plural.get(population.measure, population.measure)
        reason = (f'The {part_label} are not stated to be equal in size. A constant pace and the '
                  'time for one part cannot determine the duration of the whole or the remainder '
                  'without equal part sizes or measurements of their sizes.')
        missing = SemanticNode('required-part-equality', (
            ('whole', population.container), ('component', population.measure), ('established', False)))
        return decline(reason, AnswerProof(node, (
            ProofStep('missing-equal-part-sizes', missing, tuple(rows), reason),)))
    # Construct a duration-per-component rate only after equality, scope and
    # the continuation policy have been established. It never enters the
    # store as an observed general rate or an observed whole duration.
    rate = Rate(entity=population.entity, measure=observed.measure, per=population.measure,
                value=observed.value, verb=continuation.verb, provenance=observed.provenance)
    parts = count if scope == 'whole' else count - 1
    duration = apply_rate(rate, parts, ctx.log, source='equal-part-duration-projection')
    factor = conversion_factor(ctx.reg, observed.measure, measure, category='duration_measure')
    if factor is None:
        return decline('the projected duration needs compatible elapsed-time units')
    value = evaluate('duration * factor', {'duration': duration, 'factor': factor}, ctx.log,
                     source='projected-duration-unit') if factor != 1 else duration
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    unit_label = ctx.reg.singular_to_plural.get(measure, measure) if value != 1 else measure
    detail = (f'Projected {scope} duration for {parts:g} equal parts at the explicitly unchanged '
              f'pace: {value:g} {unit_label}.')
    return Answer('number', value, detail, proof=AnswerProof(node, (
        ProofStep('equal-parts-unchanged-rate', node, tuple(rows), detail),)))
