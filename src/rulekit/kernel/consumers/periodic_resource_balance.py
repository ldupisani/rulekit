"""A contiguous series of actual acquisition blocks and scoped transfers."""
from collections import Counter, defaultdict
from math import isfinite

from . import consumer
from .indexed_path import ordinal_index
from ..answer import Answer, ClarificationOption, ClarificationRequest, SemanticNode
from ..evaluate import evaluate
from ..model import BatchEvidence
from ..numeric_evidence import audit_numeric_mentions
from ..rate_calculation import convert_duration
from ..reference_identity import constrains
from ..resource_equations import resource_residual
from ..source_coverage import uncovered_document_units


@consumer('periodic-resource-balance', applicable=lambda s: any(
    r.kind in {'periodic-resource-gain', 'periodic-resource-rate', 'periodic-resource-unscoped-block'}
    for r in s.by_kind(BatchEvidence)))
def consume(ctx):
    def decline(reason):
        return Answer('decline', None, reason)
    rows = sorted(ctx.store.by_kind(BatchEvidence), key=lambda r: (r.provenance.sentence, r.position))
    contexts = [r for r in rows if r.kind == 'periodic-resource-context']
    gains = [r for r in rows if r.kind in {
        'periodic-resource-gain', 'periodic-resource-rate', 'periodic-resource-unscoped-block'}]
    transfers = [r for r in rows if r.kind == 'periodic-resource-transfer']
    if (not gains or len(contexts) > 1 or len(rows) != len(ctx.store.facts)
            or len(rows) != len(contexts) + len(gains) + len(transfers)
            or ctx.store.collisions or ctx.store.quarantined):
        return decline('one complete sequence of acquisitions and actual transfers is required')
    if any(r.entity != ctx.query['entity'] or r.measure != ctx.query['measure']
           or r.provenance.assumption or not isfinite(r.value) or r.value < 0
           or not float(r.value).is_integer() for r in rows):
        return decline('all events must describe the same participant and countable resource')
    context = contexts[0] if contexts else None
    ambiguous = [r for r in gains if r.kind == 'periodic-resource-unscoped-block' and r.fraction > 1]
    if len(ambiguous) > 1:
        return decline('multiple blocks need independently stated total or per-period scopes')
    clarification = None
    if ambiguous:
        row = ambiguous[0]
        choices = tuple(ClarificationOption(
            basis, label, description,
            SemanticNode('acquisition-block-scope', (('basis', basis), ('sentence', row.provenance.sentence))),
        ) for basis, label, description in (
            ('block-total', 'Total across the block', 'The stated amount covers all periods in the block.'),
            ('per-period', 'Amount in each period', 'The stated amount repeats in each period in the block.'),
        ))
        selected = ctx.interpretation if ctx.interpretation in {'block-total', 'per-period'} else None
        clarification = ClarificationRequest(
            'Does the amount for the successive periods describe their combined total or an amount in each period?',
            choices, selected=selected)
    expected = defaultdict(Counter)
    available = []
    covered = 0
    endpoints = {}
    for row in gains:
        if row.acquisition != ctx.query['period'] or row.fraction <= 0 or not float(row.fraction).is_integer():
            return decline('each block needs a positive integral number of the same elapsed periods')
        if row.marker == 'successive':
            if covered == 0:
                return decline('a successive block needs an immediately preceding indexed period')
            expected[row.provenance.sentence][row.fraction] += 1
            end = covered + int(row.fraction)
        else:
            end = ordinal_index(row.marker, ctx.reg)
            if row.fraction != 1 or end != covered + 1:
                return decline('indexed periods must form a complete series without gaps or overlaps')
        expected[row.provenance.sentence][row.value] += 1
        if context and (context.marker != row.acquisition or context.verb != row.verb
                        or row.container_ref is not None and (
                            context.container_ref is None or not constrains(row.container_ref, context.container_ref))):
            return decline('the collection events must agree with their stated duty and source')
        if row.kind == 'periodic-resource-rate' or row in ambiguous and clarification.selected == 'per-period':
            denominator = row.attribute if row.kind == 'periodic-resource-rate' else row.acquisition
            periods = convert_duration(row.fraction, row.acquisition, denominator, ctx.reg, ctx.log,
                                       source='acquisition-rate-periods')
            if periods is None:
                return decline('the rate denominator must be compatible with the acquisition block')
            amount = evaluate('rate * periods', {'rate': row.value, 'periods': periods},
                              ctx.log, source='periodic-resource-rate')
        elif row.kind in {'periodic-resource-gain', 'periodic-resource-unscoped-block'} and not row.attribute:
            amount = row.value
            evaluate('span', {'span': row.fraction}, ctx.log, source='acquisition-block-extent')
        else:
            return decline('a block amount must explicitly distinguish its total from a per-period rate')
        if not float(amount).is_integer():
            return decline('the elapsed periods must produce a whole count of resources')
        available.append(amount)
        covered = end
        endpoints[row.provenance.sentence] = (row, end)
    if covered != ordinal_index(ctx.query['index'], ctx.reg):
        return decline('the question must identify the end of the complete observed series')
    removed = []
    for row in transfers:
        gain, end = endpoints.get(row.provenance.sentence, (None, None))
        if (gain is None or ordinal_index(row.marker, ctx.reg) != end or row.position <= gain.position
                or row.container_ref is None or not row.container_ref.resolved
                or row.value > gain.value):
            return decline('a partitive transfer must identify its actual same-period acquired collection')
        expected[row.provenance.sentence][row.value] += 1
        removed.append(row.value)
    if (uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises, ctx.question), expected, missing='missing', duplicate='duplicate')):
        return decline('every period, acquisition, transfer and condition must be read')
    value = resource_residual(available, removed, ctx.log, source='periodic-resource-balance')
    if value < 0:
        return decline('transfers exceed the acquired resources')
    if clarification is not None and clarification.selected is None:
        return Answer('decline', None, 'the successive block amount needs an explicit scope',
                      clarification=clarification)
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    return Answer('number', value, 'sum the stated block totals or explicit period rates, then subtract actual transfers',
                  clarification=clarification)
