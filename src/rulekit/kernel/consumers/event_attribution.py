"""Answer a directly stated participant or explanation for one effect."""

from . import consumer
from ..answer import Answer, AnswerProof, ProofStep, SemanticNode
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..model import Quantity, Unit
from ..reference_identity import attributed_occurrences, constrains
from ..resource_equations import resource_residual
from ..source_coverage import uncovered_document_units


def _source_phrase(reading, span):
    first = next((index for index, unit in enumerate(reading.units) if unit.span[0] == span[0]), 0)
    if first and reading.units[first].sense() == "noun":
        preceding = reading.units[first - 1]
        owner = reading.units[first].features.get("owner_ref_uid")
        if preceding.sense() == "article" or preceding.uid == owner:
            span = preceding.span[0], span[1]
    words = tuple(
        word for unit in reading.units for word in unit.words
        if span[0] <= word.index <= span[1]
    )
    return Unit(-1, words).written.strip()


@consumer("event-attribution")
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    if ctx.query["role"] == "count":
        return _count_events(ctx)
    if (
        ctx.store.collisions or ctx.store.quarantined
        or uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)
        or any(r.unknown_words() for r in (*ctx.premises, ctx.question))
    ):
        return decline("the relevant events need a complete, unambiguous reading")

    requested = ctx.query_reference("subject")
    requested_actor = ctx.query_reference("actor")
    occurrences = {}
    holder = ctx.query.get("holder")
    destination = ctx.reg.word_in_category(ctx.query.get("holder_marker", ""),
                                           "measurement_container_entry_preposition")
    for fact in ctx.store.facts:
        attribution = fact.provenance.attribution
        if attribution is None or fact.provenance.assumption:
            continue
        predicate = ctx.query.get("predicate")
        if predicate and attribution.predicate != predicate:
            continue
        if holder and getattr(fact, "container", None) != holder:
            continue
        if destination and getattr(fact, "operation", None) != "add_quantity":
            continue
        if requested_actor and (attribution.actor is None or not constrains(requested_actor, attribution.actor)):
            continue
        if requested and (attribution.subject is None or not constrains(requested, attribution.subject)):
            continue
        key = fact.provenance.sentence, attribution.position
        previous = occurrences.get(key)
        if previous is not None and previous.provenance.attribution != attribution:
            return decline("the effect has competing attribution evidence")
        occurrences[key] = fact
    if len(occurrences) != 1:
        return decline("the question needs one explicitly identified effect")
    (sentence, _), fact = next(iter(occurrences.items()))
    attribution = fact.provenance.attribution
    reading = next(r for r in ctx.premises if r.sentence_index == sentence)
    role = ctx.query["role"]
    if role == "actor":
        actor = attribution.actor
        actor_class = ctx.query.get("actor_class")
        if (
            actor is None or not actor.resolved or attribution.actor_span is None
            or actor_class and not ctx.reg.category_term_contains(actor_class, actor.head)
        ):
            return decline("the effect needs an explicitly identified actor of the requested type")
        span = attribution.actor_span
    else:
        span = attribution.reason_span
        if span is None or attribution.reason_actor is not None and not attribution.reason_actor.resolved:
            return decline("the effect needs an explicitly attached explanation")
    value = _source_phrase(reading, span)
    if not value:
        return decline("the supporting phrase is missing")
    query = SemanticNode("event-attribution", (("role", role), ("predicate", attribution.predicate)))
    conclusion = SemanticNode("stated-attribution", (("value", value),))
    detail = f"The {role} is stated with the effect in sentence {sentence + 1}."
    return Answer("text", value, detail, AnswerProof(query, (ProofStep(
        "inference/stated-event-attribution", conclusion, (fact,), detail,
    ),)))


def _count_events(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(Quantity))
    if not rows or any(
        row.provenance.assumption or row.measure != ctx.query["subject"]
        or row.verb != ctx.query["predicate"] or row.value < 0 or not float(row.value).is_integer()
        or row.provenance.attribution is None or row.provenance.attribution.actor is None
        or not row.provenance.attribution.actor.resolved
        for row in rows
    ) or not closed_evidence(ctx, rows, [(row, [row.value]) for row in rows]):
        return decline("every counted effect must have its own compatible event evidence")
    query = ctx.query_reference("actor")
    if query:
        matches = attributed_occurrences(query, [row.provenance.attribution for row in rows])
        if matches is None:
            return decline("the requested actor must identify one participant")
        rows = [rows[index] for index in matches]
    return finish_batch_answer(ctx, rows, resource_residual(
        [row.value for row in rows], [], ctx.log, source="attributed-effect-count",
    ), "sum the counted effects from the selected event occurrences")
