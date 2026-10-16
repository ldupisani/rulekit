"""Sum an explicitly bounded event-result progression from its initial term."""

from collections import Counter, defaultdict
from math import isfinite
from . import consumer
from .ordered_sequence import affine_terms_from_first
from ..answer import Answer
from ..model import BatchEvidence
from ..evaluate import evaluate
from ..numeric_evidence import audit_numeric_mentions
from ..source_coverage import uncovered_document_units


@consumer(
    "event-sequence-total",
    applicable=lambda s: any(b.kind == "event-seed" for b in s.by_kind(BatchEvidence)),
)
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    by = {k: [r for r in rows if r.kind == k] for k in ("event-seed", "event-step")}
    references = [r for r in rows if r.kind == "event-reference"]
    if (
        len(rows) != 2 + len(references)
        or any(len(v) != 1 for v in by.values())
        or ctx.store.collisions
        or ctx.store.quarantined
    ):
        return decline("one initial event and one recurrence are required")
    first = by["event-seed"][0]
    step = by["event-step"][0]
    count = float(ctx.query["count"])
    if (
        any(b.provenance.assumption for b in rows)
        or first.provenance.sentence >= step.provenance.sentence
        or any(
            b.entity != ctx.query["event"] or b.measure != ctx.query["item"]
            for b in rows
        )
        or first.verb != ctx.query["effect"]
        or not isfinite(count)
        or count < 0
        or not count.is_integer()
        or not isfinite(first.value)
        or first.value < 0
        or not float(first.value).is_integer()
    ):
        return decline(
            "the projected sequence must describe one result and an integral event count"
        )
    expected = defaultdict(Counter)
    expected[first.provenance.sentence][first.value] += 1
    expected[step.provenance.sentence][step.value] += 1
    expected[ctx.question.sentence_index][count] += 1
    # Nominal references retain their source numeric representation for the
    # audit; they are not recurrence operands or additional events.
    for reference in references:
        if (
            reference.provenance.sentence != step.provenance.sentence
            or reference.value != 1
        ):
            return decline("an event reference must belong to its recurrence")
        expected[reference.provenance.sentence][reference.value] += 1
    if uncovered_document_units(
        ctx.premises, ctx.question, ctx.match.consumed
    ) or audit_numeric_mentions(
        (*ctx.premises, ctx.question),
        expected,
        missing="missing",
        duplicate="duplicate",
    ):
        return decline(
            "the sequence must account for every condition and source number"
        )
    terms = affine_terms_from_first(first.value, int(count) + 1, step.value, 0, ctx.log)
    if terms is None or any(not float(v).is_integer() for v in terms):
        return decline("the recurrence must produce finite whole-number event results")
    value = evaluate(
        " + ".join(str(v) for v in terms), {}, ctx.log, source="event-sequence-total"
    )
    ctx.log.consumed_batch_keys.update(b.key() for b in rows)
    return Answer(
        "number",
        value,
        "Sum the initial event and every explicitly requested subsequent event.",
    )
