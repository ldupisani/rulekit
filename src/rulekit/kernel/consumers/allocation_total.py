"""Total one exhaustively named allocation using ordinary relational receipts."""
from collections import Counter, defaultdict
from math import isfinite

from . import consumer
from ..answer import Answer, AnswerProof, ProofStep, SemanticNode
from ..model import AllocationGroup, Quantity, Relation
from ..numeric_evidence import audit_numeric_mentions
from ..source_coverage import quantity_source_units, uncovered_units
from ..totals import _combined_holder_totals
from ..evaluate import evaluate


@consumer("allocation-total", applicable=lambda store: any(store.by_kind(AllocationGroup)))
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)
    groups = list(ctx.store.by_kind(AllocationGroup))
    if len(groups) != 1 or ctx.store.collisions or ctx.store.quarantined:
        return decline("one unambiguous recipient group is required")
    group = groups[0]
    members = group.members
    if (len(members) < 2 or len(set(members)) != len(members)
            or group.value is not None and group.value != len(members) or group.source in members
            or group.resource != ctx.query["resource"]
            or ctx.query.get("source", group.source) != group.source
            or group.provenance.assumption):
        return decline("the counted named recipients must exhaust this allocation")
    amounts = list(ctx.store.by_kind(Quantity))
    relations = list(ctx.store.by_kind(Relation))
    units = {q.measure for q in amounts}
    if (len(units) != 1 or not amounts
            or not ctx.reg.word_in_category(next(iter(units)), "currency_measure")
            or any(q.entity not in members or not ctx.reg.word_in_category(q.verb, "acquire")
                   or q.owner or q.qualifier or q.measure_qualifier or q.label or q.time
                   or not isfinite(q.value) or q.value < 0
                   or q.provenance.sentence <= group.provenance.sentence for q in amounts)
            or any(r.subject not in members or r.standard not in members
                   or not ctx.reg.word_in_category(r.verb or "", "acquire")
                   or r.subject_owner or r.standard_owner or r.subject_label or r.standard_label
                   or r.measure_qualifier or r.standard_qualifier
                   or r.offset or r.subject_offset or r.standard_offset
                   or r.provenance.sentence <= group.provenance.sentence for r in relations)):
        return decline("only the recipients' compatible share receipts and comparisons can define the total")
    raw = [q for q in amounts if not q.provenance.source.startswith("synth/")]
    if len({q.entity for q in raw}) != len(raw):
        return decline("repeated receipts do not identify a single share per recipient")
    expected = defaultdict(Counter)
    if group.value is not None:
        expected[group.provenance.sentence][group.value] += 1
    for q in raw:
        expected[q.provenance.sentence][q.value] += 1
    for r in relations:
        expected[r.provenance.sentence][r.factor] += 1
    for reading in (*ctx.premises, ctx.question):
        covered = set(ctx.match.consumed if reading is ctx.question else ())
        for q in raw:
            covered.update(quantity_source_units(reading, q, ctx.reg))
        if uncovered_units(reading, covered):
            return decline("the allocation has an unread condition or transaction")
    if audit_numeric_mentions((*ctx.premises, ctx.question), expected, missing="missing", duplicate="duplicate"):
        return decline("the allocation does not account for every stated number exactly once")
    result = _combined_holder_totals(ctx.store, ctx.reg,
        {"holders": list(members), "measure": next(iter(units)), "holder_count": len(members)}, ctx.log)
    if isinstance(result, Answer):
        return result
    entities, totals = result
    value = evaluate(" + ".join(str(t) for t in totals), {}, ctx.log, source="named-allocation-total")
    ctx.log.consumed_component_keys.add(group.key())
    node = SemanticNode("allocation-total", (("source", group.source), ("resource", group.resource)))
    detail = f"Sum the allocated shares of {', '.join(entities)}: {value:g}."
    return Answer("number", value, detail, proof=AnswerProof(node, (
        ProofStep("named-recipient-sum", node, (group, *amounts, *relations), detail),)))
