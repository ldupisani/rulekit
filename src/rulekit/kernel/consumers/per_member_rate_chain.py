"""Explicit per-member requirements; never inferred population holdings."""

from collections import Counter
from math import isfinite, isclose

from . import ConsumerContext, consumer
from ..answer import Answer, AnswerAssumption, AnswerProof, ProofStep, SemanticNode
from ..evaluate import evaluate
from ..model import Quantity, Rate
from ..source_coverage import uncovered_document_units
from ..numeric_evidence import audit_numeric_mentions
from ..rate_calculation import apply_rate, convert_duration, rate_operands
from ..predicate_compatibility import predicates_compatible


@consumer("per-member-rate-chain")
def per_member_rate_chain(ctx: ConsumerContext):
    def decline(reason):
        return Answer("decline", None, reason)

    rates = ctx.store.by_kind(Rate)
    populations = ctx.store.by_kind(Quantity)
    individual = ctx.query.get("subject_number") == "singular"
    actor = ctx.query.get("entity")
    if (not rates or len(populations) > 1 or (not populations and not individual)
            or ctx.store.quarantined
            or any(not isinstance(f, (Rate, Quantity)) for f in ctx.store.facts)):
        return decline("a per-member chain needs explicit rates and one unambiguous population")
    if any(ctx.query.get(key) for key in (
            "entity_qualifier", "measure_qualifier", "measure_owner")):
        return decline("a class rate cannot resolve a restricted participant")
    population = populations[0] if populations else None
    owner = ctx.query.get("entity_owner")
    if owner and (individual or population is None or actor != population.measure
                  or owner != population.entity or population.owner or population.qualifier):
        return decline("the owned group must match the explicitly stated population holder")
    if population and (population.measure_qualifier or population.time is not None
            or population.provenance.distributive
            or not ctx.reg.word_in_category(population.verb, "possession_state")):
        return decline("the chain needs an unqualified population count, not a rate or dated event")
    for location in (ctx.query.get("location"), ctx.query.get("location2")):
        if location and (population is None or population.entity != location
                or (population.entity_ref and population.entity_ref.owner)
                or population.qualifier):
            return decline("the requested location does not identify the stated population")
    if any(not r.provenance.distributive for r in rates):
        return decline("every link must explicitly state a per-member rate")
    period = rates[0].per
    if any(r.per != period or not predicates_compatible(r.verb, ctx.query["verb"], r.measure, ctx.reg)
           for r in rates):
        return decline("every link and the ask must name a compatible activity and the same rate period")
    if ctx.query.get("period", period) != period:
        return decline("the periodic ask must name the same rate period")
    if any(not isfinite(v) or v < 0 or not float(v).is_integer()
           for v in [*(q.value for q in populations), *(r.value for r in rates)]):
        return decline("the population and per-period discrete counts must be nonnegative integers")

    # Validate the entire connected chain first, even when only a prefix is
    # requested. Downstream evidence is accounted for, not silently ignored.
    path, seen = [], set()
    current = population.measure if population else actor
    while True:
        if current in seen:
            return decline("the dependency chain is cyclic")
        seen.add(current)
        links = [r for r in rates if r.entity == current]
        if not links:
            break
        if len(links) != 1:
            return decline("each level needs exactly one outgoing rate; a link is ambiguous")
        path.append(links[0])
        current = links[0].measure
    if len(path) != len(rates):
        return decline("the chain contains disconnected or competing rates")
    endpoints = [i for i, r in enumerate(path)
                 if r.measure == ctx.query["measure"] and (not actor or r.entity == actor)]
    if len(endpoints) != 1:
        return decline("the requested participant and item must identify one chain edge")
    end = endpoints[0]
    selected = path[end:end + 1] if individual else path[:end + 1]

    expected = {}
    for fact, operands in [(q, (q.value,)) for q in populations] + [
            (r, rate_operands(r)) for r in rates]:
        expected.setdefault(fact.provenance.sentence, Counter()).update(operands)
    if "span_value" in ctx.query and "span" in ctx.match.slots:
        span = ctx.match.slots["span"]
        if "value" in span.features:
            expected.setdefault(ctx.question.sentence_index, Counter()).update([float(ctx.query["span_value"])])
    if audit_numeric_mentions((*ctx.premises, ctx.question), expected,
                              missing="missing", duplicate="duplicate"):
        return decline("the chain must account for every source-local numeric mention")
    if uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed):
        return decline("the chain contains an unread condition, event or restriction")

    value = 1.0 if individual else population.value
    interpretation = (
        "one individual's stated quota" if individual else
        f"closed dependency chain: each required member contributes its full {period} quota "
        "at the next level; intermediate counts are requirements, not inferred total populations"
    )
    steps = [ProofStep("individual-quota" if individual else "closed-chain-interpretation",
                       SemanticNode("population", (("measure", actor if individual else population.measure),
                                                    ("value", value))),
                       tuple(populations), interpretation)]
    for index, rate in enumerate(selected):
        previous = value
        value = apply_rate(rate, previous, ctx.log, source="per-member-rate-chain")
        if not isfinite(value) or not isclose(value, round(value), abs_tol=1e-8):
            return decline("the chain does not determine a finite discrete amount")
        steps.append(ProofStep(
            "per-member-period-quota",
            SemanticNode("required-count", (("measure", rate.measure), ("value", value))),
            (*populations, *selected[:index + 1]),
            f"{previous:g} {rate.entity} × {rate.value:g} {rate.measure} per member per {rate.per}",
        ))
    excluded = tuple(r for r in path if r not in selected)
    if excluded:
        steps.append(ProofStep("outside-requested-subgraph", SemanticNode("accounted-rates", ()),
                               excluded, "Connected rates outside the requested calculation were checked but not multiplied."))
    if "span_unit" in ctx.query:
        span = float(ctx.query["span_value"])
        periods = convert_duration(span, ctx.query["span_unit"], period, ctx.reg, ctx.log,
                                   source="chain-duration", allow_cadence=True)
        if (periods is None or not isfinite(periods) or periods < 0
                or not float(periods).is_integer()):
            return decline("the requested duration must contain a whole number of rate periods")
        value = evaluate(f"{value} * {periods}", {}, ctx.log, source="chain-span-total")
        if not isfinite(value):
            return decline("the requested total is not finite")
        steps.append(ProofStep("scale-complete-period-once", SemanticNode("span-total", (
            ("value", value), ("periods", periods))), tuple(selected),
            "Scale the complete per-period requirement once, not each dependency link."))
    proof = AnswerProof(SemanticNode("per-period-requirement", (
        ("measure", ctx.query["measure"]), ("period", period))), tuple(steps))
    return Answer("number", value, f"{value:g} {ctx.query['measure']}; interpreting {interpretation}.", proof=proof,
                  assumptions=() if individual else (AnswerAssumption("closed-quota-chain",
                      "Each required intermediate member supplies its full stated amount during the same period.",
                      tuple(sorted({r.provenance.sentence for r in selected}))),))
