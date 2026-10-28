"""Weight per-member average rates by disjoint population shares."""
from collections import Counter, defaultdict
from math import isclose, isfinite

from . import consumer
from ..answer import Answer
from ..evaluate import evaluate
from ..model import BatchEvidence
from ..numeric_evidence import audit_numeric_mentions
from ..predicate_compatibility import predicates_compatible
from ..rate_calculation import convert_duration, convert_units
from ..reference_bindings import anaphoric_forms_agree
from ..reference_identity import constrains, reference_from_unit
from ..source_coverage import uncovered_document_units


@consumer('population-rate-total', applicable=lambda s: any(
    r.kind == 'population-rate-share' for r in s.by_kind(BatchEvidence)))
def consume(ctx):
    def decline(reason):
        return Answer('decline', None, reason)
    rows = list(ctx.store.by_kind(BatchEvidence))
    contexts = [r for r in rows if r.kind == 'population-rate-inquiry']
    sources = [r for r in rows if r.kind == 'population-rate-attribution']
    counts = [r for r in rows if r.kind == 'population-rate-count']
    shares = [r for r in rows if r.kind == 'population-rate-share']
    rests = [r for r in rows if r.kind == 'population-rate-rest']
    if (len(contexts) > 1 or len(sources) > 1 or len(counts) != 1 or len(shares) != 1 or len(rests) != 1
            or len(rows) != len(ctx.store.facts)
            or len(rows) != len(contexts) + len(sources) + len(counts) + len(shares) + len(rests)
            or ctx.store.collisions or ctx.store.quarantined):
        return decline('one observed population and exhaustive subgroup average rates are required')
    count = counts[0]
    population_ref = contexts[0].container_ref if contexts else count.container_ref
    observer_ref = contexts[0].entity_ref if contexts else count.entity_ref
    query_population = reference_from_unit(ctx.match.slots['population'])
    forms = [r.acquisition for r in (*sources, count)
             if getattr(ctx.reg.lexicon.get(r.acquisition.casefold()), 'anaphoric_form', None)]
    if (population_ref is None or count.container_ref is None or not constrains(count.container_ref, population_ref)
            or not constrains(query_population, population_ref)
            or observer_ref is None or count.entity_ref is None or not constrains(count.entity_ref, observer_ref)
            or forms and not anaphoric_forms_agree(forms, 'singular', ctx.reg)
            or count.value <= 0 or not float(count.value).is_integer()
            or count.measure != ctx.query['member'] or count.value != float(ctx.query['population'])
            or count.provenance.assumption and count.provenance.sentence != ctx.question.sentence_index - 1
            or any(s.entity_ref is None or not constrains(s.entity_ref, observer_ref) for s in sources)
            or any(r.provenance.assumption for r in rows if r is not count)):
        return decline('the observer, population count and requested population must agree')
    expected = defaultdict(Counter)
    expected[count.provenance.sentence][count.value] += 1
    expected[ctx.question.sentence_index][float(ctx.query['population'])] += 1
    unit = shares[0].measure
    total_share = 0
    weighted = []
    for row in (*shares, *rests):
        if (not isfinite(row.value) or row.value < 0 or row.measure != unit
                or row in shares and (row.entity_ref is None or not constrains(row.entity_ref, population_ref)
                                     or not isfinite(row.fraction) or not 0 < row.fraction < 1)
                or contexts and row.container and row.container != contexts[0].measure):
            return decline('subgroup rates must describe the same population and measured attribute')
        if row in shares:
            total_share += row.fraction
            expected[row.provenance.sentence][row.fraction] += 1
            share = row.fraction
        else:
            if row.provenance.sentence != shares[-1].provenance.sentence or row.position <= shares[-1].position:
                return decline('the complementary group must follow its explicit same-population share')
            share = evaluate('1 - assigned', {'assigned': total_share}, ctx.log, source='unassigned-population-share')
        expected[row.provenance.sentence][row.value] += 1
        if total_share > 1 or share < 0:
            return decline('population shares cannot exceed the whole')
        members = evaluate('population * share', {'population': count.value, 'share': share},
                           ctx.log, source='subgroup-member-count')
        if not isclose(members, round(members), rel_tol=0, abs_tol=1e-8):
            return decline('the subgroup shares must describe whole population members')
        periods = convert_duration(1, ctx.query['period'], row.marker, ctx.reg, ctx.log,
                                   source='population-rate-period')
        if periods is None:
            return decline('the observation and requested elapsed periods must be compatible')
        if contexts and contexts[0].marker:
            if not predicates_compatible(contexts[0].marker, row.marker, row.marker, ctx.reg):
                return decline('the stated observation frequency must agree with the reported rates')
        weighted.append(evaluate('members * rate * periods',
                                 {'members': members, 'rate': row.value, 'periods': periods},
                                 ctx.log, source='subgroup-period-total'))
    if (uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises, ctx.question), expected, missing='missing', duplicate='duplicate')):
        return decline('every reported rate, population and observation condition must be read')
    value = evaluate(' + '.join(str(v) for v in weighted), {}, ctx.log, source='population-period-total')
    if ctx.reg.word_in_category(ctx.query['measure'], 'currency_measure'):
        value = convert_units(value, unit, ctx.query['measure'], ctx.reg, ctx.log, source='population-total-unit')
        if value is None:
            return decline('the requested monetary unit is incompatible with the observed rates')
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    return Answer('number', value, 'sum each disjoint subgroup population multiplied by its per-member average rate')
