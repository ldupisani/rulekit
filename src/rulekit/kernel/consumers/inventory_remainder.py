"""Closed, subtype-scoped inventories with actor-anchored withdrawals."""

from collections import Counter, defaultdict
from math import isfinite

from . import consumer
from ..model import InventoryScope, InventoryWithdrawal, Quantity
from ..evaluate import evaluate
from ..source_coverage import uncovered_document_units
from ..numeric_evidence import audit_numeric_mentions
from ..resource_equations import resource_residual


@consumer("inventory-remainder")
def consume(ctx):
    from ..answer import Answer, AnswerProof, ProofStep, SemanticNode

    def decline(reason):
        return Answer("decline", None, reason)

    scopes = list(ctx.store.by_kind(InventoryScope))
    amounts = list(ctx.store.by_kind(Quantity))
    withdrawals = list(ctx.store.by_kind(InventoryWithdrawal))
    if len(scopes) != 1 or not amounts or not withdrawals:
        return decline("the remainder needs one enumerated inventory and explicit withdrawals")
    scope = scopes[0]
    if (scope.container != ctx.query["container"] or scope.item != ctx.query["item"]
            or scope.provenance.assumption):
        return decline("the ask must identify the asserted opening inventory")
    expected = defaultdict(Counter)
    opening = {}
    for q in amounts:
        bucket = (q.measure.split("[", 1)[0], q.measure_qualifier)
        if (q.entity != scope.container or bucket[0] != scope.item or not bucket[1]
                or q.owner or q.qualifier or q.label or bucket in opening
                or q.provenance.sentence != scope.provenance.sentence
                or q.provenance.assumption or not isfinite(q.value) or q.value < 0
                or not float(q.value).is_integer()):
            return decline("opening counts must uniquely enumerate this inventory's subtypes")
        opening[bucket] = q.value
        expected[q.provenance.sentence][q.value] += 1
    # A list mixing independent facets can overlap (size versus colour,
    # for example). Only one declared attribute family licenses this
    # bounded partition; mere adjective syntax is not disjointness evidence.
    families = [cat for cat in ctx.reg.attribute_compatibility
                if all(ctx.reg.word_in_category(qualifier, cat) for _, qualifier in opening)]
    if len(families) != 1:
        return decline("inventory subtypes need one shared declared attribute family")
    if uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed):
        return decline("the inventory has an unread event, condition, or location")
    removed = defaultdict(list)
    for event in withdrawals:
        bucket = (event.item, event.qualifier)
        if bucket not in opening or event.provenance.sentence <= scope.provenance.sentence:
            return decline("a withdrawal has no prior opening count for its exact subtype")
        if event.value is not None and event.factor is None:
            value = event.value
            expected[event.provenance.sentence][value] += 1
        elif event.factor is not None and event.value is None:
            anchors = [a for a in withdrawals if a.value is not None and a.factor is None
                       and (a.actor, a.item, a.qualifier) ==
                       (event.standard_actor, event.standard_item, event.standard_qualifier)
                       and a.provenance.sentence <= event.provenance.sentence]
            if len(anchors) != 1 or event.actor != event.standard_actor:
                return decline("a proportional removal needs one same-actor absolute reference")
            if not isfinite(event.factor) or event.factor < 0:
                return decline("a withdrawal factor must be finite and nonnegative")
            value = evaluate("factor * anchor", {"factor": event.factor, "anchor": anchors[0].value},
                             ctx.log, source="inventory-proportional-withdrawal")
            expected[event.provenance.sentence][event.factor] += 1
        else:
            return decline("a withdrawal must state either an amount or one proportional reference")
        if not isfinite(value) or value < 0 or not float(value).is_integer():
            return decline("enumerated item withdrawals must be nonnegative whole counts")
        removed[bucket].append(value)
    error = audit_numeric_mentions((*ctx.premises, ctx.question), expected,
                                   missing="a stated amount lies outside the inventory",
                                   duplicate="inventory evidence repeats a source amount")
    if error:
        return decline(error)
    remaining = {b: resource_residual([n], removed[b], ctx.log, source="inventory-subtype-remainder")
                 for b, n in opening.items()}
    if any(n < 0 for n in remaining.values()):
        return decline("withdrawals exceed an opening subtype count")
    total = resource_residual(list(remaining.values()), [], ctx.log, source="inventory-total-remainder")
    ctx.log.consumed_inventory_keys.update(f.key() for f in (scope, *withdrawals))
    node = SemanticNode("inventory-remainder", (("container", scope.container), ("item", scope.item)))
    detail = "; ".join(f"{qualifier}: {value:g} remaining" for (_, qualifier), value in remaining.items())
    return Answer("number", total, detail, proof=AnswerProof(node, (
        ProofStep("scoped-inventory-conservation", node, (scope, *amounts, *withdrawals), detail),)))
