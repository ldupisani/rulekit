"""Revenue from an explicitly priced product mix and a relative sales amount."""
from collections import Counter, defaultdict
from math import isfinite
from . import consumer
from .production_profit import compatible_products
from ..affine_graph import AffineError, AffineGraph
from ..answer import Answer, AnswerProof, ProofStep, SemanticNode
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..model import Atom, BatchEvidence, CommercialTerm, Membership, Predication, Price, Quantity, Relation, VerbalRelation
from ..numeric_evidence import audit_numeric_mentions
from ..pricing import consume_unit_quotes
from ..source_coverage import membership_source_units, quantity_ledger_source_units, uncovered_units
from ..evaluate import evaluate
from ..resource_equations import resource_residual


@consumer("sales-revenue")
def consume(ctx):
    if ctx.query.get("mode") == "difference":
        return _product_revenue_difference(ctx)
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
    def production_context(f):
        return (isinstance(f, Predication) and f.subject == scale.entity and f.polarity
                and ctx.reg.word_in_category(f.verb, 'commercial_production_verb')
                and compatible_products(ctx.reg, [f.dobj] + [p.item for p in prices]))

    # A location may elaborate an already licensed production/sale context.
    # It must not excuse a separate event, actor, or unread condition.
    context_sentences = {
        f.provenance.sentence for f in ctx.store.facts
        if production_context(f) and f.provenance.source != 'fold'
        and not f.provenance.assumption
    }
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
        if production_context(f):
            continue
        if (isinstance(f, VerbalRelation) and f.entity == scale.entity and f.polarity
                and f.role == 'spatial-location' and not f.provenance.assumption
                and f.provenance.sentence in context_sentences
                and ctx.reg.word_in_category(f.verb, 'sell')
                and ctx.reg.word_in_category(f.prep, 'quantity_site_preposition')
                and ctx.reg.word_in_category(f.obj, 'quantity_site_location')):
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


def _product_revenue_difference(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    quantities = list(ctx.store.by_kind(Quantity))
    counts = [q for q in quantities if q.provenance.source != "synth/relation"]
    comparisons = list(ctx.store.by_kind(Relation))
    quotes = list(ctx.store.by_kind(Price))
    purposes = list(ctx.store.by_kind(BatchEvidence))
    actors = {ctx.query_reference("entity"), ctx.query_reference("other")}
    item, qualifier = ctx.query["item"], ctx.query.get("qualifier") or ""
    if (len(actors) != 2 or not counts or len(quotes) != 1
            or any(actor is None or not actor.resolved for actor in actors)):
        return decline("revenue comparison needs two identified sellers, completed sales, and one price")
    quote = quotes[0]
    if (quote.item != item or (quote.qualifier or "") != qualifier or quote.per not in (None, item)
            or not ctx.reg.word_in_category(quote.measure or "", "currency_measure")
            or quote.provenance.assumption
            or any(q.entity_ref not in actors or q.measure != item
                   or (q.measure_qualifier or "") != qualifier or q.provenance.assumption
                   or not ctx.reg.word_in_category(q.verb, "sell") for q in counts)
            or len({q.entity_ref for q in counts}) != len(counts)
            or any(r.subject_ref not in actors or r.standard_ref not in actors
                   or r.measure != item or (r.measure_qualifier or "") != qualifier
                   or (r.standard_qualifier or qualifier) != qualifier or r.provenance.assumption
                   or not ctx.reg.word_in_category(r.verb, "sell") for r in comparisons)):
        return decline("the sale counts and unit price must refer to the same product")
    purpose = ctx.query_reference("purpose")
    if len(purposes) > 1 or (purpose is not None and not purposes) or any(
        row.kind != "sales-purpose" or set(row.members) != {actor.head for actor in actors}
        or row.measure != item or row.attribute != qualifier or row.provenance.assumption
        or purpose is not None and (row.container_ref is None
                                    or row.container_ref.head != purpose.head
                                    or row.container_ref.qualifiers != purpose.qualifiers)
        for row in purposes
    ):
        return decline("the stated sales purpose must match the sellers and product")
    covered = {}
    for row in counts:
        if row.provenance.source == "fold":
            reading = next(r for r in ctx.premises if r.sentence_index == row.provenance.sentence)
            covered[reading.sentence_index] = quantity_ledger_source_units(reading, [row], ctx.reg)
    rows = [*quantities, *comparisons, quote, *purposes]
    operands = [(q, [q.value]) for q in counts] + [(quote, [quote.value])]
    operands.extend((r, [r.factor] if r.offset == 0 else [abs(r.offset)]) for r in comparisons)
    if not closed_evidence(ctx, rows, operands, covered=covered):
        return decline("every sale, comparison and pricing condition must be read")
    try:
        graph = AffineGraph(
            [(q.entity_ref, q.value) for q in counts],
            [(r.subject_ref, r.standard_ref, r.factor, r.offset) for r in comparisons], ctx.log,
        )
        first, second = (graph.value(ctx.query_reference(role)) for role in ("entity", "other"))
    except AffineError as error:
        return decline(str(error))
    if any(q.entity_ref not in actors or q.measure != item or (q.measure_qualifier or "") != qualifier
           or q.value != (first if q.entity_ref == ctx.query_reference("entity") else second)
           for q in quantities if q.provenance.source == "synth/relation"):
        return decline("derived sales counts must agree with the complete comparison")
    if any(value < 0 or not isfinite(value) or not float(value).is_integer() for value in (first, second)):
        return decline("sales must be nonnegative whole counts")
    sign = -1 if ctx.reg.word_in_category(ctx.query["direction"], "less_dir") else 1
    value = evaluate("(first - second) * price * sign",
                     dict(first=first, second=second, price=quote.value, sign=sign),
                     ctx.log, source="same-product-revenue-difference")
    if value < 0:
        return decline("the stated comparison direction contradicts the revenue")
    consume_unit_quotes(quotes, ctx.log)
    return finish_batch_answer(ctx, rows, value, "multiply the difference in sales counts by the common unit price")
