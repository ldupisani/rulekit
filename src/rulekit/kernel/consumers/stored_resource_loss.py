"""Ordered allocations of a received resource, followed by a scoped loss."""
from collections import Counter, defaultdict
from math import isfinite

from . import consumer
from ..answer import Answer
from ..evaluate import evaluate
from ..model import BatchEvidence, Quantity
from ..numeric_evidence import audit_numeric_mentions
from ..rate_calculation import convert_units
from ..resource_equations import resource_residual
from ..source_coverage import uncovered_document_units
from ..reference_identity import constrains


@consumer("stored-resource-loss", applicable=lambda s: any(
    r.kind == "resource-remainder-store" for r in s.by_kind(BatchEvidence)))
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)
    rows = sorted(ctx.store.by_kind(BatchEvidence), key=lambda r: (r.provenance.sentence, r.position))
    openings = [r for r in rows if r.kind == "resource-receipt"]
    receipts = list(ctx.store.by_kind(Quantity))
    if (not openings and len(receipts) == 1
            and receipts[0].entity == ctx.query["entity"]
            and ctx.reg.word_in_category(receipts[0].verb, "resource_receipt_verb")
            and ctx.reg.word_in_category(receipts[0].measure, "currency_measure")
            and not any((receipts[0].owner, receipts[0].qualifier,
                         receipts[0].measure_qualifier, receipts[0].time, receipts[0].label))):
        receipt = receipts[0]
        opening = BatchEvidence(receipt.provenance, "resource-receipt", receipt.entity,
                                receipt.measure, receipt.value, 0)
        openings = [opening]
        rows.insert(0, opening)
    locations = [r for r in rows if r.kind == "resource-remainder-store"]
    losses = [r for r in rows if r.kind == "resource-store-loss"]
    accesses = [r for r in rows if r.kind == "resource-store-access"]
    fractions = [r for r in rows if r.kind == "resource-fraction"]
    if (len(openings) != 1 or len(locations) != 1 or len(losses) != 1 or len(accesses) > 1
            or not fractions or len(rows) != 3 + len(fractions) + len(accesses) or len(ctx.store.facts) != len(rows)
            or ctx.store.collisions or ctx.store.quarantined):
        return decline("one received pool, ordered allocations and a uniquely located loss are required")
    opening, location, loss = openings[0], locations[0], losses[0]
    access = accesses[0] if accesses else None
    actor = ctx.query["entity"]
    if (opening.entity != actor or location.entity != actor or location.attribute != actor
            or access is not None and (access.entity != actor or access.container_ref != location.container_ref)
            or opening.provenance.sentence >= fractions[0].provenance.sentence
            or max(f.provenance.sentence for f in fractions) >= location.provenance.sentence
            or location.provenance.sentence >= loss.provenance.sentence
            or access is not None and loss.provenance.sentence != access.provenance.sentence
            or access is None and (loss.entity != actor or loss.container_ref != location.container_ref)
            or any(r.provenance.assumption for r in rows)
            or opening.measure != loss.measure):
        return decline("the pool, allocations, store owner and loss must share one ordered account")
    if any(not isfinite(r.value) or r.value < 0 for r in rows):
        return decline("resource amounts must be finite and nonnegative")
    expected = defaultdict(Counter)
    expected[opening.provenance.sentence][opening.value] += 1
    expected[loss.provenance.sentence][loss.value] += 1
    balance = opening.value
    for index, step in enumerate(fractions):
        anchors = [r for r in fractions if r.entity and r.provenance.sentence == step.provenance.sentence]
        owner = step.entity or (anchors[0].entity if len(anchors) == 1 else "")
        if (owner != actor or step.attribute and step.attribute != actor
                or not 0 <= step.value <= 1
                or step.marker == "remainder" and (
                    step.container_ref is None or location.container_ref is None
                    or constrains(step.container_ref, location.container_ref)
                    or constrains(location.container_ref, step.container_ref))
                or step.marker not in {"opening", "remainder"}
                or step.marker == "opening" and index != 0):
            return decline("each fraction must name the same pool or its current remainder")
        expected[step.provenance.sentence][step.value] += 1
        allocated = evaluate("base * fraction", {"base": balance, "fraction": step.value}, ctx.log, source="resource-allocation-fraction")
        balance = resource_residual([balance], [allocated], ctx.log, source="unallocated-resource-remainder")
    if (uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises, ctx.question), expected, missing="missing", duplicate="duplicate")):
        return decline("every receipt, allocation, storage and loss condition must be read")
    value = resource_residual([balance], [loss.value], ctx.log, source="stored-resource-loss")
    if value < 0:
        return decline("the surviving amount exceeds the stored balance")
    value = convert_units(value, opening.measure, ctx.query["measure"], ctx.reg, ctx.log, source="resource-loss-output-unit")
    if value is None:
        return decline("the requested currency does not match the received resource")
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    return Answer("number", value, "successive explicit allocations leave the stored remainder; loss equals that remainder minus the surviving money")
