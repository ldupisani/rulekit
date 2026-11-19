"""Allocate one complete itemized account equally among its stated payers.

The reader preserves price quotes as Expenditure operands, so the shared
pricing resolver owns unit-versus-lot arithmetic. Quotes do not establish a
payment or a change in the participants' cash balances.
"""
from collections import Counter, defaultdict
from functools import partial
from math import isfinite

from . import consumer
from .indexed_path import ordinal_index
from ..answer import Answer, AnswerAssumption, ClarificationOption, ClarificationRequest, SemanticNode
from ..evaluate import evaluate
from ..model import BatchEvidence, Expenditure, Quantity
from ..numeric_evidence import audit_numeric_mentions
from ..pricing import expenditure_mentions, resolve_expenditure_prices
from ..resource_equations import equal_share, resource_residual
from ..source_coverage import uncovered_document_units


@consumer('shared-account-cost', applicable=lambda s: any(
    r.kind == 'bill-population' for r in s.by_kind(BatchEvidence)))
def consume(ctx):
    def decline(reason):
        return Answer('decline', None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    groups = [r for r in rows if r.kind == 'bill-population']
    divisions = [r for r in rows if r.kind == 'bill-division']
    subdivisions = [r for r in rows if r.kind == 'within-group-division']
    pairs = [r for r in rows if r.kind == 'cohort-pair']
    expenses = list(ctx.store.by_kind(Expenditure))
    if (len(groups) != 1 or not expenses or len(rows) != 1 + len(divisions) + len(subdivisions) + len(pairs)
            or len(pairs) > 1 or len(divisions) > 1 or len(subdivisions) > 1 or ctx.store.collisions or ctx.store.quarantined):
        return decline('one itemized account and one payer population are required')
    if not divisions and ctx.query.get('equal') != 'true':
        return decline('equal division must be explicitly stated')
    group = groups[0]
    if (group.provenance.assumption or not isfinite(group.value)
            or group.value <= 0 or not float(group.value).is_integer()):
        return decline('the payer count must be a positive whole number')
    if len({e.measure for e in expenses}) != 1:
        return decline('account charges must use one currency')
    expected = defaultdict(Counter)
    expected[group.provenance.sentence][group.value] += 1
    roster = list(ctx.store.by_kind(Quantity))
    pair = next(iter(pairs), None)
    if pair:
        if (pair.provenance.assumption or pair.value != 1 or group.value != 2
                or pair.entity != group.entity or len(roster) != 2
                or any(r.provenance.sentence != pair.provenance.sentence or r.measure != pair.measure
                       for r in roster)):
            return decline('the contrasted counts must identify both purchasing groups')
        expected[pair.provenance.sentence][pair.value] += 1
    for count in roster:
        expected[count.provenance.sentence][count.value] += 1
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
    answer = _allocate(ctx, total, group, roster, divisions, subdivisions, pair)
    if answer.committed:
        ctx.log.consumed_batch_keys.update(r.key() for r in rows)
        ctx.log.consumed_expenditure_keys.update(e.key() for e in expenses)
    return answer


def _roster_sizes(ctx, group, roster, pair):
    """Keep ordinal indices and explicit pair labels distinct when indexing a complete roster."""
    uniform = None
    indexed = {}
    for row in roster:
        ref = row.entity_ref
        if (not ref.resolved or ref.head != group.entity or ref.owner or ref.label
                or row.provenance.assumption or row.owner or row.time or not row.is_state
                or row.measure_qualifier or row.content_ref or row.label
                or not ctx.reg.word_in_category(row.verb, 'plain_have_state')
                or not ctx.reg.word_in_category(row.measure, 'cohort_member')
                or not isfinite(row.value) or row.value <= 0 or not float(row.value).is_integer()):
            return None
        if row.provenance.distributive and not ref.qualifiers:
            if uniform is not None:
                return None
            uniform = row.value
        elif not row.provenance.distributive and len(ref.qualifiers) == 1:
            label, = ref.qualifiers
            if pair:
                if label not in (pair.marker, pair.attribute):
                    return None
                index = label
            else:
                index = ordinal_index(label, ctx.reg)
                if index is None or index > group.value:
                    return None
            if index in indexed:
                return None
            indexed[index] = (label, row.value)
        else:
            return None
    if uniform is not None and not indexed:
        return uniform, {}
    if uniform is None and len(indexed) == group.value:
        sizes = {size for _, size in indexed.values()}
        common_size = next(iter(sizes)) if len(sizes) == 1 else None
        return common_size, indexed
    return None


def _allocate(ctx, total, group, roster, divisions, subdivisions, pair):
    share = partial(equal_share, log=ctx.log, source='equal-account-share')
    scopes = {d.measure or d.entity for d in divisions if d.measure or d.entity}
    if ctx.query.get('basis'):
        scopes.add(ctx.query['basis'])
    if len(scopes) > 1:
        return Answer('decline', None, 'the invoice specifies conflicting division groups')
    basis = next(iter(scopes), None)
    payer = ctx.query.get('person')
    if not payer:
        if roster and (not basis or subdivisions):
            return Answer('decline', None, 'specify whether the question asks about the groups or their members')
        payer = basis or group.entity
    initiators = {d.entity for d in divisions if d.entity}
    if not roster:
        if initiators - {group.entity}:
            return Answer('decline', None, 'the division names participants outside the purchasing group')
        if payer != group.entity or basis not in (None, group.entity) or subdivisions or ctx.query.get('cohort'):
            return Answer('decline', None, 'the question needs explicit member counts for the purchasing groups')
        return Answer('number', share(total, group.value),
                      f'{total:g} divided equally among {group.value:g} payers.')

    roles = {r.measure for r in roster}
    sizes = _roster_sizes(ctx, group, roster, pair)
    if (len(roles) != 1 or sizes is None
            or not ctx.reg.word_in_category(group.entity, 'membership_collective')):
        return Answer('decline', None, 'member counts must describe every purchasing group exactly once')
    member, = roles
    if (initiators - {group.entity, member} or member == group.entity or payer not in (member, group.entity)
            or basis not in (None, member, group.entity)):
        return Answer('decline', None, 'the division and question must identify the counted payers')
    if subdivisions:
        within, = subdivisions
        if (within.entity != group.entity or within.measure != member or basis == member):
            return Answer('decline', None, 'the within-group division must apply to each purchasing group’s share')
        basis = group.entity
    uniform, indexed = sizes
    index = None
    if ctx.query.get('cohort'):
        label = ctx.query['index']
        if pair:
            index = label if label in indexed else None
        else:
            index = ordinal_index(label, ctx.reg)
            if index is not None and index > group.value:
                index = None
        if payer != member or ctx.query['cohort'] != group.entity or index is None:
            return Answer('decline', None, 'the question must identify a member of a stated group')

    clarification = None
    if basis is None and payer == member and uniform is None:
        clarification = _division_clarification(ctx.interpretation, group.entity, member)
        selected = clarification.selected
        if selected is None:
            return Answer('decline', None, 'unequal group sizes give different per-member payments',
                          clarification=clarification)
        basis = member if selected == 'among-members' else group.entity
    assumptions = ()
    if basis is None and payer == member:
        sources = {r.provenance.sentence for r in [*roster, *divisions]}
        if ctx.query.get('equal'):
            sources.add(ctx.question.sentence_index)
        assumptions = (AnswerAssumption('equal-member-contributions',
                       'The per-member question is read as an equal contribution from every member. '
                       'An equal split within each equal-sized group gives the same payment.',
                       tuple(sorted(sources))),)
    basis = basis or payer
    if basis == group.entity and payer == member and not (subdivisions or clarification):
        return Answer('decline', None, 'state how each group divides its share among its members')
    if payer == basis == group.entity:
        return Answer('number', share(total, group.value),
                      f'{total:g} divided into {group.value:g} equal group shares.')

    return _member_payments(ctx, total, group, sizes, index,
                            per_member_question=payer == member, members_split=basis == member,
                            clarification=clarification, assumptions=assumptions)


def _division_clarification(interpretation, group, member):
    options = (
        ClarificationOption('among-members', 'Equal member shares',
                            'Divide the invoice equally among all members.',
                            SemanticNode('account-division', (('payers', member),))),
        ClarificationOption('within-groups', 'Equal group shares, then equal member shares',
                            'Each group pays the same total and divides it equally among its members.',
                            SemanticNode('account-division', (('payers', group), ('within', member)))),
    )
    selected = interpretation if interpretation in {option.id for option in options} else None
    return ClarificationRequest('Who shares the invoice equally?', options, selected)


def _member_payments(ctx, total, group, sizes, index, *, per_member_question, members_split,
                     clarification, assumptions):
    uniform, indexed = sizes
    share = partial(equal_share, log=ctx.log, source='equal-account-share')
    if members_split:
        if uniform is None:
            population = resource_residual([size for _, size in indexed.values()], [], ctx.log,
                                          source='group-member-population')
        else:
            population = evaluate('groups * size', dict(groups=group.value, size=uniform),
                                  ctx.log, source='group-member-population')
        per_member = share(total, population)
        if per_member_question:
            return Answer('number', per_member, f'{total:g} divided among {population:g} members.',
                          clarification=clarification, assumptions=assumptions)

        def group_contribution(size):
            return evaluate('size * share', dict(size=size, share=per_member), ctx.log,
                            source='group-member-contributions')

        amount = group_contribution
        reason = 'Sum the equal member payments in each group.'
    else:
        per_group = share(total, group.value)
        amount = partial(share, per_group)
        reason = f'Divide each group’s share of {per_group:g} equally among its members.'

    if index is not None or uniform is not None:
        size = uniform if uniform is not None else indexed[index][1]
        return Answer('number', amount(size), reason, clarification=clarification)
    currency = next(iter(ctx.store.by_kind(Expenditure))).measure
    values = [{'entity': f'{label} {group.entity}', 'measure': currency, 'value': amount(size)}
              for _, (label, size) in sorted(indexed.items())]
    return Answer('series', values, reason, clarification=clarification)
