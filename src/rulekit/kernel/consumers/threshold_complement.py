"""A strict threshold and its inclusive opposite partition one population."""
from collections import Counter, defaultdict
from math import isfinite, isclose

from . import consumer
from ..answer import Answer
from ..evaluate import evaluate
from ..model import PopulationEvidence, Quantity
from ..numeric_evidence import audit_numeric_mentions
from ..source_coverage import uncovered_document_units


@consumer('threshold-complement', applicable=lambda s: bool(s.by_kind(PopulationEvidence)))
def consume(ctx):
    def decline(reason):
        return Answer('decline', None, reason)

    rows = list(ctx.store.by_kind(PopulationEvidence))
    shares = [r for r in rows if r.kind == 'share']
    totals = [r for r in rows if r.kind == 'population']
    # An unindexed population reuses ordinary ownership evidence. An indexed
    # share must still have an explicitly matching indexed total.
    if len(shares) == 1 and not shares[0].scope and not totals:
        quantities = list(ctx.store.by_kind(Quantity))
        if len(quantities) != 1:
            return decline('one explicit unindexed population count is required')
        quantity = quantities[0]
        if (not ctx.reg.word_in_category(quantity.verb, 'possession_state')
                or quantity.occurrence is not None or quantity.time is not None
                or quantity.owner or quantity.qualifier or quantity.measure_qualifier or quantity.label
                or quantity.entity_ref is None or not quantity.entity_ref.resolved
                or quantity.entity_ref.described):
            return decline('the unindexed population needs an unqualified ownership count')
        totals = [PopulationEvidence(kind='population', position=-1,
                                     entity=quantity.entity, member=quantity.measure,
                                     value=quantity.value, provenance=quantity.provenance)]
    if (len(shares) != 1 or len(totals) != 1
            or any(r.kind not in {'share', 'population'} for r in rows)
            or ctx.store.collisions or ctx.store.quarantined):
        return decline('one threshold share and one scoped population are required')
    share, total = shares[0], totals[0]
    numeric = share.boundary_value is not None
    requested_numeric = ctx.query.get('boundary_value')
    if (numeric != (requested_numeric is not None)
            or numeric and (not isfinite(share.boundary_value)
                            or share.boundary_value != float(requested_numeric))
            or not numeric and share.boundary_label != ctx.query.get('boundary_label')):
        return decline('the query must preserve the exact numeric or categorical boundary')
    if (total.scope != share.scope or not share.entity or total.entity != share.entity
            or total.member != share.member or ctx.query['member'] != total.member
            or ('owner' in ctx.match.slots and not ctx.query.get('entity'))
            or (ctx.query.get('entity') and ctx.query['entity'] != total.entity)
            or ctx.query['assessment'] != share.assessment or share.provenance.assumption
            or not all(isfinite(v) for v in (share.value, total.value))
            or not 0 <= share.value <= 1 or total.value < 0
            or not float(total.value).is_integer()):
        return decline('the collection, assessment, member type and population owner must match')
    lower = lambda op: ctx.reg.word_in_category(op, 'threshold_lower')
    upper = lambda op: ctx.reg.word_in_category(op, 'threshold_upper')
    same = (lower(share.operator) and lower(ctx.query['operator'])
            or upper(share.operator) and upper(ctx.query['operator']))
    opposite = (lower(share.operator) and upper(ctx.query['operator'])
                or upper(share.operator) and lower(ctx.query['operator']))
    inclusive = ctx.query['inclusive'] == 'true'
    if not (same and not inclusive or opposite and inclusive):
        return decline('only an identical strict threshold or its inclusive opposite is determined')
    expected = defaultdict(Counter)
    expected[share.provenance.sentence][share.value] += 1
    expected[total.provenance.sentence][total.value] += 1
    if numeric:
        expected[share.provenance.sentence][share.boundary_value] += 1
        expected[ctx.question.sentence_index][float(requested_numeric)] += 1
    if (uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises, ctx.question), expected,
                                      missing='missing', duplicate='duplicate')):
        return decline('the threshold partition must account for all source content')
    value = evaluate('n * (1 - f)' if opposite else 'n * f',
                     {'n': total.value, 'f': share.value}, ctx.log,
                     source='threshold-population-partition')
    if not isclose(value, round(value), abs_tol=1e-8):
        return decline('the share does not describe whole population members')
    ctx.log.consumed_component_keys.update(r.key() for r in rows)
    return Answer('number', value, 'Count the stated strict threshold or its exact inclusive complement.')
