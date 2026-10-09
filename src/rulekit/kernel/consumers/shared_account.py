"""Allocate one complete itemized account equally among its stated payers.

The reader preserves price quotes as Expenditure operands, so the shared
pricing resolver owns unit-versus-lot arithmetic. Quotes do not establish a
payment or a change in the participants' cash balances.
"""
from collections import Counter, defaultdict
from math import isfinite

from . import consumer
from ..answer import Answer
from ..evaluate import evaluate
from ..model import BatchEvidence, Expenditure
from ..numeric_evidence import audit_numeric_mentions
from ..pricing import expenditure_mentions, resolve_expenditure_prices
from ..resource_equations import resource_residual
from ..source_coverage import uncovered_document_units


@consumer('shared-account-cost', applicable=lambda s: any(
    r.kind == 'bill-population' for r in s.by_kind(BatchEvidence)))
def consume(ctx):
    def decline(reason):
        return Answer('decline', None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    groups = [r for r in rows if r.kind == 'bill-population']
    divisions = [r for r in rows if r.kind == 'bill-division']
    expenses = list(ctx.store.by_kind(Expenditure))
    if (len(groups) != 1 or not expenses or len(rows) != 1 + len(divisions)
            or len(divisions) > 1 or ctx.store.collisions or ctx.store.quarantined):
        return decline('one itemized account and one payer population are required')
    if not divisions and ctx.query.get('equal') != 'true':
        return decline('equal division must be explicitly stated')
    group = groups[0]
    if (group.provenance.assumption or not isfinite(group.value)
            or group.value <= 0 or not float(group.value).is_integer()):
        return decline('the payer count must be a positive whole number')
    if 'person' in ctx.match.slots and ctx.query.get('person') != group.entity:
        return decline('the question names a different payer class')
    if len({e.measure for e in expenses}) != 1:
        return decline('account charges must use one currency')
    expected = defaultdict(Counter)
    expected[group.provenance.sentence][group.value] += 1
    for expense in expenses:
        if (expense.provenance.assumption or expense.basis != 'quote'
                or expense.entity or expense.account or expense.channel or expense.supplier
                or expense.provenance.sentence < group.provenance.sentence
                or expense.lot_quantity is None or not isfinite(expense.lot_quantity)
                or expense.lot_quantity <= 0 or not float(expense.lot_quantity).is_integer()):
            return decline('each charge must belong to the complete stated account')
        expected[expense.provenance.sentence].update(expenditure_mentions(expense).values())
    resolved, error = resolve_expenditure_prices(expenses, ctx.log)
    if error:
        return decline(error)
    if any(e.value is None for e in resolved):
        return decline('every account charge needs a known cost')
    if (uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises, ctx.question), expected,
                                      missing='missing', duplicate='duplicate')):
        return decline('every item, cost and payment condition must be accounted for')
    total = resource_residual([e.value for e in resolved], [], ctx.log,
                              source='itemized-account-total')
    value = evaluate('total / payers', {'total': total, 'payers': group.value},
                     ctx.log, source='equal-account-share')
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    ctx.log.consumed_expenditure_keys.update(e.key() for e in expenses)
    return Answer('number', value,
                  f'{total:g} divided equally among {group.value:g} payers; '
                  'relative price quotes are per item or package unless stated as totals.')
