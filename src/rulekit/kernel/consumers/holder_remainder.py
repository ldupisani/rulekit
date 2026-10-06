"""An exhaustive population with a known prefix and one remaining member."""
from collections import Counter, defaultdict
from math import isfinite

from . import consumer
from ..answer import Answer, AnswerProof, ProofStep, SemanticNode
from ..evaluate import evaluate
from ..model import BatchEvidence, GroupTotal, Quantity
from ..numeric_evidence import audit_numeric_mentions
from ..resource_equations import resource_residual
from ..source_coverage import uncovered_units


def has_holder_prefix(store):
    """A question shape alone cannot imply a holder partition."""
    return any(row.kind in {"holder-share", "holder-subtotal"} for row in store.by_kind(BatchEvidence))


@consumer("holder-remainder", applicable=has_holder_prefix)
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    holder = ctx.match.slots.get("holder")
    if (holder is None or holder.features.get("owner") or holder.features.get("label")
            or tuple(holder.features.get("reference_qualifiers", ())) not in ((), (ctx.query["order"],))):
        return decline("the indexed holder cannot hide additional restrictions")
    rows = list(ctx.store.by_kind(BatchEvidence))
    shares = [r for r in rows if r.kind in {"holder-share", "holder-subtotal"}]
    populations = [r for r in rows if r.kind == "holder-population"]
    if not populations and shares:
        for q in ctx.store.by_kind(Quantity):
            if (q.measure != shares[0].entity or q.provenance.sentence >= shares[0].provenance.sentence
                    or q.owner or q.qualifier or q.label or q.measure_qualifier
                    or q.time or q.segment or q.occurrence
                    or not ctx.reg.word_in_category(q.verb, "possession_state")):
                continue
            reading = next((r for r in ctx.premises if r.sentence_index == q.provenance.sentence), None)
            if reading is None:
                continue
            preps = [u.features.get("fold", "") for u in reading.units
                     if ctx.reg.word_in_category(u.features.get("fold", ""), "spatial_location_preposition")]
            scope = f"{preps[0]} {q.entity}" if len(preps) == 1 else ""
            populations.append(BatchEvidence(q.provenance, "holder-population", q.measure,
                                              q.measure, q.value, 0, container=scope))
    totals = list(ctx.store.by_kind(GroupTotal))
    if (len(shares) != 1 or len(populations) != 1 or any(r.kind not in {"holder-population", "holder-share", "holder-subtotal"} for r in rows)
            or len(totals) != 1 or ctx.store.collisions or ctx.store.quarantined):
        return decline("one remaining holder needs one population, known prefix and total")
    population, share, total = populations[0], shares[0], totals[0]
    if (population.entity != share.entity or share.entity != ctx.query["entity"]
            or share.measure != total.measure or total.measure != ctx.query["item"]
            or ctx.reg.attrs.get(share.marker, {}).get("ordinal_index") != 1):
        return decline("the holder prefix and total need matching identities")
    reading = next(r for r in ctx.premises if r.sentence_index == share.provenance.sentence)
    source = next((u for u in reading.units if u.span[0] == share.position), None)
    if (source is None or source.features.get("owner") or source.features.get("label")
            or tuple(source.features.get("reference_qualifiers", ())) != (share.marker,)):
        return decline("the partition cannot hide additional holder restrictions")
    collective = share.kind == "holder-subtotal"
    amount = share.subtotal if collective else share.per_member
    values = (population.value, share.value, amount, total.value)
    if any(not isfinite(v) or v < 0 or not float(v).is_integer() for v in values):
        return decline("holder populations and contents must be whole nonnegative counts")
    if share.value < 1 or population.value - share.value != 1:
        return decline("the known prefix must leave exactly one holder")
    ordinal = ctx.reg.attrs.get(ctx.query.get("order", ""), {}).get("ordinal_index")
    if ordinal is not None and ordinal != population.value:
        return decline("the requested ordinal is not the remaining holder")
    if ordinal is None and not ctx.reg.word_in_category(ctx.query.get("order", ""), "holder_terminal_order"):
        return decline("the remaining holder is not identified")
    if total.scope and total.scope != population.container:
        return decline("population and total locations differ")
    expected = defaultdict(Counter)
    expected[population.provenance.sentence][population.value] += 1
    expected[share.provenance.sentence].update((share.value, amount))
    expected[total.provenance.sentence][total.value] += 1
    if audit_numeric_mentions((*ctx.premises, ctx.question), expected, missing="missing", duplicate="duplicate"):
        return decline("every count must belong to the same holder partition")
    if any(uncovered_units(r) for r in ctx.premises) or uncovered_units(ctx.question, ctx.match.consumed):
        return decline("the holder partition contains unread restrictions")
    known = amount if collective else evaluate(
        "count * amount", {"count": share.value, "amount": amount},
        ctx.log, source="uniform-holder-prefix")
    value = resource_residual([total.value], [known], ctx.log, source="remaining-holder")
    if value < 0:
        return decline("the known contents exceed the total")
    # Population cardinality participates in the exhaustive partition proof.
    evaluate("population - prefix", {"population": population.value, "prefix": share.value},
             ctx.log, source="single-remaining-holder")
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    node = SemanticNode("holder-remainder", (("entity", share.entity), ("measure", share.measure)))
    known_expression = f"{amount:g}" if collective else f"{share.value:g} × {amount:g}"
    detail = f"{total.value:g} − {known_expression} = {value:g}"
    return Answer("number", value, detail, proof=AnswerProof(node, (
        ProofStep("exhaustive-holder-partition", node, (population, share, total), detail),)))
