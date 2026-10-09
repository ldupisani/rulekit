"""Resolve an acyclic graph of participants' shares of one joint earning."""
from collections import Counter, defaultdict
from math import isfinite

from ..answer import Answer
from ..evaluate import evaluate
from ..model import BatchEvidence, FractionQuantity, Relation
from ..numeric_evidence import audit_numeric_mentions
from ..source_coverage import uncovered_document_units
from ..predicate_compatibility import predicates_compatible
from ..rate_calculation import convert_units

JOINT_KINDS = frozenset({'joint-total', 'joint-share', 'joint-relative'})


def has_joint_shares(store):
    return any(r.kind in JOINT_KINDS for r in store.by_kind(BatchEvidence))


def difference(ctx):
    def decline(reason):
        return Answer('decline', None, reason)
    rows = list(ctx.store.by_kind(BatchEvidence))
    totals = [r for r in rows if r.kind == 'joint-total']
    if (len(totals) != 1 or ctx.store.collisions or ctx.store.quarantined
            or any(r.kind not in JOINT_KINDS or r.provenance.assumption for r in rows)):
        return decline('shares need one asserted joint total and an unambiguous account')
    total = totals[0]
    if (len(total.members) < 2 or len(set(total.members)) != len(total.members)
            or not isfinite(total.value) or total.value < 0
            or not ctx.reg.word_in_category(total.measure, 'currency_measure')
            or not (ctx.query['measure'] == total.measure or
                    ctx.reg.word_in_category(ctx.query['measure'], 'earnable_quantity_object'))
            or not predicates_compatible(total.verb, ctx.query.get('verb',''), total.measure, ctx.reg)):
        return decline('the question must compare earnings within the stated joint account')
    shares = [r for r in rows if r.kind != 'joint-total']
    # Existing fraction/multiplier comparison grammar supplies the same graph
    # edge. Do not add a second reader for "half/twice as much as".
    for relation in ctx.store.by_kind(Relation):
        if (relation.provenance.assumption or relation.measure not in (None, total.measure)
                or relation.offset or relation.subject_offset or relation.standard_offset
                or relation.subject_owner or relation.standard_owner
                or relation.subject_label or relation.standard_label
                or relation.measure_qualifier or relation.standard_qualifier
                or any(ref and (not ref.resolved or ref.described)
                       for ref in (relation.subject_ref, relation.standard_ref))):
            return decline('only pure comparisons within this earning account define shares')
        shares.append(BatchEvidence(provenance=relation.provenance,kind='joint-relative',
                       entity=relation.subject,measure=total.measure,value=relation.factor,
                       position=0,container=relation.standard,verb=relation.verb or ''))
    if len({r.entity for r in shares}) != len(shares):
        return decline('each participant must have one share definition')
    expected = defaultdict(Counter)
    expected[total.provenance.sentence][total.value] += 1
    values = {}
    for r in shares:
        if (r.entity not in total.members or not isfinite(r.value) or r.value < 0 or r.kind == 'joint-share' and r.value > 1
                or r.provenance.sentence <= total.provenance.sentence
                or not predicates_compatible(r.verb, total.verb, total.measure, ctx.reg)):
            return decline('shares must refer to participants in the same earning event')
        expected[r.provenance.sentence][r.value] += 1
        if r.kind == 'joint-share':
            if r.marker == 'anaphoric':
                # Do not guess past another share or intervening statement.
                # The unique account and complete source/numeric audits below
                # also exclude competing amounts in the antecedent sentence.
                if r.measure or r.provenance.sentence != total.provenance.sentence + 1:
                    return decline('an amount reference needs the immediately preceding joint total')
            else:
                if r.measure != total.measure or r.subtotal != total.value:
                    return decline('the repeated amount must identify the joint total exactly')
                expected[r.provenance.sentence][r.subtotal] += 1
            values[r.entity] = evaluate('total * share', {'total':total.value,'share':r.value},ctx.log,source='joint-total-share')
        elif r.container not in total.members or r.container == r.entity:
            return decline('a relative share must reference another participant')
    pending = [r for r in shares if r.kind == 'joint-relative']
    while pending:
        ready = [r for r in pending if r.container in values]
        if not ready:
            return decline('relative shares form a cycle or have no known base')
        for r in ready:
            values[r.entity] = evaluate('base * share', {'base':values[r.container],'share':r.value},ctx.log,source='relative-earned-share')
            pending.remove(r)
    if sum(values.values()) > total.value + 1e-9:
        return decline('the participants shares exceed the joint total')
    a,b = ctx.query.get('a'),ctx.query.get('b')
    if a == b or a not in values or b not in values:
        return decline('both compared participants need determined earnings')
    if (uncovered_document_units(ctx.premises,ctx.question,ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises,ctx.question),expected,missing='missing',duplicate='duplicate')):
        return decline('every amount and condition must belong to this earning account')
    fractions = list(ctx.store.by_kind(FractionQuantity))
    for fraction in fractions:
        matching = [r for r in shares if r.kind == 'joint-share'
                    and r.entity == fraction.entity and r.measure == fraction.measure
                    and r.value == fraction.fraction and r.verb == fraction.verb
                    and r.provenance.sentence == fraction.provenance.sentence
                    and not fraction.pool_qualifier and fraction.time is None]
        if len(matching) != 1:
            return decline('a generic fraction must identify exactly the same stated share')
    ctx.log.consumed_fraction_keys.update(f.key() for f in fractions)
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    value = evaluate('abs(a - b)', {'a':values[a],'b':values[b]},ctx.log,source='joint-earnings-difference')
    if ctx.reg.word_in_category(ctx.query['measure'], 'currency_measure'):
        value = convert_units(value,total.measure,ctx.query['measure'],ctx.reg,ctx.log,source='joint-earnings-output-unit')
        if value is None:
            return decline('the requested currency unit is not convertible from the account')
    return Answer('number',value,f'Difference between the two determined earnings: {value:g}.')
