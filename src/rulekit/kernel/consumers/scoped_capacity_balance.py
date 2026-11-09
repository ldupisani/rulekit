"""Compare scoped populations constrained by one measured-resource specification."""

from math import floor
from . import consumer
from ..answer import Answer, AnswerAssumption
from ..model import BatchEvidence, Quantity
from ..affine_graph import AffineGraph, AffineError
from ..quantity_ratios import quantity_through_ratios
from ..reference_identity import reference_from_unit
from ..composition_evidence import finish_batch_answer
from ..evaluate import evaluate

KINDS = {
    "capacity-scope-ratio",
    "capacity-resource",
    "capacity-specification",
    "capacity-member-size",
}


@consumer(
    "scoped-capacity-balance",
    applicable=lambda s: any(r.kind in KINDS for r in s.by_kind(BatchEvidence)),
)
def consume(ctx):
    def fail(s):
        return Answer("decline", None, s)

    rows = list(ctx.store.by_kind(BatchEvidence))
    populations = list(ctx.store.by_kind(Quantity))
    by = {k: [r for r in rows if r.kind == k] for k in KINDS}
    if (
        len(rows) + len(populations) != len(ctx.store.facts)
        or len(populations) != 1
        or any(r.kind not in KINDS for r in rows)
        or any(len(by[k]) != 1 for k in KINDS - {"capacity-member-size"})
        or len(by["capacity-member-size"]) != 2
    ):
        return fail(
            "two identified populations need one resource ratio, observed amount and per-size specification"
        )
    pop = populations[0]
    ratio = by["capacity-scope-ratio"][0]
    resource = by["capacity-resource"][0]
    spec = by["capacity-specification"][0]
    sizes = by["capacity-member-size"]
    actor = reference_from_unit(ctx.match.slots["who"])
    left = reference_from_unit(ctx.match.slots["left"])
    right = reference_from_unit(ctx.match.slots["right"])
    scopes = {r.container_ref for r in sizes}
    indices = [
        tuple(
            ctx.reg.attribute_value(q, "ordinal_index")
            for q in scope.qualifiers
            if ctx.reg.attribute_value(q, "ordinal_index") is not None
        )
        for scope in scopes
    ]
    if (
        pop.entity_ref != actor
        or not actor.resolved
        or not ctx.reg.word_in_category(pop.verb, "possession_state")
        or not ctx.reg.word_in_category(pop.measure, "capacity_holder")
        or pop.owner
        or pop.label
        or pop.content_ref
        or pop.provenance.assumption
        or spec.entity_ref != actor
        or any(r.entity_ref != actor for r in sizes)
        or pop.value != len(scopes)
        or len(scopes) != 2
        or {left, right} != scopes
        or any(scope.head != pop.measure for scope in scopes)
        or any(len(index) != 1 or not 1 <= index[0] <= pop.value for index in indices)
        or len(set(indices)) != len(indices)
        or {ratio.entity_ref, ratio.container_ref} != scopes
        or resource.entity_ref not in scopes
        or any(r.measure != ctx.query["measure"] for r in sizes)
        or spec.acquisition != ctx.query["measure"]
        or pop.measure_ref is not None
        and set(pop.measure_ref.qualifiers) - {ctx.query["measure"]}
        or pop.measure_qualifier
        and pop.measure_qualifier != ctx.query["measure"]
    ):
        return fail(
            "the same owner, distinct containers and measured population must be used throughout"
        )
    try:
        graph = AffineGraph(
            [(resource.entity_ref, resource.value)],
            [(ratio.entity_ref, ratio.container_ref, ratio.value, 0)],
            ctx.log,
        )
        amounts = {}
        for r in sizes:
            total = quantity_through_ratios(
                graph.value(r.container_ref),
                (resource.measure, resource.attribute),
                (r.measure, r.measure),
                [
                    (
                        (spec.measure, spec.attribute),
                        (spec.container, spec.acquisition),
                        spec.value,
                        1,
                    ),
                    ((r.attribute, r.measure), (r.measure, r.measure), r.value, 1),
                ],
                ctx.reg,
                ctx.log,
            )
            amounts[r.container_ref] = floor(total + 1e-9)
    except AffineError as error:
        return fail(str(error))
    loss = float(ctx.query.get("loss", "0"))
    if loss:
        affected = left
        member = reference_from_unit(ctx.match.slots["affected"])
        if (
            set(member.qualifiers) != {left.head, *left.qualifiers}
            or loss != 1
            or amounts[affected] < 2
            or member.owner is not None
        ):
            return fail(
                "the stated within-group removal needs two distinct existing members in that group"
            )
        amounts[affected] -= loss
    operands = [(r, [r.value]) for r in [*rows, pop]]
    # The actor count in the conditional is a source number, not a second loss.
    from ..numeric_evidence import audit_numeric_mentions
    from collections import Counter, defaultdict

    expected = defaultdict(Counter)
    for r, vals in operands:
        expected[r.provenance.sentence].update(vals)
    if loss:
        expected[ctx.question.sentence_index][loss] += 1
    from ..source_coverage import uncovered_units, quantity_ledger_source_units

    population_reading = next(
        r for r in ctx.premises if r.sentence_index == pop.provenance.sentence
    )
    footprint = quantity_ledger_source_units(population_reading, [pop], ctx.reg)

    if (
        ctx.store.collisions
        or ctx.store.quarantined
        or any(
            r.provenance.assumption and r.kind != "capacity-member-size" for r in rows
        )
        or audit_numeric_mentions(
            (*ctx.premises, ctx.question),
            expected,
            missing="missing",
            duplicate="duplicate",
            additional_kinds=("attributive_count",),
        )
        or any(
            uncovered_units(
                reading,
                (
                    ctx.match.consumed
                    if reading is ctx.question
                    else footprint if reading is population_reading else ()
                ),
            )
            for reading in (*ctx.premises, ctx.question)
        )
    ):
        return fail(
            "every container, resource, member size and conditional change must be read"
        )
    value = evaluate(
        "first - second",
        dict(first=amounts[left], second=amounts[right]),
        ctx.log,
        source="capacity-population-difference",
    )
    if value < 0:
        return fail(
            "the first population is not the larger population after the stated change"
        )
    return finish_batch_answer(
        ctx,
        rows,
        value,
        "derive each resource budget, apply the per-size rule and compare the resulting member counts",
        assumptions=(
            AnswerAssumption(
                "proportional-fully-stocked-containers",
                "Both containers have the same filled proportion and are stocked to the stated resource-per-size limit; stated member sizes are retained after the removal.",
                tuple(
                    sorted(
                        {
                            pop.provenance.sentence,
                            resource.provenance.sentence,
                            *[r.provenance.sentence for r in sizes],
                        }
                    )
                ),
            ),
        ),
    )
