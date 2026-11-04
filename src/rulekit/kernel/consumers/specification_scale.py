"""Apply an explicitly adopted input/output ratio to a scoped output demand."""
from collections import Counter, defaultdict
from math import isfinite

from . import consumer
from ..answer import Answer
from ..evaluate import evaluate
from ..model import Rate, SpecificationEvidence
from ..numeric_evidence import audit_numeric_mentions
from ..rate_calculation import apply_ratio, convert_units
from ..source_coverage import uncovered_document_units


@consumer('specification-scale', applicable=lambda s: bool(s.by_kind(SpecificationEvidence)))
def consume(ctx):
    def decline(reason):
        return Answer('decline', None, reason)

    rows = list(ctx.store.by_kind(SpecificationEvidence))
    if (ctx.store.collisions or ctx.store.quarantined
            or any(r.provenance.assumption for r in rows)):
        return decline('the specification and its application must be asserted and unambiguous')
    by_kind = defaultdict(list)
    for row in rows:
        by_kind[row.kind].append(row)
    if any(len(group) != 1 for group in by_kind.values()):
        return decline('each specification role must have one definition')
    expected = defaultdict(Counter)
    if set(by_kind) == {'reference', 'application'}:
        reference, target = by_kind['reference'][0], by_kind['application'][0]
        entity = target.entity
        if (not reference.scope or reference.scope != target.scope
                or reference.output_item != target.output_item
                or reference.provenance.sentence >= target.provenance.sentence):
            return decline('the application must identify the stated specification and output')
        population = 1.0  # Direct output demand, not a source-stated population.
        expected[target.provenance.sentence][target.output_value] += 1
    elif set(by_kind) == {'context', 'reference', 'reuse', 'target'}:
        context, reference, reuse, target = (
            by_kind[k][0] for k in ('context', 'reference', 'reuse', 'target'))
        entity = context.entity
        scope = context.scope_ref
        if (scope is None or not scope.resolved or target.scope_ref is None
                or not target.scope_ref.resolved or scope != target.scope_ref):
            return decline('the demand must identify the same scope and owner as the plan')
        if reuse.scope == '$anaphor:population$':
            if not ctx.reg.word_in_category(target.population_item, 'person'):
                return decline('a universal person reference needs an explicitly counted human population')
        elif scope != reuse.scope_ref:
            return decline('the adopted ratio must apply to the same scope and owner')
        if (entity != reuse.entity or (reference.entity and reference.entity != entity)
                or len({context.output_item, reference.output_item, target.output_item}) != 1
                or not context.provenance.sentence < reference.provenance.sentence
                < reuse.provenance.sentence < target.provenance.sentence
                or not isfinite(target.population) or target.population <= 0
                or not float(target.population).is_integer()):
            return decline('the context, reference, adoption and population must describe one plan')
        population = target.population
        expected[target.provenance.sentence].update((population, target.output_value))
    else:
        return decline('a reference ratio needs an explicit matching application or serving plan')
    if (entity != ctx.query['entity'] or reference.input_item != ctx.query['input_item']
            or not all(isfinite(v) and v > 0 for v in
                       (reference.value, reference.output_value, target.output_value))):
        return decline('the requested input and actor must match a positive input/output specification')
    expected[reference.provenance.sentence].update((reference.value, reference.output_value))
    if (uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises, ctx.question), expected,
                                      missing='missing', duplicate='duplicate',
                                      additional_kinds=('attributive_count',))):
        return decline('every input, output and condition must belong to the specification')
    size = convert_units(target.output_value, target.output_measure, reference.output_measure,
                         ctx.reg, ctx.log, source='specification-output-unit')
    if size is None:
        return decline('output quantities must use compatible units')
    demand = evaluate('population * size', {'population': population, 'size': size},
                      ctx.log, source='specification-output-demand')
    amount = apply_ratio(reference.value, reference.output_value, demand, ctx.log,
                         source='specification-input-required')
    value = convert_units(amount, reference.measure, ctx.query['measure'],
                          ctx.reg, ctx.log, source='specification-input-unit')
    if value is None:
        return decline('the requested input unit is not convertible')
    ctx.log.consumed_component_keys.update(r.key() for r in rows)
    return Answer('number', value, 'Apply the stated input/output ratio to the explicitly adopted output demand.')
