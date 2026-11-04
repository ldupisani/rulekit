"""Recover a partitioned opening stock from observed lists and complementary fractions."""

from . import consumer
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..answer import Answer
from ..model import BatchEvidence
from ..reference_identity import reference_from_unit, constrains
from ..evaluate import evaluate


@consumer("section-stock-reconstruction")
def consume(ctx):
    rows = list(ctx.store.by_kind(BatchEvidence))
    contexts = [r for r in rows if r.kind == "section-stock-context"]
    known = [r for r in rows if r.kind == "section-observed"]
    removed = [r for r in rows if r.kind == "section-removed-fraction"]
    rest = [r for r in rows if r.kind == "section-remainder"]

    def fail(s):
        return Answer("decline", None, s)

    if (
        len(contexts) != 1
        or not known
        or len(removed) != 1
        or not rest
        or len(rows) != 1 + len(known) + 1 + len(rest)
    ):
        return fail(
            "one stock, disjoint observed section and exhaustive complementary section are required"
        )
    context, removed = contexts[0], removed[0]
    asked = reference_from_unit(ctx.match.slots["holder"])
    if asked.owner or asked.label or set(asked.qualifiers) - {context.measure}:
        return fail("the requested container has an unstated identity or restriction")
    if (
        not constrains(ctx.query_reference(), context.entity_ref)
        or not constrains(
            ctx.query_reference("other") or ctx.query_reference(), context.entity_ref
        )
        or context.container != ctx.query["holder"]
        or context.measure != ctx.query["measure"]
        or any(
            (r.entity_ref != context.entity_ref and not (r is removed and not r.entity))
            or r.container_ref != context.container_ref
            for r in rows
        )
        or len({r.attribute for r in known}) != 1
        or any(r.attribute != removed.attribute for r in rest)
        or removed.measure != context.measure
        or removed.acquisition != context.measure
        and not ctx.reg.category_term_contains(context.measure, removed.acquisition)
        or known[0].attribute == removed.attribute
        or not 0 <= removed.value < 1
        or any(
            r.measure != context.measure
            and not ctx.reg.category_term_contains(context.measure, r.measure)
            for r in [*known, *rest]
        )
    ):
        return fail(
            "the lists must cover the same stock in distinct sections and the remainder must identify the fraction’s section"
        )
    if any(not float(r.value).is_integer() or r.value < 0 for r in [*known, *rest]):
        return fail("stock components require whole nonnegative counts")
    if any(r.provenance.assumption for r in rows):
        return fail("stock reconstruction requires observed evidence")
    for group in (known, rest):
        identities = [(r.measure, r.acquisition_ref) for r in group]
        if len(set(identities)) != len(identities):
            return fail("a component list repeats an item identity")
    operands = [
        (context, []),
        (removed, [removed.value]),
        *((r, [r.value]) for r in [*known, *rest]),
    ]
    if not closed_evidence(ctx, rows, operands):
        return fail("every stock component and condition must be explained")
    value = evaluate(
        "known + remaining / (1 - fraction)",
        dict(
            known=sum(r.value for r in known),
            remaining=sum(r.value for r in rest),
            fraction=removed.value,
        ),
        ctx.log,
        source="section-stock-reconstruction",
    )
    if not float(value).is_integer():
        return fail("the fraction does not determine a whole opening stock")
    return finish_batch_answer(
        ctx,
        rows,
        value,
        "sum the observed section and the other section reconstructed from its exhaustive remainder",
    )
