"""Sum source-local count × per-member amounts in a complete account."""

from collections import Counter, defaultdict
from math import isfinite

from . import consumer
from ..answer import Answer, AnswerAssumption
from ..model import BatchEvidence, EarningRate, Quantity
from ..evaluate import evaluate
from ..numeric_evidence import audit_numeric_mentions
from ..predicate_compatibility import predicates_compatible
from ..rate_calculation import convert_units
from ..reference_bindings import anaphoric_forms_agree, referenced_forms_agree
from ..reference_identity import reference_from_unit
from ..source_coverage import uncovered_document_units, covered_temporal_annotation


@consumer("weighted-account-total")
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    quotes = list(ctx.store.by_kind(EarningRate))
    quantities = list(ctx.store.by_kind(Quantity))
    who = ctx.match.slots.get("who")
    actor = reference_from_unit(who) if who is not None else None
    # An activity-qualified nominal can omit its actor, or repeat it with a
    # pronoun. Resolve only within one complete, uniquely owned population.
    if ctx.query["mode"] == "components" and (actor is None or not actor.resolved):
        owners = {r.entity_ref for r in rows}
        if len(owners) != 1 or None in owners:
            return decline("the component population has no unique activity participant")
        actor = next(iter(owners))
        if not actor.resolved:
            return decline("the activity participant must be explicitly resolved")
        if who is not None:
            forms = [u.surface for reading in ctx.premises for u in reading.units
                     if u.sense() == "pronoun" and reference_from_unit(u) == actor
                     and getattr(ctx.reg.lexicon.get(u.surface.casefold()), "anaphoric_form", None)]
            if not anaphoric_forms_agree([*forms, who.surface], "singular", ctx.reg):
                return decline("the question pronoun conflicts with the activity participant")
    if (
        not (rows or quantities)
        or ctx.store.collisions
        or ctx.store.quarantined
        or not referenced_forms_agree((*ctx.premises, ctx.question), actor, ctx.reg)
        or any(row.entity_ref != actor or row.provenance.assumption for row in rows)
    ):
        return decline("one fully resolved, actual component account is required")
    periods = {
        (r.provenance.sentence, r.marker)
        for r in rows
        if r.marker and r.marker != "components"
    }
    if any(
        not isinstance(f, (BatchEvidence, EarningRate, Quantity))
        and not covered_temporal_annotation(f, ctx.premises, actor.head, periods)
        for f in ctx.store.facts
    ):
        return decline("an additional event lies outside the weighted account")
    expected = defaultdict(Counter)
    amounts = []
    assumptions = []
    requested_measure = ctx.query.get("measure")
    for row in rows:
        if (
            not isfinite(row.value)
            or row.value < 0
            or row.kind not in {"account-unit-supplement", "account-client-supplement"}
            and not float(row.value).is_integer()
        ):
            return decline("component populations must be nonnegative whole counts")
        expected[row.provenance.sentence][row.value] += 1
    if ctx.query["mode"] == "earnings":
        period = ctx.match.slots.get("period")
        window = reference_from_unit(period) if period is not None else None
        work = [r for r in rows if r.kind == "account-work"]
        for q in quantities:
            reading = next(
                (r for r in ctx.premises if r.sentence_index == q.provenance.sentence),
                None,
            )
            if (
                q.entity_ref != actor
                or q.owner
                or q.qualifier
                or q.measure_qualifier
                or q.label
                or q.provenance.distributive
                or q.provenance.assumption
                or reading is None
                or not any(
                    u.sense() == "verb"
                    and ctx.reg.word_in_category(
                        u.features.get("fold", ""), "past_service_predicate"
                    )
                    for u in reading.units
                )
            ):
                return decline(
                    "an additional holding or uncompleted service lies outside the earnings account"
                )
            time_units = [
                u
                for u in reading.units
                if q.time
                and u.surface.casefold() == q.time.casefold()
                and ctx.reg.word_in_category(
                    u.features.get("lemma", ""), "duration_measure"
                )
                and u.features.get("pattern_consumed")
            ]
            if q.time and len(time_units) != 1:
                return decline(
                    "the completed service needs one preserved reporting period"
                )
            reporting = reference_from_unit(time_units[0]) if time_units else None
            work.append(
                BatchEvidence(
                    provenance=q.provenance,
                    kind="account-work",
                    entity=q.entity,
                    entity_ref=q.entity_ref,
                    measure=q.measure,
                    value=q.value,
                    position=0,
                    verb=q.verb,
                    marker=reporting.head if reporting else "",
                    container=reporting.head if reporting else "",
                    container_ref=reporting,
                )
            )
            expected[q.provenance.sentence][q.value] += 1
        if (
            len(quotes) != 1
            or not work
            or any(r.kind not in {
                "account-work", "account-product", "account-unit-supplement",
                "account-client-supplement",
            } for r in rows)
        ):
            return decline(
                "earnings need one service quote and actual matching work counts"
            )
        quote = quotes[0]
        requested_measure = requested_measure or quote.measure
        if (
            quote.entity != actor.head
            or quote.basis != "service"
            or quote.provenance.assumption
            or quote.per != ctx.query["item"]
            or quote.verb != ctx.query["verb"]
            or not isfinite(quote.value)
            or quote.value < 0
        ):
            return decline(
                "the service price must identify the requested participant and activity"
            )
        expected[quote.provenance.sentence][
            quote.numerator if quote.numerator is not None else quote.value
        ] += 1
        if quote.denominator is not None:
            expected[quote.provenance.sentence][quote.denominator] += 1
        for row in work:
            if (
                row.measure != quote.per
                or row.verb != quote.verb
                or row.provenance.sentence <= quote.provenance.sentence
                or row.marker != ctx.query.get("period", "")
                or row.container_ref != window
                or not isfinite(row.value)
                or row.value < 0
                or not float(row.value).is_integer()
            ):
                return decline("the completed work and requested period must agree")
            value = evaluate(
                "count * price",
                {"count": row.value, "price": quote.value},
                ctx.log,
                source="service-earned-subtotal",
            )
            amounts.append((value, quote.measure))
        work_count = evaluate(
            " + ".join(str(row.value) for row in work), {}, ctx.log,
            source="completed-service-population",
        )
        for row in rows:
            if row.kind not in {"account-unit-supplement", "account-client-supplement"}:
                continue
            if row.kind == "account-unit-supplement":
                if row.container != quote.per or row.container_ref is None or row.container_ref.described:
                    return decline("the supplement must name the completed service unit")
            else:
                if (row.acquisition != actor.head or not ctx.reg.word_in_category(
                    row.container, "service_client"
                )):
                    return decline("the clients must belong to the service provider")
                assumptions.append(AnswerAssumption(
                    "one-client-per-service",
                    f"One distinct client per completed service: {work_count:g} clients.",
                    tuple(sorted({row.provenance.sentence, *[r.provenance.sentence for r in work]})),
                ))
            value = evaluate(
                "count * supplement", {"count": work_count, "supplement": row.value},
                ctx.log, source="service-population-supplement",
            )
            amounts.append((value, row.measure))
        products = [r for r in rows if r.kind == "account-product"]
        for row in products:
            if row.marker and (
                row.marker != ctx.query.get("period", "") or row.container_ref != window
            ):
                return decline("the supplement belongs to another reporting period")
            if row.attribute == "implicit-per-service":
                if row.acquisition != quote.per or row.value > work_count:
                    return decline("the supplemented service subset exceeds or differs from the completed work")
                assumptions.append(AnswerAssumption(
                    "per-service-supplement",
                    f"The {row.per_member:g} {row.measure} supplement applies to each of the {row.value:g} stated services.",
                    (row.provenance.sentence,),
                ))
            elif row.attribute == "implicit-per-client":
                assumptions.append(AnswerAssumption(
                    "per-client-supplement",
                    f"Each of the {row.value:g} clients paid the stated {row.per_member:g} {row.measure} supplement.",
                    (row.provenance.sentence,),
                ))
        ctx.log.consumed_earnings_account_keys.add(quote.key())
    else:
        if (
            quotes
            or quantities
            or any(
                r.kind != "account-product" or r.marker != "components" for r in rows
            )
        ):
            return decline(
                "a component total needs explicitly counted objects and contents"
            )
        depiction = ctx.query.get("scope") == "depicted-components"
        if any(
            not (
                depiction
                or
                r.container == ctx.query["host"]
                or ctx.reg.category_term_contains(ctx.query["host"], r.container)
            )
            or r.verb != ctx.query["verb"]
            for r in rows
        ):
            return decline(
                "the objects must belong to the requested class and activity"
            )
        if depiction:
            if not ctx.reg.word_in_category(ctx.query["verb"], "component_depiction_activity"):
                return decline("action on a whole does not establish action on its components")
            assumptions.append(AnswerAssumption(
                "explicitly-depicted-components",
                "Count the explicitly described parts as included in the depictions of the whole objects.",
                tuple(sorted({r.provenance.sentence for r in rows})),
            ))
        products = rows
    for row in products:
        if (
            not isfinite(row.per_member)
            or row.per_member < 0
            or ctx.query["mode"] == "components"
            and not float(row.per_member).is_integer()
        ):
            return decline("per-member amounts must be finite and nonnegative")
        expected[row.provenance.sentence][row.per_member] += 1
        value = evaluate(
            "count * each",
            {"count": row.value, "each": row.per_member},
            ctx.log,
            source="explicit-component-product",
        )
        amounts.append((value, row.measure))
    if uncovered_document_units(
        ctx.premises, ctx.question, ctx.match.consumed
    ) or audit_numeric_mentions(
        (*ctx.premises, ctx.question),
        expected,
        missing="missing",
        duplicate="duplicate",
    ):
        return decline(
            "every quantity, condition and component must belong to the account"
        )
    converted = [
        convert_units(
            value,
            unit,
            requested_measure,
            ctx.reg,
            ctx.log,
            source="weighted-account-unit",
        )
        for value, unit in amounts
    ]
    if any(value is None for value in converted):
        return decline("all contributions must use compatible requested quantities")
    value = evaluate(
        " + ".join(map(str, converted)), {}, ctx.log, source="weighted-account-total"
    )
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    return Answer(
        "number",
        value,
        "sum each population multiplied by its per-member amount",
        assumptions=tuple(assumptions),
    )
