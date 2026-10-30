"""One unknown elapsed duration in an exhaustive, ordered process partition."""
from collections import Counter, defaultdict
from math import isfinite

from . import consumer
from .indexed_path import ordinal_index
from ..answer import Answer, AnswerProof, ProofStep, SemanticNode
from ..dimensions import conversion_factor
from ..evaluate import evaluate
from ..model import BatchEvidence
from ..numeric_evidence import audit_numeric_mentions
from ..reference_bindings import anaphoric_forms_agree
from ..reference_identity import constrains, reference_from_unit
from ..resource_equations import resource_residual
from ..source_coverage import uncovered_document_units


@consumer('process-part-remainder', applicable=lambda s: any(
    r.kind == 'process-population' for r in s.by_kind(BatchEvidence)))
def consume(ctx):
    def decline(reason):
        return Answer('decline', None, reason)
    rows = list(ctx.store.by_kind(BatchEvidence))
    populations = [r for r in rows if r.kind == 'process-population']
    totals = [r for r in rows if r.kind == 'process-total-duration']
    parts = sorted((r for r in rows if r.kind in {'process-part-duration', 'process-part-factor'}),
                   key=lambda r: (r.provenance.sentence, r.position))
    if (len(populations) != 1 or len(totals) != 1 or not parts
            or len(rows) != len(ctx.store.facts) or len(rows) != len(parts) + 2
            or ctx.store.collisions or ctx.store.quarantined):
        return decline('one process partition, its total and complete known parts are required')
    population, total = populations[0], totals[0]
    # An unqualified elapsed-time question uses the first directly measured
    # part's unit. This is an output convention, not an assumed duration;
    # every part and the total still need compatible stated measurements.
    measure = ctx.query.get('measure') or parts[0].measure

    def duration_in_output_unit(row, source):
        factor = conversion_factor(ctx.reg, row.measure, measure, category='duration_measure')
        if factor is None:
            return None
        return evaluate('duration * factor', {'duration': row.value, 'factor': factor}, ctx.log,
                        source=source) if factor != 1 else row.value

    count = ordinal_index(population.value, ctx.reg)
    requested = ordinal_index(ctx.query['index'], ctx.reg)
    whole = population.container_ref
    query_whole = ctx.match.slots.get('whole')
    if (count is None or count < 2 or requested is None or not 1 <= requested <= count
            or population.entity != ctx.query['entity'] or total.entity != population.entity
            or ctx.query['part'] != population.measure or whole is None or not whole.resolved
            or total.container_ref is None or not constrains(total.container_ref, whole)
            or not isfinite(total.value) or total.value < 0
            or ctx.query.get('whole') and ctx.query['whole'] != population.container
            or query_whole is not None and whole is not None and not constrains(reference_from_unit(query_whole), whole)
            or population.provenance.assumption
            or total.provenance.assumption and total.provenance.sentence != ctx.question.sentence_index - 1):
        return decline('the participant, process, part and total duration must identify one partition')
    expected = defaultdict(Counter)
    expected[population.provenance.sentence][population.value] += 1
    expected[total.provenance.sentence][total.value] += 1
    values = {}
    previous = None
    for row in parts:
        index = ordinal_index(row.marker, ctx.reg)
        if (index is None or not 1 <= index <= count or index == requested or index in values
                or row.attribute != population.measure or row.provenance.assumption
                or row.provenance.sentence <= population.provenance.sentence
                or not isfinite(row.value) or row.value <= 0):
            return decline('each known part needs one positive duration in the same ordered process')
        expected[row.provenance.sentence][row.value] += 1
        if row.kind == 'process-part-factor':
            forms = [surface for surface in (previous.acquisition if previous else '', row.acquisition)
                     if getattr(ctx.reg.lexicon.get(surface.casefold()), 'anaphoric_form', None) is not None]
            if (previous is None or index != ordinal_index(previous.marker, ctx.reg) + 1
                    or row.provenance.sentence != previous.provenance.sentence + 1
                    or not anaphoric_forms_agree(forms, 'singular', ctx.reg)
                    or row.entity_ref and row.entity_ref.resolved and row.entity != population.entity):
                return decline('a relative duration needs the immediately preceding part and compatible actor')
            value = evaluate('previous * factor', {'previous': values[index - 1], 'factor': row.value},
                             ctx.log, source='relative-part-duration')
        else:
            if (row.entity != population.entity or row.container_ref is not None
                    and not constrains(row.container_ref, whole)):
                return decline('a known part describes a different participant or process')
            value = duration_in_output_unit(row, 'process-part-duration-unit')
            if value is None:
                return decline('part durations must have compatible elapsed-time units')
        values[index] = value
        previous = row
    if len(values) != count - 1:
        return decline('all other parts of the exhaustive process must be known')
    if (uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises, ctx.question), expected, missing='missing', duplicate='duplicate')):
        return decline('every process condition and duration must be read')
    converted = duration_in_output_unit(total, 'whole-process-duration-unit')
    if converted is None:
        return decline('the whole process needs compatible elapsed-time units')
    remaining = resource_residual([converted], values.values(), ctx.log, source='process-part-remainder')
    if remaining < 0:
        return decline('known parts exceed the total duration')
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    node = SemanticNode('process-part-remainder', (('entity', population.entity),
                        ('index', str(requested)), ('measure', measure)))
    detail = f'Total process duration minus every other part, with units normalized: {remaining:g} {measure}.'
    return Answer('number', remaining, detail, proof=AnswerProof(node, (
        ProofStep('complete-process-residual', node, tuple(rows), detail),)))
