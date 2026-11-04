"""Close a stated source partition using ordered whole and unassigned shares."""

from collections import Counter, defaultdict
from math import isfinite

from . import consumer
from ..answer import Answer, AnswerAssumption
from ..evaluate import evaluate
from ..model import BatchEvidence, Quantity
from ..numeric_evidence import audit_numeric_mentions
from ..predicate_compatibility import predicates_compatible
from ..rate_calculation import convert_units
from ..reference_bindings import referenced_forms_agree
from ..reference_identity import constrains, reference_from_unit
from ..resource_equations import resource_residual
from ..source_coverage import (
    covered_temporal_annotation,
    uncovered_document_units,
    uncovered_units,
    quantity_source_units,
)


@consumer("source-contribution-remainder")
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = sorted(
        ctx.store.by_kind(BatchEvidence),
        key=lambda row: (row.provenance.sentence, row.position),
    )
    totals = [row for row in rows if row.kind == "contribution-target"]
    observed = list(ctx.store.by_kind(Quantity))
    footprints = {}
    if not totals and len(observed) == 1:
        whole = observed[0]
        if (
            whole.provenance.assumption
            or whole.time
            or whole.measure_qualifier
            or not ctx.reg.word_in_category(whole.verb, "contribution_change_verb")
            or not ctx.reg.word_in_category(whole.measure, "contribution_unit")
        ):
            return decline(
                "an actual contribution total needs one compatible measured outcome"
            )
        total = BatchEvidence(
            provenance=whole.provenance,
            kind="contribution-target",
            entity=whole.entity,
            entity_ref=whole.entity_ref,
            measure=whole.measure,
            value=whole.value,
            verb=whole.verb,
            position=-1,
        )
        totals = [total]
        rows.append(total)
        reading = next(
            r for r in ctx.premises if r.sentence_index == whole.provenance.sentence
        )
        footprints[reading.sentence_index] = quantity_source_units(
            reading, whole, ctx.reg
        )
    elif observed:
        return decline("the contribution account has competing measured outcomes")
    inventory = [row for row in rows if row.kind == "contribution-source"]
    parts = [
        row
        for row in rows
        if row.kind
        in {
            "contribution-fraction",
            "contribution-multiple",
            "contribution-remainder-fraction",
            "contribution-amount",
        }
    ]
    if not totals and rows and all(row.kind == "contribution-amount" for row in rows):
        return _observed_sources(ctx, rows)
    if (
        len(totals) != 1
        or not inventory
        or not parts
        or len(rows) != len(totals) + len(inventory) + len(parts)
        or ctx.store.collisions
        or ctx.store.quarantined
    ):
        return decline(
            "one target and its complete stated source partition are required"
        )
    total = totals[0]
    actor = (
        reference_from_unit(ctx.match.slots["who"])
        if "who" in ctx.match.slots
        else reference_from_unit(ctx.match.slots["attribute"]).owner
    )
    if (
        total.entity_ref != actor
        or not isfinite(total.value)
        or total.value <= 0
        or not referenced_forms_agree((*ctx.premises, ctx.question), actor, ctx.reg)
        or ctx.query["verb"]
        and not predicates_compatible(
            total.verb, ctx.query["verb"], total.measure, ctx.reg
        )
        or any(row.provenance.assumption for row in rows)
        or any(row.entity and row.entity_ref != actor for row in (*inventory, *parts))
        or any(
            row.container_ref is None or not row.container_ref.resolved
            for row in (*inventory, *parts)
        )
    ):
        return decline(
            "the target, inventories and contributions must describe one resolved recipient"
        )
    sources = {row.container_ref: row for row in inventory}
    if len(sources) != len(inventory) or len(
        {source.head for source in sources}
    ) != len(sources):
        return decline(
            "the stated source inventory contains overlapping or repeated descriptions"
        )

    def identify(reference):
        matching = [source for source in sources if constrains(reference, source)]
        return matching[0] if len(matching) == 1 else None

    requested = identify(reference_from_unit(ctx.match.slots["source"]))
    if requested is None:
        return decline(
            "the requested source must uniquely identify one member of the stated inventory"
        )
    expected = defaultdict(Counter)
    expected[total.provenance.sentence][total.value] += 1
    amounts = {}
    for index, part in enumerate(parts):
        source = identify(part.container_ref)
        if (
            source is None
            or source in amounts
            or source == requested
            or not isfinite(part.value)
            or part.value < 0
            or part.provenance.sentence <= total.provenance.sentence
            or sources[source].provenance.sentence >= part.provenance.sentence
            or part.attribute
            and sources[source].marker != part.attribute
            or part.verb
            and not predicates_compatible(part.verb, total.verb, total.measure, ctx.reg)
            or part.measure
            and part.kind != "contribution-amount"
            and not _quantity_basis_agrees(
                part.measure, part.provenance.sentence, total.measure, ctx
            )
        ):
            return decline(
                "each stated contribution must identify its own source, quantity and temporal context"
            )
        expected[part.provenance.sentence][part.value] += 1
        if part.kind == "contribution-multiple":
            standard = identify(part.acquisition_ref) if part.acquisition_ref else None
            if part.acquisition_ref is None:
                prior = [
                    row
                    for row in parts[:index]
                    if row.provenance.sentence == part.provenance.sentence - 1
                ]
                if len(prior) == 1:
                    standard = identify(prior[0].container_ref)
            if standard not in amounts or standard == source:
                return decline(
                    "a relative contribution needs an already established distinct source amount"
                )
            base = amounts[standard]
        elif part.kind == "contribution-remainder-fraction":
            base = resource_residual(
                [total.value],
                amounts.values(),
                ctx.log,
                source="unassigned-contribution-target",
            )
        else:
            base = total.value
        if (
            part.kind not in {"contribution-multiple", "contribution-amount"}
            and part.value > 1
        ):
            return decline("a part-of-whole contribution cannot exceed its base")
        if part.kind == "contribution-amount":
            value = convert_units(
                part.value,
                part.measure,
                total.measure,
                ctx.reg,
                ctx.log,
                source="source-measured-contribution-unit",
            )
            if value is None:
                return decline(
                    "a measured contribution must have the same quantity as the target"
                )
        else:
            value = evaluate(
                "base * factor",
                {"base": base, "factor": part.value},
                ctx.log,
                source="source-contribution-amount",
            )
        amounts[source] = value
        if (
            resource_residual(
                [total.value],
                amounts.values(),
                ctx.log,
                source="contribution-account-balance",
            )
            < 0
        ):
            return decline("the stated contributions exceed the closed target")
    if set(sources) - set(amounts) != {requested}:
        return decline(
            "the source partition must leave exactly the requested contribution unknown"
        )
    periods = {
        (row.provenance.sentence, marker)
        for row in rows
        for marker in (row.marker, row.attribute)
        if marker
    }
    for fact in ctx.store.facts:
        if isinstance(fact, BatchEvidence):
            continue
        if fact in observed:
            continue
        if not covered_temporal_annotation(fact, ctx.premises, actor.head, periods):
            return decline(
                "an additional event lies outside the closed contribution account"
            )
    if (
        any(
            uncovered_units(reading, footprints.get(reading.sentence_index, ()))
            for reading in ctx.premises
        )
        or uncovered_units(ctx.question, ctx.match.consumed)
        or audit_numeric_mentions(
            (*ctx.premises, ctx.question),
            expected,
            missing="missing",
            duplicate="duplicate",
        )
    ):
        return decline(
            "every target, source, fraction and condition must belong to the contribution account"
        )
    residual = resource_residual(
        [total.value], amounts.values(), ctx.log, source="missing-source-contribution"
    )
    if "attribute" in ctx.match.slots and not _quantity_basis_agrees(
        ctx.match.slots["attribute"].features.get("lemma", ""),
        ctx.question.sentence_index,
        total.measure,
        ctx,
    ):
        return decline(
            "the requested contribution names a different quantity dimension"
        )
    value = convert_units(
        residual,
        total.measure,
        ctx.query["measure"] or total.measure,
        ctx.reg,
        ctx.log,
        source="source-contribution-output-unit",
    )
    if value is None:
        return decline("the requested contribution unit must match the target quantity")
    ctx.log.consumed_batch_keys.update(row.key() for row in rows)
    return Answer(
        "number",
        value,
        "treat the listed sources as accounting for the full target; subtract whole-target and successive unassigned shares",
        assumptions=(AnswerAssumption("complete-source-partition",
            "The listed sources account for the full stated total or target.",
            tuple(sorted({total.provenance.sentence, *[r.provenance.sentence for r in inventory]}))),),
    )


def _quantity_basis_agrees(measure, sentence, target_unit, ctx):
    if ctx.reg.attribute_applies_to(measure, target_unit):
        return True
    if not ctx.reg.word_in_category(measure, "quantity_change_nominal"):
        return False
    reading = next(
        (r for r in (*ctx.premises, ctx.question) if r.sentence_index == sentence), None
    )
    nouns = (
        [
            u
            for u in reading.units
            if u.sense() == "noun" and u.features.get("lemma") == measure
        ]
        if reading
        else []
    )
    if len(nouns) != 1:
        return False
    dimensions = [
        q
        for q in reference_from_unit(nouns[0]).qualifiers
        if ctx.reg.word_in_category(q, "quantity_attribute")
    ]
    return (
        len(dimensions) == 1
        and ctx.reg.attribute_applies_to(dimensions[0], target_unit)
        and all(
            q in dimensions
            or ctx.reg.word_in_category(q, "remaining_quantity_descriptor")
            for q in reference_from_unit(nouns[0]).qualifiers
        )
    )


def _observed_sources(ctx, rows):
    """Direct attributed amounts can answer a source lookup without a target."""

    def decline(reason):
        return Answer("decline", None, reason)

    actor = (
        reference_from_unit(ctx.match.slots["who"])
        if "who" in ctx.match.slots
        else reference_from_unit(ctx.match.slots["attribute"]).owner
    )
    source = reference_from_unit(ctx.match.slots["source"])
    if (
        len(rows) != len(ctx.store.facts)
        or ctx.store.collisions
        or ctx.store.quarantined
        or not referenced_forms_agree((*ctx.premises, ctx.question), actor, ctx.reg)
    ):
        return decline(
            "a source lookup needs one completely read attributed-amount account"
        )
    expected = defaultdict(Counter)
    grouped = defaultdict(list)
    unit = ctx.query["measure"] or rows[0].measure
    if "attribute" in ctx.match.slots and not _quantity_basis_agrees(
        ctx.match.slots["attribute"].features.get("lemma", ""),
        ctx.question.sentence_index,
        unit,
        ctx,
    ):
        return decline(
            "the requested observed contribution has a different quantity dimension"
        )
    for row in rows:
        if (
            row.entity_ref is None
            or not row.entity_ref.resolved
            or row.container_ref is None
            or not row.container_ref.resolved
            or row.provenance.assumption
            or not isfinite(row.value)
            or row.value < 0
        ):
            return decline(
                "each observed amount must identify its actual recipient and source"
            )
        expected[row.provenance.sentence][row.value] += 1
        amount = convert_units(
            row.value,
            row.measure,
            unit,
            ctx.reg,
            ctx.log,
            source="observed-contribution-unit",
        )
        if amount is None:
            return decline(
                "the observed account must use compatible requested quantities"
            )
        grouped[(row.entity_ref, row.container_ref, row.verb)].append(amount)
    if uncovered_document_units(
        ctx.premises, ctx.question, ctx.match.consumed
    ) or audit_numeric_mentions(
        (*ctx.premises, ctx.question),
        expected,
        missing="missing",
        duplicate="duplicate",
    ):
        return decline("all attributed amounts and source restrictions must be read")
    selected = []
    for (recipient, origin, verb), amounts in grouped.items():
        value = evaluate(
            " + ".join(str(value) for value in amounts),
            {},
            ctx.log,
            source="observed-source-subtotal",
        )
        if (
            recipient == actor
            and constrains(source, origin)
            and (
                not ctx.query["verb"]
                or predicates_compatible(verb, ctx.query["verb"], unit, ctx.reg)
            )
        ):
            selected.append(value)
    if not selected:
        return decline(
            "no observed contribution identifies the requested recipient, activity and source"
        )
    value = evaluate(
        " + ".join(str(value) for value in selected),
        {},
        ctx.log,
        source="requested-source-total",
    )
    ctx.log.consumed_batch_keys.update(row.key() for row in rows)
    return Answer(
        "number",
        value,
        "sum the directly observed amounts for the requested recipient, activity and source",
    )
