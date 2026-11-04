"""Normalize an explicitly adjusted numerator and work duration to a unit rate."""

from . import consumer
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..answer import Answer
from ..model import BatchEvidence
from ..reference_identity import constrains
from ..evaluate import evaluate
from ..predicate_compatibility import predicates_compatible
from ..rate_calculation import convert_units, convert_duration


@consumer(
    "adjusted-unit-rate",
    applicable=lambda s: any(
        r.kind == "adjusted-rate-base" for r in s.by_kind(BatchEvidence)
    ),
)
def consume(ctx):
    rows = list(ctx.store.by_kind(BatchEvidence))
    base = [r for r in rows if r.kind == "adjusted-rate-base"]
    extra = [r for r in rows if r.kind == "adjusted-rate-increment"]
    context = [r for r in rows if r.kind == "adjusted-rate-context"]

    def fail(s):
        return Answer("decline", None, s)

    if (
        len(base) != 1
        or len(extra) != 1
        or len(context) > 1
        or len(rows) != 2 + len(context)
    ):
        return fail(
            "one base and one explicit numerator-and-duration adjustment are required"
        )
    base, extra = base[0], extra[0]
    if (
        not constrains(ctx.query_reference(), base.entity_ref)
        or not constrains(
            ctx.query_reference("other") or ctx.query_reference(), base.entity_ref
        )
        or any(r.entity_ref != base.entity_ref or r.provenance.assumption for r in rows)
        or base.marker != extra.marker
        or not predicates_compatible(base.verb, extra.verb, base.measure, ctx.reg)
    ):
        return fail(
            "the elected adjustment must belong to the same participant and workday"
        )
    amount = convert_units(
        extra.value,
        extra.measure,
        base.measure,
        ctx.reg,
        ctx.log,
        source="adjusted-output-unit",
    )
    duration = convert_duration(
        extra.per_member,
        extra.container,
        base.container,
        ctx.reg,
        ctx.log,
        source="adjusted-duration-unit",
    )
    total_duration = convert_duration(
        base.per_member + (duration or 0),
        base.container,
        ctx.query["unit"],
        ctx.reg,
        ctx.log,
        source="adjusted-rate-denominator",
    )
    if (
        amount is None
        or duration is None
        or total_duration is None
        or total_duration <= 0
    ):
        return fail("both adjusted units must be compatible and duration positive")
    if not closed_evidence(
        ctx,
        rows,
        [
            (base, [base.value, base.per_member]),
            (extra, [extra.value, extra.per_member]),
            *((r, []) for r in context),
        ],
        additional_kinds=("attributive_count",),
    ):
        return fail("all base amounts, adjustments and conditions must be explained")
    value = evaluate(
        "(base + extra) / duration",
        dict(base=base.value, extra=amount, duration=total_duration),
        ctx.log,
        source="adjusted-unit-rate",
    )
    return finish_batch_answer(
        ctx,
        rows,
        value,
        f'{base.measure} per {ctx.query["unit"]}, including both the extra pay and the longer workday',
    )
