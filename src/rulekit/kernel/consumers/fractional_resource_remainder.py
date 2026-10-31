"""Ordered allocations from a measured opening stock or its current balance."""
from collections import Counter, defaultdict
from math import isfinite

from ..answer import Answer
from ..dimensions import conversion_factor
from ..evaluate import evaluate
from ..model import BatchEvidence, RegionEvidence
from ..numeric_evidence import audit_numeric_mentions
from ..resource_equations import resource_residual
from ..source_coverage import uncovered_document_units


def consume(ctx):
    def decline(reason):
        return Answer('decline', None, reason)
    measurements = list(ctx.store.by_kind(RegionEvidence))
    batches = list(ctx.store.by_kind(BatchEvidence))
    steps = sorted((r for r in batches if r.kind == 'fractional-resource-use'),
                   key=lambda r: (r.provenance.sentence, r.position))
    goals = [r for r in batches if r.kind == 'resource-production-goal']
    if (len(measurements) != 1 or not steps or len(goals) > 1
            or len(steps) + len(goals) != len(batches)
            or len(measurements) + len(batches) != len(ctx.store.facts)
            or ctx.store.collisions or ctx.store.quarantined):
        return decline('one measured stock and a complete sequence of fractional uses are required')
    opening = measurements[0]
    if (opening.stage != 'opening' or opening.shape or opening.dimension
            or not opening.quantity or opening.material != ctx.query['material']
            or ctx.query.get('quantity') not in ('inferred', opening.quantity)
            or opening.provenance.assumption or not isfinite(opening.value) or opening.value < 0
            or any(g.entity != opening.entity or g.measure != opening.material
                   or g.provenance.sentence != opening.provenance.sentence for g in goals)):
        return decline('the question must identify the same measured resource stock')
    expected = defaultdict(Counter)
    expected[opening.provenance.sentence][opening.value] += 1
    balance = opening.value
    purposes = set()
    remainder_seen = False
    for step in steps:
        anchors = [r for r in steps if r.entity and r.provenance.sentence == step.provenance.sentence]
        actor = step.entity or (anchors[0].entity if len(anchors) == 1 else '')
        if (actor != opening.entity or step.provenance.sentence <= opening.provenance.sentence
                or step.provenance.assumption or not isfinite(step.value) or not 0 <= step.value <= 1
                or step.marker not in {'opening', 'remainder'}
                or step.measure and step.measure != opening.material
                or step.container_ref is None or not step.container_ref.resolved):
            return decline('each fraction must name the same stock or its current remainder')
        # Parallel uses in one allocation clause share its opening-stock
        # base. Across sentences, a fresh unqualified fraction may instead
        # refer to what is now held; neither a pronoun nor a repeated resource
        # name establishes the original amount after depletion. An explicit
        # switch to the remainder also prevents a silent switch back.
        if (step.marker == 'opening'
                and (remainder_seen or step.provenance.sentence != steps[0].provenance.sentence)
                and balance != opening.value):
            return decline('a later fraction must distinguish the original stock from its current remainder')
        expected[step.provenance.sentence][step.value] += 1
        base = opening.value if step.marker == 'opening' else balance
        allocated = evaluate('base * fraction', {'base': base, 'fraction': step.value},
                             ctx.log, source='fractional-resource-allocation')
        balance = resource_residual([balance], [allocated], ctx.log, source='fractional-resource-balance')
        remainder_seen |= step.marker == 'remainder'
        if balance < -1e-9:
            return decline('the stated allocations exceed the resource stock')
        purposes.add(step.container_ref)
    if 'purpose_count' in ctx.query:
        count = float(ctx.query['purpose_count'])
        expected[ctx.question.sentence_index][count] += 1
        if (count != len(purposes) or not count.is_integer()
                or any(p.head != ctx.query['product'] for p in purposes)):
            return decline('the stated number of production varieties must match the distinct uses')
        evaluate('count', {'count': count}, ctx.log, source='verified-production-variety-count')
    if (uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises, ctx.question), expected, missing='missing', duplicate='duplicate')):
        return decline('every stock measurement, allocation and condition must be read')
    unit = ctx.query.get('unit') or opening.unit
    factor = conversion_factor(ctx.reg, opening.unit, unit)
    if factor is None:
        return decline('the requested unit is incompatible with the measured stock')
    value = evaluate('remaining * factor', {'remaining': max(0, balance), 'factor': factor},
                     ctx.log, source='fractional-resource-output-unit')
    ctx.log.consumed_batch_keys.update(r.key() for r in batches)
    ctx.log.consumed_component_keys.add(opening.key())
    return Answer('number', value, 'subtract explicit fractions of the original stock or current remainder in order')
