"""A complete ordered partition, with a separate event fraction per batch."""

from collections import Counter, defaultdict
from math import isclose, isfinite

from . import consumer
from ..answer import Answer, AnswerProof, ProofStep, SemanticNode
from ..evaluate import evaluate
from ..model import BatchEvidence, Quantity
from ..numeric_evidence import audit_numeric_mentions
from ..resource_equations import resource_residual
from ..source_coverage import uncovered_units


@consumer("batch-outcomes")
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = sorted(ctx.store.by_kind(BatchEvidence), key=lambda f: (f.provenance.sentence, f.position))
    shares = [r for r in rows if r.kind == "share"]
    openings = [r for r in rows if r.kind == "population"]
    if not shares or ctx.store.collisions or ctx.store.quarantined:
        return decline("batch outcomes need unambiguous ordered shares")
    # Ordinary asserted ownership can supply the same opening count. Loading
    # does not become ownership merely to reuse this path.
    quantities = [q for q in ctx.store.by_kind(Quantity)
                  if q.provenance.sentence < shares[0].provenance.sentence]
    if not openings:
        openings = [q for q in quantities if q.entity == ctx.query["entity"]
                    and (ctx.reg.word_in_category(q.verb, "possession_state")
                         or ctx.reg.word_in_category(q.verb, "initial_state_verb"))]
    if len(openings) != 1:
        return decline("batch outcomes need one explicit opening population")
    opening = openings[0]
    measure = opening.measure
    if isinstance(opening, Quantity) and (opening.measure_qualifier or opening.owner or opening.qualifier or opening.label):
        return decline("a qualified opening needs an exact batch identity")
    if isinstance(opening, Quantity):
        reading = next((r for r in ctx.premises if r.sentence_index == opening.provenance.sentence), None)
        units = [u for u in reading.units if u.features.get("value_kind") == "count"
                 and u.features.get("value") == opening.value
                 and u.features.get("lemma") == measure] if reading else []
        if len(units) != 1 or any(units[0].features.get(k) for k in ("owner", "label", "reference_qualifiers")):
            return decline("the opening count needs one unqualified source collection")
    entity = ctx.query["entity"]
    if opening.entity != entity or opening.provenance.sentence >= shares[0].provenance.sentence:
        return decline("the population must precede this participant's batches")

    def same_collection(item):
        # A bare superclass may abbreviate this one explicit subtype, never
        # substitute a sibling or a narrower subtype for a mixed population.
        return item == measure or ctx.reg.word_in_category(measure, item)

    if not same_collection(ctx.query["item"]):
        return decline("the ask does not identify the opening collection")
    reference = ctx.query.get("evidence_entity_reference")
    if reference and (reference.get("head") != entity or not reference.get("resolved")
                      or any(reference.get(k) for k in ("owner", "label", "qualifiers"))):
        return decline("the asked participant needs the same unqualified batch identity")
    if any(value for key, value in ctx.query.items()
           if key not in {"consumer", "entity", "measure", "item", "verb", "mode",
                          "sum_measure_variants", "evidence_entity_reference"}):
        return decline("an additionally qualified ask needs exact batch-scope evidence")
    for row in rows:
        reading = next((r for r in ctx.premises if r.sentence_index == row.provenance.sentence), None)
        unit = next((u for u in reading.units if u.span[0] == row.position), None) if reading else None
        if (unit is None or unit.features.get("owner") or unit.features.get("label")
                or tuple(unit.features.get("reference_qualifiers", ())) != ((row.marker,) if row.kind == "share" else ())):
            return decline("batch labels cannot hide another subtype or ownership restriction")
    expected = defaultdict(Counter)
    expected[opening.provenance.sentence][opening.value] += 1
    selected = []
    for index, row in enumerate(shares):
        advance = ctx.reg.attrs.get(row.marker, {}).get("batch_advance")
        if advance != (0 if index == 0 else 1):
            return decline("disjoint batches need one first batch followed only by next batches")
        if row.entity != entity or not same_collection(row.measure) or row.verb != ctx.query["verb"]:
            return decline("every batch must describe the same participant, collection and event")
        if row.provenance.assumption or not (isfinite(row.value) and row.value > 0 and float(row.value).is_integer()
                                           and isfinite(row.fraction) and 0 <= row.fraction <= 1):
            return decline("batch shares must be asserted finite counts and fractions within one whole")
        expected[row.provenance.sentence].update((row.value, row.fraction))
        value = evaluate("population * fraction", {"population": row.value, "fraction": row.fraction},
                         ctx.log, source="batch-selected-count")
        if not isfinite(value) or not isclose(value, round(value), rel_tol=0, abs_tol=1e-8):
            return decline("a batch outcome must count whole objects, not round fractional objects")
        selected.append(value)
    if (opening.provenance.assumption or not isfinite(opening.value) or opening.value <= 0
            or not float(opening.value).is_integer()
            or resource_residual([opening.value], [s.value for s in shares], ctx.log,
                                 source="batch-population-coverage") != 0):
        return decline("the disjoint batches must exactly exhaust the opening population")
    if audit_numeric_mentions((*ctx.premises, ctx.question), expected, missing="missing", duplicate="duplicate"):
        return decline("every numeric mention must belong to the population or a batch share")
    # Earlier nonnumeric introductions can establish the participant. Once
    # the collection starts, no unread event/condition may silently vanish.
    for reading in ctx.premises:
        if reading.sentence_index >= opening.provenance.sentence and uncovered_units(reading):
            return decline("the batch interval contains an unread event or condition")
    if uncovered_units(ctx.question, ctx.match.consumed):
        return decline("the batch question contains an unread restriction")
    value = resource_residual([opening.value], selected, ctx.log, source="batch-outcome-complement") \
        if ctx.query["mode"] == "complement" else resource_residual(selected, [], ctx.log, source="batch-outcome-total")
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    node = SemanticNode("batch-outcomes", (("entity", entity), ("measure", measure), ("mode", ctx.query["mode"])))
    detail = "; ".join(f"{r.value:g} × {r.fraction:g} = {v:g}" for r, v in zip(shares, selected))
    return Answer("number", value, f"{value:g} {measure}; {detail}", proof=AnswerProof(node, (
        ProofStep("exhaustive-disjoint-batches", node, (opening, *shares), detail),)))
