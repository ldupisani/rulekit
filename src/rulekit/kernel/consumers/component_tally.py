"""Explicit numerical tallies of labeled measurements, never unit conversion."""
from collections import Counter, defaultdict
from math import isfinite

from . import consumer
from ..answer import Answer, AnswerProof, ProofStep, SemanticNode
from ..model import MeasuredComponent
from ..evaluate import evaluate
from ..affine_graph import dependency_graph, AffineError
from ..numeric_evidence import audit_numeric_mentions
from ..source_coverage import uncovered_document_units


@consumer("component-tally", applicable=lambda store: any(store.by_kind(MeasuredComponent)))
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)
    rows = list(ctx.store.by_kind(MeasuredComponent))
    entities = {r.entity for r in rows}
    products = {r.product for r in rows if r.product}
    requested = list(zip(ctx.query["components"], ctx.query["measures"]))
    keyed = {(r.component, r.measure): r for r in rows}
    if (len(entities) != 1 or len(products) > 1 or not rows
            or ctx.query.get("entity", next(iter(entities))) not in entities
            or ctx.query.get("product") and products and ctx.query["product"] not in products
            or len(keyed) != len(rows) or len(requested) != len(set(requested))
            or set(requested) != set(keyed) or ctx.store.collisions or ctx.store.quarantined
            or any(r.provenance.assumption or not isfinite(r.value) or r.value < 0 for r in rows)):
        return decline("the tally must identify each distinct measured component of one participant exactly once")
    expected = defaultdict(Counter)
    for r in rows:
        expected[r.provenance.sentence][r.value] += 1
    if (uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises, ctx.question), expected, missing="missing", duplicate="duplicate")):
        return decline("the component tally has unread conditions or unaccounted amounts")
    scope = (next(iter(entities)), next(iter(products), ""))
    node = lambda key: (scope, *key)
    anchors = [(node(key), row.value) for key, row in keyed.items() if not row.reference]
    links = [(node(key), node((row.reference, row.reference_measure)), row.value, 0)
             for key, row in keyed.items() if row.reference]
    try:
        graph = dependency_graph(anchors, links, ctx.log)
        resolved = {key: graph.value(node(key)) for key in keyed}
    except AffineError:
        return decline("component dependencies must be anchored and acyclic with matching unit labels")
    value = evaluate(" + ".join(str(resolved[key]) for key in requested), {}, ctx.log, source="explicit-component-count-tally")
    ctx.log.consumed_component_keys.update(r.key() for r in rows)
    node = SemanticNode("component-count-tally", (("entity", next(iter(entities))),))
    detail = "; ".join(f"{resolved[k]:g} {k[1]} of {k[0]}" for k in requested)
    detail += f". Explicit numerical tally: {value:g}; this is not a converted physical quantity."
    return Answer("number", value, detail, proof=AnswerProof(node, (
        ProofStep("labeled-component-count-sum", node, tuple(rows), detail),)))
