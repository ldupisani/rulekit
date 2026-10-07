"""Residual length in a complete ordered route; no geometric assumptions."""
from collections import Counter, defaultdict
from math import isfinite

from . import consumer
from ..answer import Answer, AnswerProof, ProofStep, SemanticNode
from ..model import IndexedPathEvidence
from ..numeric_evidence import audit_numeric_mentions
from ..rate_calculation import convert_units
from ..resource_equations import resource_residual
from ..source_coverage import uncovered_document_units


def ordinal_index(value, reg):
    """Numeric ordinal tokens and declared lexical ordinals share one index."""
    try:
        index = float(value)
    except (TypeError, ValueError):
        index = reg.attrs.get(value, {}).get("ordinal_index")
    return int(index) if isinstance(index, (int, float)) and isfinite(index) and index > 0 and index == int(index) else None


@consumer("indexed-path", applicable=lambda store: any(store.by_kind(IndexedPathEvidence)))
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)
    rows = list(ctx.store.by_kind(IndexedPathEvidence))
    population = [r for r in rows if r.kind == "population"]
    totals = [r for r in rows if r.kind == "total"]
    terminals = [r for r in rows if r.kind == "terminal"]
    contexts = [r for r in rows if r.kind == "context"]
    gaps = [r for r in rows if r.kind == "gap"]
    legs = [r for r in rows if r.kind == "distance"]
    if (len(population) != 1 or len(totals) != 1 or len(terminals) != 1
            or len(contexts) > 1 or len(gaps) > 1 or not legs
            or ctx.store.collisions or ctx.store.quarantined):
        return decline("the route needs a checkpoint count, a total and an immediate terminal exit")
    pop, total, terminal = population[0], totals[0], terminals[0]
    count = ordinal_index(pop.value, ctx.reg)
    requested = ordinal_index(ctx.query["index"], ctx.reg)
    actor = pop.entity
    def same_actor(entity):
        return entity == actor or ctx.reg.word_in_category(entity, "path_singular_reference")
    if (not ctx.reg.word_in_category(actor, "path_vehicle")
            or not all(same_actor(r.entity) for r in rows)
            or not same_actor(ctx.query["entity"])
            or not count or count < 2 or not requested or requested >= count
            or total.route != pop.route
            or any(r.checkpoint and r.checkpoint != pop.checkpoint for r in rows)
            or ctx.query["checkpoint"] != pop.checkpoint
            or any(r.site and r.site != terminal.site for r in rows)
            or ordinal_index(terminal.index, ctx.reg) != count
            or any(ordinal_index(r.index, ctx.reg) != requested for r in gaps)
            or any(r.provenance.assumption and (r is not total or
                   r.provenance.sentence != ctx.question.sentence_index - 1) for r in rows)):
        return decline("the distances must describe one vehicle, route and complete indexed checkpoint sequence")
    indices = [ordinal_index(r.index, ctx.reg) for r in legs]
    # Cardinality plus range/uniqueness proves exhaustiveness without allocating
    # a range proportional to an arbitrary user-supplied checkpoint count.
    if (len(indices) != count - 2 or len(set(indices)) != len(indices)
            or any(i is None or not 1 <= i < count or i == requested for i in indices)
            or any(not isfinite(r.value) or r.value < 0 for r in (*legs, total))):
        return decline("every other traveled segment must have exactly one nonnegative distance")
    expected = defaultdict(Counter)
    for row in (pop, total, *legs):
        expected[row.provenance.sentence][row.value] += 1
    if (uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises, ctx.question), expected, missing="missing", duplicate="duplicate")):
        return decline("the route has an unread condition or an unaccounted distance")
    known = [convert_units(r.value, r.measure, total.measure, ctx.reg, ctx.log, source="indexed-route-unit") for r in legs]
    if any(v is None for v in known):
        return decline("the route distances need compatible length units")
    value = resource_residual([total.value], known, ctx.log, source="indexed-route-residual")
    if value < 0 or gaps and value <= 0:
        return decline("the remaining segment cannot satisfy the stated total and further travel")
    output_measure = ctx.query.get("measure", total.measure)
    value = convert_units(value, total.measure, output_measure, ctx.reg, ctx.log, source="indexed-route-output-unit")
    if value is None:
        return decline("the requested distance unit must be compatible with the route total")
    ctx.log.consumed_component_keys.update(r.key() for r in rows)
    node = SemanticNode("indexed-path-distance", (("entity", actor), ("index", str(requested)), ("measure", output_measure)))
    detail = f"Total {total.value:g} {total.measure}, less the other traveled segments; immediate exit adds zero: {value:g} {output_measure}."
    return Answer("number", value, detail, proof=AnswerProof(node, (
        ProofStep("complete-path-residual", node, tuple(rows), detail),)))
