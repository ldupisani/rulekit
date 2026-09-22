"""Shared query scope and candidate selection for forward/inverse rates.

Evidence fields extend saved review contracts without discarding the freshly
read activity, grammatical number, or nominal restrictions at execution time.
The consumers still own population, duration and completeness policy.
"""

from dataclasses import replace

from .model import Rate
from .predicate_compatibility import predicates_compatible


def normalize_rate_query(ctx):
    query = dict(ctx.query)
    for field in ("verb", "subject_number", "entity_owner", "entity_qualifier",
                  "measure_owner", "measure_qualifier"):
        if "evidence_" + field in query:
            query[field] = query["evidence_" + field]
    return replace(ctx, query=query)


def matching_rates(ctx, measure):
    """Exactly scoped activity candidates; ambiguity is never resolved here."""
    verb = ctx.query.get("verb")
    return [rate for rate in ctx.store.by_kind(Rate)
            if rate.entity == ctx.query["entity"]
            and (verb is None or predicates_compatible(rate.verb, verb, rate.measure, ctx.reg))
            and (rate.measure == measure or (
                measure in ctx.reg.category_parents
                and ctx.reg.word_in_category(rate.measure, measure)))]


def unsupported_rate_scope(query, *, allow_population_owner=False):
    """A flat class rate cannot supply an unstated nominal restriction."""
    if query.get("entity_qualifier"):
        return "the rate subject qualifier needs matching scoped evidence"
    if query.get("measure_qualifier") or query.get("measure_owner"):
        return "the rate object restriction needs matching scoped evidence"
    if query.get("entity_owner") and not allow_population_owner:
        return "the owned rate subject needs matching scoped evidence"
    return None


def collective_rate_subject(ctx, rate):
    """Retain a folded rate's explicitly plural grammatical subject.

    This reads the analyzer's bound subject, not raw text or a word list.
    Without that source evidence, an unresolved plural ask cannot assume
    that a rate for one member was stated collectively.
    """
    if rate.provenance.distributive:
        return False
    numbers = set()
    for reading in ctx.premises:
        if reading.sentence_index != rate.provenance.sentence:
            continue
        for unit in reading.units:
            if unit.sense() != "verb" or unit.features.get("lemma") != rate.verb:
                continue
            for obligation in unit.obligations():
                subject = obligation.target
                if (obligation.need == "subject" and hasattr(subject, "features")
                        and subject.features.get("lemma") == rate.entity):
                    numbers.add(subject.features.get("number"))
    return numbers == {"plural"}
