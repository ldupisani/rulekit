"""Revenue from an explicitly priced product mix and a relative sales amount."""
from collections import Counter, defaultdict
from math import isfinite
from . import consumer
from .production_profit import compatible_products
from ..answer import Answer, AnswerProof, ProofStep, SemanticNode
from ..model import Atom, CommercialTerm, Membership, Predication
from ..numeric_evidence import audit_numeric_mentions
from ..source_coverage import membership_source_units, uncovered_units
from ..evaluate import evaluate
from ..resource_equations import resource_residual


@consumer("sales-revenue")
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)
    terms = list(ctx.store.by_kind(CommercialTerm))
    prices = [t for t in terms if t.basis == "basket-price"]
    counts = [t for t in terms if t.basis == "basket-count"]
    scales = [t for t in terms if t.basis == "sales-scale"]
    if not prices or not counts or len(scales) != 1 or len(terms) != len(prices)+len(counts)+1:
        return decline("sales revenue needs one completely priced prior product mix and one current multiplier")
    scale = scales[0]
    if (not ctx.query['entity'] or any(t.entity != ctx.query['entity'] for t in terms)
            or any(not isfinite(t.value) or t.value < 0 for t in terms)
            or ctx.store.collisions or ctx.store.quarantined
            or any(t.provenance.assumption for t in prices + counts)
            or any(not float(t.value).is_integer() for t in counts)
            or any(t.period != scale.period for t in counts)
            or scale.period != ctx.query['period']
            or any(t.provenance.sentence >= scale.provenance.sentence for t in prices+counts)):
        return decline("the same seller and period unit must scope the complete sales comparison")
    keyed_prices = {(p.item,p.qualifier):p for p in prices}
    keyed_counts = {(c.item,c.qualifier):c for c in counts}
    if (len(keyed_prices) != len(prices) or len(keyed_counts) != len(counts)
            or keyed_prices.keys() != keyed_counts.keys()
            or len({p.measure for p in prices}) != 1):
        return decline("each sold product descriptor needs exactly one price in the same currency")
    for reading in ctx.premises:
        for unit in reading.units:
            word = unit.features.get('lemma','')
            if ctx.reg.word_in_category(word,'commercial_product'):
                if unit.features.get('owner') or len(unit.features.get('reference_qualifiers',())) > 1:
                    return decline("product restrictions must be preserved by the complete price key")
    background_coverage = defaultdict(set)
    for f in ctx.store.facts:
        if isinstance(f,CommercialTerm):
            continue
        if (isinstance(f, Atom) and f.entity == scale.entity and f.polarity
                and ctx.reg.word_in_category(f.pred, "person")):
            continue
        if (isinstance(f, Membership) and f.member == scale.entity and f.polarity
                and ctx.reg.word_in_category(f.collection, "person")):
            reading = next((r for r in ctx.premises if r.sentence_index == f.provenance.sentence), None)
            if reading is not None:
                background_coverage[reading.sentence_index].update(membership_source_units(reading, f, ctx.reg))
            continue
        if (isinstance(f,Predication) and f.subject == scale.entity and f.polarity
                and ctx.reg.word_in_category(f.verb,'commercial_production_verb')
                and compatible_products(ctx.reg,[f.dobj]+[p.item for p in prices])):
            continue
        return decline("the sales account contains an additional event or incompatible context")
    expected=defaultdict(Counter)
    for t in terms:expected[t.provenance.sentence][t.value]+=1
    if (any(uncovered_units(r, background_coverage[r.sentence_index]) for r in ctx.premises)
            or uncovered_units(ctx.question, ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises,ctx.question),expected,missing='missing',duplicate='duplicate')):
        return decline("the sales account has unread amounts or conditions")
    subtotals=[evaluate('price * count',{'price':keyed_prices[k].value,'count':c.value},ctx.log,source='product-revenue')
               for k,c in keyed_counts.items()]
    prior=resource_residual(subtotals,[],ctx.log,source='prior-sales-revenue')
    value=evaluate('prior * factor',{'prior':prior,'factor':scale.value},ctx.log,source='current-sales-revenue')
    ctx.log.consumed_commercial_term_keys.update(t.key() for t in terms)
    node=SemanticNode('sales-revenue',(('entity',scale.entity),('period',scale.period)))
    detail=f'{prior:g} prior revenue × {scale.value:g} = {value:g}'
    return Answer('number',value,detail,proof=AnswerProof(node,(ProofStep('priced-sales-comparison',node,tuple(terms),detail),)))
