"""Multiply place-scoped per-station yields, preserving ordered site identity."""
from collections import Counter,defaultdict
from dataclasses import replace
from math import isfinite
from . import consumer
from ..answer import Answer
from ..model import BatchEvidence,Rate
from ..evaluate import evaluate
from ..rate_calculation import apply_rate
from ..source_coverage import uncovered_document_units
from ..numeric_evidence import audit_numeric_mentions
from ..predicate_compatibility import predicates_compatible


@consumer('located-yield-difference',applicable=lambda s:any(r.kind=='located-yield' for r in s.by_kind(BatchEvidence)))
def consume(ctx):
    def decline(reason):return Answer('decline',None,reason)
    rows=list(ctx.store.by_kind(BatchEvidence))
    yields=sorted((r for r in rows if r.kind=='located-yield'),key=lambda r:(r.provenance.sentence,r.position))
    counts=[r for r in rows if r.kind=='site-population']
    contexts=[r for r in rows if r.kind=='located-context']
    used_contexts=[]
    for i,y in enumerate(yields):
        if y.acquisition:
            continue
        matches=[c for c in contexts if c.entity==y.entity
                 and c.provenance.sentence+1==y.provenance.sentence
                 and not c.provenance.assumption]
        if len(matches)!=1:
            return decline('an unlocated rate needs one immediately preceding outing by the same collector')
        context=matches[0]
        used_contexts.append(context.key())
        yields[i]=replace(y,acquisition=context.acquisition,marker=context.marker,
                          acquisition_ref=context.acquisition_ref)
    if len(used_contexts)!=len(contexts) or len(set(used_contexts))!=len(contexts):
        return decline('each outing context must ground exactly one yield')
    if (len(yields)!=2 or len(counts)!=2 or len(rows)!=4+len(contexts) or ctx.store.collisions or ctx.store.quarantined
            or len({r.entity for r in yields})!=2):
        return decline('an omitted comparison standard needs exactly two distinct scoped yields')
    expected=defaultdict(Counter);values={};used=[]
    for index,y in enumerate(yields,1):
        match=[r for r in counts if ctx.reg.attrs.get(r.marker,{}).get('ordinal_index')==index]
        if len(match)!=1:return decline('each site needs one count at its discourse index')
        n=match[0];used.append(n)
        site=n.entity
        if not site:
            antecedents=[r for r in counts if r.entity
                         and (r.provenance.sentence,r.position)<(n.provenance.sentence,n.position)]
            if len(antecedents)!=1:
                return decline('an elided site needs one preceding explicit population head')
            site=antecedents[0].entity
        if (y.provenance.assumption or site!=y.acquisition or n.measure!=y.container
                or n.provenance.sentence<yields[-1].provenance.sentence
                or y.measure!=ctx.query['measure'] or y.attribute!=ctx.query['item']
                or not predicates_compatible(y.verb,ctx.query['verb'],y.attribute,ctx.reg)
                or y.marker and not any(ctx.reg.word_in_category(y.marker,c)
                                         for c in ('nearby_location_descriptor','distinct_location_descriptor'))
                or y.acquisition_ref is not None and not y.acquisition_ref.resolved
                or not all(isfinite(v) and v>=0 and float(v).is_integer() for v in (y.value,n.value))):
            return decline('each rate must match its own site population, item and acquisition event')
        expected[y.provenance.sentence][y.value]+=1;expected[n.provenance.sentence][n.value]+=1
        rate=Rate(entity=y.entity,measure=y.measure,per=y.container,value=y.value,verb=y.verb,provenance=y.provenance)
        values[y.entity]=apply_rate(rate,n.value,ctx.log,source='located-station-yield')
    if len({r.key() for r in used})!=2:return decline('the site counts must be distinct')
    a=ctx.query['entity'];other=ctx.query.get('other')
    if a not in values or other and (other not in values or other==a):return decline('the named comparison must refer to the two established collectors')
    b=next(p for p in values if p!=a)
    if (uncovered_document_units(ctx.premises,ctx.question,ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises,ctx.question),expected,missing='missing',duplicate='duplicate')):
        return decline('every location, event and count must belong to the compared yields')
    direction=-1 if ctx.reg.word_in_category(ctx.query['direction'],'less_dir') else 1
    value=evaluate('direction * (a - b)',{'direction':direction,'a':values[a],'b':values[b]},ctx.log,source='located-yield-difference')
    if value<0:return decline('the stated comparative direction conflicts with the yields')
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    return Answer('number',value,'Compare the two per-station yields after applying each site population.')
