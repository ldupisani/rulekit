"""Local batch fractions over opening-stock partitions or independent acquisitions."""

from collections import Counter, defaultdict
from math import isclose, isfinite

from . import consumer
from ..answer import Answer, AnswerProof, ProofStep, SemanticNode
from ..evaluate import evaluate
from ..model import BatchEvidence, Quantity
from ..numeric_evidence import audit_numeric_mentions
from ..resource_equations import resource_residual
from ..source_coverage import uncovered_units


ACQUIRED_BATCH_KINDS = frozenset({"acquisition", "acquired-discard", "acquired-classify", "batch-discard", "batch-classify"})


@consumer("batch-outcomes")
def consume(ctx):
    if ctx.query.get("scope") == "acquired":
        return _acquired_batches(ctx)
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


def _acquired_batches(ctx):
    """Independent acquisitions, each with its own local selection evidence.

    Classification alone never removes stock. An explicit question-local
    removal can complete a classified batch, with item, actor, quality and
    ordinal checked against that batch rather than the accumulated balance.
    """
    def decline(reason):
        return Answer("decline", None, reason)

    def quality(word):
        categories = [c for c in ctx.reg.word_categories.get(word, ())
                      if "batch_quality" in ctx.reg.cat_ancestors(c)
                      and c in ctx.reg.category_antonyms]
        if len(categories) != 1:
            return None
        category = categories[0]
        return (frozenset((category, ctx.reg.category_antonyms[category])),
                ctx.reg.category_polarity.get(category))

    rows = list(ctx.store.by_kind(BatchEvidence))
    # Standalone acquisitions remain ordinary quantities for ratios, discourse
    # groups and balance consumers. Normalize them locally only when answering
    # a batch question; do not impose batch accounting on unrelated questions.
    occupied = {r.provenance.sentence for r in rows}
    quantities = [q for q in ctx.store.by_kind(Quantity)
                  if q.provenance.sentence not in occupied
                  and ctx.reg.word_in_category(q.verb, "batch_acquisition_verb")]
    if any(q.owner or q.qualifier or q.label or q.measure_qualifier or q.time
           or q.segment or q.provenance.source.startswith("synth/") for q in quantities):
        return decline("an acquisition needs explicit unqualified source identity")
    rows.extend(BatchEvidence(q.provenance, "acquisition", q.entity, q.measure,
                              q.value, 0, acquisition=q.verb) for q in quantities)
    rows.sort(key=lambda r: (r.provenance.sentence, r.position))
    if not rows or ctx.store.collisions or ctx.store.quarantined:
        return decline("acquired batches need unambiguous evidence")
    if any(r.kind not in ACQUIRED_BATCH_KINDS or r.provenance.assumption for r in rows):
        return decline("acquired batches cannot be mixed with an opening-stock partition or assumption")
    entity, measure = rows[0].entity, rows[0].measure
    if (not entity or not measure or ctx.query.get("entity", entity) != entity
            or ctx.query.get("item") != measure or any(r.entity != entity for r in rows)):
        return decline("all acquired batches must identify the same participant and item")
    # Explicit objects are checked by the grammar. Pronoun disposal and
    # question-local completion need the same frames after item resolution.
    def accepts_item(verb):
        if not verb:
            return True
        frames = [(category, frame) for category, frame in ctx.reg.selectional_frames(verb)
                  if any(root in ctx.reg.cat_ancestors(category)
                         for root in ("batch_acquisition_verb", "batch_disposal_verb"))]
        return any("theme" in frame and ctx.reg.word_in_category(measure, frame["theme"])
                   for _, frame in frames)

    if any(not accepts_item(verb) for row in rows
           for verb in (row.acquisition, row.verb)) or not accepts_item(
               ctx.query.get("completion_disposal")):
        return decline("the acquisition or disposal verb does not accept this item type")
    expected = defaultdict(Counter)
    batches = []
    for row in rows:
        if row.kind in {"batch-discard", "batch-classify"}:
            if (not batches or batches[-1][1] is not None
                    or row.provenance.sentence != batches[-1][0].provenance.sentence + 1):
                return decline("a standalone fraction needs the immediately preceding unclassified acquisition")
            batches[-1][1] = row
            expected[row.provenance.sentence][row.fraction] += 1
            continue
        if (row.measure != measure or not isfinite(row.value) or row.value <= 0
                or not float(row.value).is_integer()):
            return decline("each acquisition needs a positive whole count of the same item")
        expected[row.provenance.sentence][row.value] += 1
        outcome = None if row.kind == "acquisition" else row
        if outcome:
            expected[row.provenance.sentence][row.fraction] += 1
        batches.append([row, outcome])
    if not batches:
        return decline("batch outcomes need an acquisition")
    if audit_numeric_mentions((*ctx.premises, ctx.question), expected, missing="missing", duplicate="duplicate"):
        return decline("every numeric mention must belong to an acquisition or its outcome")
    for reading in ctx.premises:
        if reading.sentence_index >= rows[0].provenance.sentence and uncovered_units(reading):
            return decline("the acquired-batch interval contains an unread event or restriction")
    unread = uncovered_units(ctx.question, ctx.match.consumed)
    # The shared possession ask leaves a trailing remainder adjective outside
    # its match. Admit only that exact suffix; other time/scope changes remain unread.
    if (len(unread) == 1 and ctx.reg.word_in_category(ctx.query.get("verb", ""), "possession_state")
            and unread[0] is next((u for u in reversed(ctx.question.units) if u.sense() != "punct"), None)
            and ctx.reg.word_in_category(unread[0].features.get("lemma", ""), "remnant_adj")):
        unread = ()
    if unread:
        return decline("the acquired-batch question contains an unread restriction")
    if any(ctx.query.get(k) for k in ("measure_qualifier", "owner", "qualifier", "label", "time")):
        return decline("an additionally qualified balance needs exact batch identity")

    asked_quality = quality(ctx.query["attribute"]) if ctx.query.get("attribute") else None
    if ctx.query.get("attribute") and asked_quality is None:
        return decline("the requested quality is not a declared batch classification")
    completion = ctx.query.get("completion_attribute")
    completion_index = None
    if completion:
        if (ctx.query.get("completion_item") != measure
                or ctx.query.get("completion_entity", entity) != entity):
            return decline("the question-local removal identifies a different actor or item")
        index = ctx.reg.attrs.get(ctx.query.get("completion_round", ""), {}).get("batch_index")
        if ctx.query.get("completion_round") and index is None:
            return decline("the requested round is not identified")
        if index is None and sum(outcome is not None and outcome.kind in {"acquired-classify", "batch-classify"}
                                 for _, outcome in batches) != 1:
            return decline("an unnumbered removal needs one unambiguous classified batch")
        completion_index = len(batches) - 1 if index in (None, -1) else int(index) - 1
        if not 0 <= completion_index < len(batches):
            return decline("the requested round does not exist")
        acquired, outcome = batches[completion_index]
        if ctx.query.get("completion_acquisition", acquired.acquisition) != acquired.acquisition:
            return decline("the question refers to a different acquisition event")
        if outcome is None or outcome.kind not in {"acquired-classify", "batch-classify"}:
            return decline("question-local removal needs a classified, not already disposed, batch")

    selected = []
    details = []
    for index, (acquired, outcome) in enumerate(batches):
        # An asserted acquisition with no selection retains its whole count.
        # It cannot answer a quality-specific question without classification.
        outcome = outcome or acquired
        if not isfinite(outcome.fraction) or not 0 <= outcome.fraction <= 1:
            return decline("batch outcome fractions must lie within one whole")
        affected = evaluate("population * fraction", {"population": acquired.value, "fraction": outcome.fraction},
                            ctx.log, source="batch-selected-count")
        if not isfinite(affected) or not isclose(affected, round(affected), rel_tol=0, abs_tol=1e-8):
            return decline("batch outcomes must count whole objects")
        classified = quality(outcome.attribute) if outcome.attribute else None
        if outcome.attribute and (classified is None or outcome.sign not in (-1, 1)):
            return decline("the outcome quality is not a declared binary classification")
        positive = (affected if outcome.sign == 1 else acquired.value - affected) if classified else None
        removed = 0.0
        removed_sign = None
        if outcome.kind in {"acquired-discard", "batch-discard"}:
            removed, removed_sign = affected, outcome.sign
        if index == completion_index:
            removal_quality = quality(completion)
            if classified is None or removal_quality is None or removal_quality[0] != classified[0]:
                return decline("removal and classification describe different qualities")
            removed_sign = removal_quality[1]
            removed = positive if removed_sign == 1 else acquired.value - positive
        if ctx.query["mode"] == "acquired":
            if ctx.query.get("verb") != acquired.acquisition or asked_quality:
                return decline("the requested acquisition needs matching event and class evidence")
            value = acquired.value
        elif ctx.query["mode"] == "discarded":
            if ctx.query.get("disposal_verb") and outcome.verb != ctx.query["disposal_verb"]:
                return decline("the requested disposal event does not match every batch")
            if asked_quality:
                if classified is None or classified[0] != asked_quality[0]:
                    return decline("a qualified disposal needs compatible quality evidence")
                value = removed if removed_sign == asked_quality[1] else 0.0
            else:
                value = removed
        elif asked_quality:
            if classified is None or classified[0] != asked_quality[0]:
                return decline("a qualified remainder needs compatible quality evidence for every batch")
            value = positive if asked_quality[1] == 1 else acquired.value - positive
            if removed_sign == asked_quality[1]:
                value = resource_residual([value], [removed], ctx.log, source="batch-quality-remainder")
        else:
            value = resource_residual([acquired.value], [removed], ctx.log, source="batch-retained-count")
        selected.append(value)
        details.append(f"batch {index + 1}: {acquired.value:g}, selected {affected:g}, removed {removed:g}, answer contribution {value:g}")
    total = resource_residual(selected, [], ctx.log, source="acquired-batch-total")
    if not isfinite(total) or total < 0:
        return decline("invalid acquired-batch balance")
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    node = SemanticNode("acquired-batches", (("entity", entity), ("measure", measure), ("mode", ctx.query["mode"])))
    detail = "; ".join(details)
    return Answer("number", total, f"{total:g} {measure}; {detail}", proof=AnswerProof(node, (
        ProofStep("independent-acquisition-outcomes", node, (*ctx.store.by_kind(BatchEvidence), *quantities), detail),)))
