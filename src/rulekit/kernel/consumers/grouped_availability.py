"""Count eligible units in uniform groups, retaining exclusions and vacancy evidence."""

from math import isfinite

from . import consumer
from ..composition_evidence import closed_evidence, finish_batch_answer
from .indexed_path import ordinal_index
from ..answer import Answer
from ..evaluate import evaluate
from ..model import BatchEvidence
from ..reference_identity import reference_from_unit


@consumer("grouped-availability")
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    contexts = [r for r in rows if r.kind == "available-capacity-context"]
    structures = [r for r in rows if r.kind == "available-capacity-structure"]
    exclusions = [r for r in rows if r.kind == "available-capacity-exclusion"]
    vacancies = [r for r in rows if r.kind == "available-capacity-vacancy"]
    if (
        len(contexts) > 1
        or len(structures) != 1
        or len(exclusions) != 1
        or len(vacancies) > 1
        or len(rows)
        != len(contexts) + len(structures) + len(exclusions) + len(vacancies)
    ):
        return decline(
            "one uniform capacity structure and an explicit exclusion are required"
        )
    structure, exclusion = structures[0], exclusions[0]
    exclusion_reading = next(
        r for r in ctx.premises if r.sentence_index == exclusion.provenance.sentence
    )
    excluded = [
        reference_from_unit(u)
        for u in exclusion_reading.units
        if u.span[0] == exclusion.position
        and u.features.get("lemma") == exclusion.measure
    ]
    if (
        len(excluded) != 1
        or excluded[0].label
        or (excluded[0].owner is not None and excluded[0].owner != structure.entity_ref)
    ):
        return decline("an excluded group must belong to the same stated site")
    reading = next(
        r for r in ctx.premises if r.sentence_index == structure.provenance.sentence
    )
    units = [
        u
        for u in reading.units
        if u.features.get("value_kind") == "count"
        and u.features.get("lemma") == structure.measure
        and u.features.get("value") == structure.per_member
    ]
    if (
        len(units) != 1
        or any(
            not ctx.reg.word_in_category(q, "uniform_structure_descriptor")
            for q in reference_from_unit(units[0]).qualifiers
        )
        or reference_from_unit(units[0]).owner
        or reference_from_unit(units[0]).label
    ):
        return decline(
            "the per-group count must describe all units, without an unstated subset"
        )
    if any(
        not ctx.reg.word_in_category(q, "distinct_option_descriptor")
        for q in reference_from_unit(ctx.match.slots["unit"]).qualifiers
    ):
        return decline(
            "a qualified availability request needs matching subset evidence"
        )
    if (
        structure.measure != ctx.query["measure"]
        or exclusion.measure != structure.container
        or any(
            not isfinite(v) or v < 0 or not float(v).is_integer()
            for v in (structure.value, structure.per_member, exclusion.value)
        )
        or structure.value <= 0
        or structure.per_member <= 0
        or exclusion.value > structure.value
        or exclusion.provenance.sentence <= structure.provenance.sentence
    ):
        return decline("capacity units, excluded groups and whole counts must agree")
    operands = [(structure, [structure.value, structure.per_member])]
    if exclusion.attribute:
        index = ordinal_index(exclusion.attribute, ctx.reg)
        if ctx.reg.word_in_category(exclusion.attribute, "holder_terminal_order"):
            index = structure.value
        if index is None or index > structure.value or exclusion.value != 1:
            return decline(
                "an ordinal exclusion must identify one group within the declared structure"
            )
    else:
        operands.append((exclusion, [exclusion.value]))
    if contexts:
        context = contexts[0]
        if (
            context.container_ref != structure.entity_ref
            or context.measure != structure.measure
            or ctx.query.get("entity")
            and context.entity_ref != reference_from_unit(ctx.match.slots["who"])
        ):
            return decline(
                "the reservation purpose must identify the requested site and unit"
            )
    if not vacancies and ctx.query.get("vacant") != "true":
        return decline(
            "available assignments need explicit evidence that the other units are unoccupied"
        )
    if not closed_evidence(ctx, rows, operands):
        return decline(
            "every capacity, exclusion and occupancy condition must belong to the same site"
        )
    value = evaluate(
        "(groups - unavailable) * each",
        dict(
            groups=structure.value,
            unavailable=exclusion.value,
            each=structure.per_member,
        ),
        ctx.log,
        source="available-grouped-capacity",
    )
    return finish_batch_answer(
        ctx,
        rows,
        value,
        "count the units in eligible groups, using the explicit absence of other occupants",
    )
