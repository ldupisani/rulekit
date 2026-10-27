"""Recover uniform contents from a retained part and an exhaustive equal share."""
from collections import Counter, defaultdict
from math import isclose, isfinite

from . import consumer
from ..answer import Answer
from ..evaluate import evaluate
from ..model import BatchEvidence, Quantity
from ..numeric_evidence import audit_numeric_mentions
from ..resource_equations import resource_residual
from ..rate_calculation import convert_units
from ..source_coverage import uncovered_document_units, uncovered_units, quantity_source_units


@consumer("uniform-content-distribution", applicable=lambda s: any(
    r.kind in ("uniform-stock", "allocation-recipients") for r in s.by_kind(BatchEvidence)))
def consume(ctx):
    if ctx.query.get("mode") == "forward":
        return _forward_share(ctx)
    def decline(reason):
        return Answer("decline", None, reason)
    rows = list(ctx.store.by_kind(BatchEvidence))
    kinds = ("uniform-stock", "retained-count", "remainder-recipients", "recipient-share")
    if (len(rows) != 4 or any(sum(r.kind == k for r in rows) != 1 for k in kinds)
            or len(ctx.store.facts) != 4 or ctx.store.collisions or ctx.store.quarantined):
        return decline("one uniform stock, retained count and complete recipient distribution are required")
    stock, retained, recipients, share = (next(r for r in rows if r.kind == k) for k in kinds)
    recipient_ref, share_ref = recipients.container_ref, share.container_ref
    if (recipient_ref is not None and share_ref is not None
            and (recipient_ref.qualifiers != share_ref.qualifiers
                 or recipient_ref.label != share_ref.label
                 or recipient_ref.owner and share_ref.owner and recipient_ref.owner != share_ref.owner)):
        return decline("recipient descriptions must identify the same allocation group")
    if (any(r.measure != ctx.query["item"] for r in rows)
            or stock.container != ctx.query["unit"]
            or any(r.entity != stock.entity for r in (retained, recipients))
            or share.entity not in ("", stock.entity)
            or share.attribute not in ("", stock.entity)
            or recipients.container != share.container
            or recipients.attribute and recipients.attribute != stock.entity
            or stock.provenance.sentence >= retained.provenance.sentence
            or retained.provenance.sentence != recipients.provenance.sentence
            or share.provenance.sentence <= recipients.provenance.sentence
            or any(r.provenance.assumption for r in (stock, retained, recipients))):
        return decline("contents, owner, recipients and event order must identify one distribution")
    if any(not isfinite(r.value) or r.value < 0 or not float(r.value).is_integer() for r in rows) or stock.value <= 0 or recipients.value <= 0:
        return decline("containers, recipients and discrete contents require nonnegative whole counts")
    expected = defaultdict(Counter)
    for row in rows:
        expected[row.provenance.sentence][row.value] += 1
    if (uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises, ctx.question), expected, missing="missing", duplicate="duplicate")):
        return decline("all quantities and restrictions must belong to this distribution")
    distributed = evaluate("recipients * each", {"recipients": recipients.value, "each": share.value}, ctx.log, source="equal-distributed-total")
    total = resource_residual([retained.value, distributed], [], ctx.log, source="reconstructed-opening-stock")
    value = evaluate("total / containers", {"total": total, "containers": stock.value}, ctx.log, source="uniform-container-contents")
    if not isclose(value, round(value), abs_tol=1e-9):
        return decline("the reconstructed stock does not divide into whole equal contents")
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    return Answer("number", value, "retained amount plus recipients × each share, divided by equal containers")


def _forward_share(ctx):
    """Divide one explicitly transferred pool, with optional retention."""
    def decline(reason):
        return Answer("decline", None, reason)
    rows = list(ctx.store.by_kind(BatchEvidence))
    pools = [r for r in rows if r.kind == "allocation-pool"]
    holdings = list(ctx.store.by_kind(Quantity))
    # Ordinary possession remains ordinary Quantity evidence. It is adapted
    # only inside an explicit allocation query, never reclassified globally.
    if not pools and len(holdings) == 1:
        holding = holdings[0]
        if (not holding.is_state or holding.provenance.assumption
                or not ctx.reg.word_in_category(holding.verb, "possession_state")
                or not ctx.reg.word_in_category(holding.measure, "currency_measure")):
            return decline("an allocation needs one actual held pool")
        pool = BatchEvidence(provenance=holding.provenance, kind="allocation-pool",
                             entity=holding.entity, measure=holding.measure,
                             value=holding.value, position=-1, marker=holding.measure,
                             attribute="currency")
        pools = [pool]
        rows.append(pool)
    elif holdings:
        return decline("an allocation cannot also absorb unrelated holdings")
    groups = [r for r in rows if r.kind == "allocation-recipients"]
    retained = [r for r in rows if r.kind == "allocation-retained"]
    if (len(pools) != 1 or len(groups) != 1 or len(retained) > 1
            or len(rows) != 2 + len(retained) or len(ctx.store.facts) != len(rows)
            or ctx.store.collisions or ctx.store.quarantined
            or any(r.provenance.assumption for r in rows)):
        return decline("one complete actual allocation and recipient population are required")
    pool, group = pools[0], groups[0]
    if (pool.entity != group.entity or group.container != ctx.query.get("recipient")
            or group.measure not in ("", pool.measure)
            or pool.provenance.sentence > group.provenance.sentence
            or any(r.entity != pool.entity or r.measure != pool.measure
                   or r.attribute != pool.attribute
                   or not pool.provenance.sentence < r.provenance.sentence <= group.provenance.sentence
                   for r in retained)):
        return decline("the pool, retention and recipients must identify the same allocation")
    if (ctx.query.get("item") not in ("", pool.measure)
            or ctx.query.get("quantity") not in ("", pool.attribute)):
        return decline("the question requests a different resource or physical basis")
    if (any(not isfinite(r.value) or r.value < 0 for r in rows)
            or group.value <= 0 or not float(group.value).is_integer()
            or pool.attribute == "count" and any(not float(r.value).is_integer() for r in rows)):
        return decline("recipient counts and discrete resources must be whole; measured amounts must be finite")
    unit = ctx.query.get("unit") or pool.marker
    total = convert_units(pool.value, pool.marker, unit, ctx.reg, ctx.log, source="allocation-pool-unit")
    removed = [convert_units(r.value, r.marker, unit, ctx.reg, ctx.log,
                             source="allocation-retention-unit") for r in retained]
    if total is None or any(v is None for v in removed):
        return decline("the requested units must match the allocated quantity")
    expected = defaultdict(Counter)
    for row in rows:
        expected[row.provenance.sentence][row.value] += 1
    footprints = {r.provenance.sentence: quantity_source_units(
        ctx.premises[r.provenance.sentence], r, ctx.reg) for r in holdings}
    unread = any(uncovered_units(reading, footprints.get(reading.sentence_index, ()))
                 for reading in ctx.premises)
    if (unread or uncovered_units(ctx.question, ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises, ctx.question), expected,
                                      missing="missing", duplicate="duplicate")):
        return decline("all amounts and distribution conditions must be read")
    available = resource_residual([total], removed, ctx.log, source="allocated-remainder")
    if available < 0:
        return decline("the retained amount exceeds the pool")
    value = evaluate("available / recipients", {"available": available, "recipients": group.value},
                     ctx.log, source="uniform-recipient-share")
    if pool.attribute == "count" and not isclose(value, round(value), abs_tol=1e-9):
        return decline("the discrete pool does not divide into whole shares")
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    return Answer("number", value, f"the actual allocated remainder divided equally among recipients, in {unit}")
