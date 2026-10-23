"""A closed purchased basket, selected explicitly or by a complete-domain reference."""
from collections import Counter, defaultdict
from . import consumer
from ..answer import Answer
from ..model import BatchEvidence, Expenditure, Price, Quantity
from ..pricing import expenditure_mentions, resolve_expenditure_prices
from ..numeric_evidence import audit_numeric_mentions
from ..source_coverage import uncovered_document_units
from ..resource_accounting import purchase_collection_contains
from ..resource_equations import resource_residual
from ..learn import _bound


@consumer('closed-purchase-basket')
def consume(ctx):
    def decline(reason):
        return Answer('decline', None, reason)
    expenses = ctx.store.by_kind(Expenditure)
    contexts = ctx.store.by_kind(BatchEvidence)
    # A singular purchased item also establishes one item and its unit
    # price. Preserve those facts for the existing inventory/price asks.
    support = [f for f in ctx.store.facts if isinstance(f, (Price, Quantity))]
    for fact in support:
        matches = [e for e in expenses if e.quantity is None
                   and e.provenance.sentence == fact.provenance.sentence
                   and e.verb == fact.verb]
        if isinstance(fact, Quantity):
            matches = [e for e in matches if e.entity == fact.entity and e.item == fact.measure
                       and (e.qualifier or '') == (fact.measure_qualifier or '') and fact.value == 1]
        else:
            matches = [e for e in matches if e.item == fact.item and e.value == fact.value
                       and (e.qualifier or '') == (fact.qualifier or '')]
        if len(matches) != 1:
            return decline('an inventory or price fact falls outside the purchased basket')
    if (not expenses or ctx.store.collisions or ctx.store.quarantined
            or len(ctx.store.facts) != len(expenses) + len(contexts) + len(support)
            or any(r.kind not in {'occasion-context', 'purchase-contents-context'} for r in contexts)):
        return decline('the basket must contain only fully specified purchases and context')
    buyers = {e.entity for e in expenses if e.entity}
    if len(buyers) != 1 or len({e.measure for e in expenses}) != 1:
        return decline('one buyer and one currency must identify the complete basket')
    all_items = ctx.query.get('scope') == 'all'
    anchors = [e for e in expenses if e.entity]
    if all_items:
        fixed = [min(anchors, key=lambda e: (e.provenance.sentence, e.position))]
    else:
        fixed = [e for e in expenses if (e.item, e.qualifier or '') ==
                 (ctx.query['item'], ctx.query.get('qualifier', '') or '')]
        remainder = [e for e in expenses if e not in fixed]
        if (len(fixed) != 1 or not remainder
                or any(not purchase_collection_contains(ctx.query['collection'], e.item, ctx.reg)
                       for e in remainder)):
            return decline('the named item and collection must partition the purchased basket')
    if (any(e.provenance.assumption or e.basis != 'purchase' for e in expenses)
            or any(not e.entity and e.provenance.sentence < fixed[0].provenance.sentence for e in expenses)):
        return decline('the basket needs actual purchases and an explicit buyer before any continuation')
    # Follow the parser's subject binding at the recorded purchase event.
    # This uses existing expenditure provenance instead of adding a second
    # buyer fact that unrelated accounting consumers would need to consume.
    def buyer_subject(expense):
        for reading in ctx.premises:
            if reading.sentence_index == expense.provenance.sentence:
                for unit in reading.units:
                    if unit.uid == expense.event and unit.sense() == 'verb':
                        return _bound(unit, 'subject')
        return None

    anchor = buyer_subject(fixed[0])
    for expense in expenses:
        if expense.entity:
            continue
        subjects = [buyer_subject(e) for e in expenses
                    if e.provenance.sentence == expense.provenance.sentence]
        subjects = {u.uid: u for u in subjects if u is not None}
        if len(subjects) != 1:
            return decline('a continued purchase needs one same-sentence buyer')
        subject = next(iter(subjects.values()))
        if subject.sense() == 'pronoun' and (
                anchor is None or subject.features.get('number') != anchor.features.get('number')):
            return decline('the buyer pronoun must agree with the explicit buyer')
    packing = [r for r in contexts if r.kind == 'purchase-contents-context']
    if len(packing) > 1 or any(r.provenance.sentence != fixed[0].provenance.sentence for r in packing):
        return decline('packing must refer to the single purchased item in its clause')
    if not all_items and any(r.kind == 'purchase-contents-context' and r.measure != ctx.query['collection'] for r in contexts):
        return decline('the packing context names different contents')
    expected = defaultdict(Counter)
    for e in expenses:
        expected[e.provenance.sentence].update(expenditure_mentions(e).values())
    if (audit_numeric_mentions((*ctx.premises, ctx.question), expected,
                               missing='missing', duplicate='duplicate')
            or uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)):
        return decline('every purchase, price and condition must be read')
    resolved, error = resolve_expenditure_prices(expenses, ctx.log)
    if error or any(e.value is None for e in resolved):
        return decline(error or 'every purchase needs a known cost')
    value = resource_residual([e.value for e in resolved], [], ctx.log, source='closed-purchase-basket')
    ctx.log.consumed_expenditure_keys.update(e.key() for e in expenses)
    ctx.log.consumed_batch_keys.update(r.key() for r in contexts)
    return Answer('number', value, 'sum fixed item costs and explicit package count × package price charges')
