"""Sum complete, separately identified rate × extent components.

Relative quotes retain their source scope. An omitted standard requires a
unique preceding quote of the same role, before any extent is reported.
"""

from collections import Counter, defaultdict
from math import isfinite

from . import consumer
from ..answer import Answer, AnswerAssumption
from ..evaluate import evaluate
from ..model import BatchEvidence, Rate, Quantity
from ..numeric_evidence import audit_numeric_mentions
from ..predicate_compatibility import predicates_compatible
from ..rate_calculation import apply_rate, convert_duration, convert_units
from ..reference_bindings import referenced_forms_agree
from ..reference_identity import reference_from_unit
from ..source_coverage import uncovered_document_units


KINDS = {
    "scoped-rate",
    "scoped-relative-rate",
    "scoped-extent",
    "scoped-relative-extent",
    "scoped-projection-span",
}


@consumer(
    "scoped-rate-total",
    applicable=lambda s: any(r.kind in KINDS for r in s.by_kind(BatchEvidence)),
)
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = sorted(
        ctx.store.by_kind(BatchEvidence),
        key=lambda r: (r.provenance.sentence, r.position),
    )
    observed_spans = list(ctx.store.by_kind(Quantity))
    if observed_spans and ctx.query.get("projection"):
        for observed in observed_spans:
            if (
                observed.time
                or observed.owner
                or observed.qualifier
                or observed.measure_qualifier
                or not ctx.reg.word_in_category(
                    observed.verb, "scheduled_activity_verb"
                )
                or not ctx.reg.word_in_category(observed.measure, "duration_measure")
            ):
                return decline(
                    "the projection requires one complete stated work duration"
                )
            rows.append(
                BatchEvidence(
                    provenance=observed.provenance,
                    kind="scoped-projection-span",
                    entity=observed.entity,
                    entity_ref=observed.entity_ref,
                    measure=observed.measure,
                    value=observed.value,
                    position=0,
                )
            )
    if (
        not rows
        or len(rows) != len(ctx.store.facts)
        or ctx.store.collisions
        or ctx.store.quarantined
        or any(r.kind not in KINDS for r in rows)
    ):
        return decline("one complete account of scoped rates and extents is required")
    actor = reference_from_unit(ctx.match.slots["who"])
    if ctx.match.slots["who"].features.get("number") == "plural":
        return decline(
            "a plural rate account needs an explicit individual or collective scope"
        )
    if not referenced_forms_agree((*ctx.premises, ctx.question), actor, ctx.reg):
        return decline(
            "the actor and possessed contexts need compatible reference forms"
        )
    expected = defaultdict(Counter)
    spans = [row for row in rows if row.kind == "scoped-projection-span"]
    windows = {
        window
        for row in rows
        if row.kind in {"scoped-extent", "scoped-relative-extent"}
        for window in (row.marker, row.attribute)
        if window
    }
    if len(windows) > 1:
        return decline("the component extents specify different reporting periods")
    reporting = next(iter(windows), "") or ctx.query.get("period", "")
    if ctx.query.get("period") and reporting != ctx.query["period"]:
        return decline("the stated schedule and requested reporting period must agree")
    if len(spans) > 1 or spans and (not ctx.query.get("projection") or not reporting):
        return decline(
            "a projected account needs one span and an explicit reporting cadence"
        )
    quotes = {"rate": {}, "extent": {}}
    sources = {"rate": {}, "extent": {}}
    for row in rows:
        if row.kind == "scoped-projection-span":
            if (
                row.entity_ref != actor
                or not isfinite(row.value)
                or row.value < 0
                or row.provenance.assumption
                and row.provenance.sentence != ctx.question.sentence_index - 1
            ):
                return decline(
                    "the projection span must belong to this participant and question"
                )
            expected[row.provenance.sentence][row.value] += 1
            continue
        if (
            row.entity_ref != actor
            or row.container_ref is None
            or not row.container_ref.resolved
            or row.container_ref.owner not in (None, actor)
            or row.provenance.assumption
            or not isfinite(row.value)
            or row.value < 0
        ):
            return decline(
                "each rate and extent must identify the same actor and a resolved scope"
            )
        role = "rate" if row.kind.endswith("rate") else "extent"
        scope = row.container_ref
        if scope in quotes[role]:
            return decline("a scope cannot have competing rates or extents")
        expected[row.provenance.sentence][row.value] += 1
        if row.kind.startswith("scoped-relative-"):
            candidates = [
                (key, value)
                for key, value in quotes[role].items()
                if key != scope
                and (row.acquisition_ref is None or key == row.acquisition_ref)
            ]
            if len(candidates) != 1:
                return decline(
                    "a relative quote needs one unambiguous earlier standard of the same role"
                )
            standard, (base, measure, period, verb) = candidates[0]
            prior = sources[role][standard]
            if (
                row.acquisition_ref is None
                and (
                    row.provenance.sentence != prior.provenance.sentence + 1
                    or role == "rate"
                    and quotes["extent"]
                )
                or row.measure
                and row.measure != measure
                or row.marker
                and period
                and row.marker != period
                or role == "rate"
                and row.verb != verb
            ):
                return decline(
                    "an omitted standard must refer directly to the preceding compatible quote"
                )
            factor = (
                evaluate(
                    "1 + sign * fraction",
                    {"sign": row.sign, "fraction": row.value},
                    ctx.log,
                    source="relative-rate-factor",
                )
                if row.sign
                else row.value
            )
            value = evaluate(
                "base * factor",
                {"base": base, "factor": factor},
                ctx.log,
                source="scoped-relative-quantity",
            )
        else:
            value, measure, period, verb = row.value, row.measure, row.marker, row.verb
        if not isfinite(value) or value < 0:
            return decline(
                "relative quantities cannot produce negative or nonfinite amounts"
            )
        if role == "extent":
            period = row.marker or row.attribute or period
        quotes[role][scope] = (value, measure, period, verb)
        sources[role][scope] = row
    rates, extents = quotes["rate"], quotes["extent"]
    if not rates or rates.keys() != extents.keys():
        return decline("every scope needs its own rate and extent")
    if ctx.query.get("quantity") == "currency" and any(
        not ctx.reg.word_in_category(value[1], "currency_measure")
        for value in rates.values()
    ):
        return decline("a monetary question requires monetary component rates")
    if ctx.query.get("span_unit"):
        expected[ctx.question.sentence_index][float(ctx.query["span_value"])] += 1
    if uncovered_document_units(
        ctx.premises, ctx.question, ctx.match.consumed
    ) or audit_numeric_mentions(
        (*ctx.premises, ctx.question),
        expected,
        missing="missing",
        duplicate="duplicate",
    ):
        return decline("every quote, extent and condition must belong to this account")
    unit = ctx.query.get("measure") or next(iter(rates.values()))[1]
    amounts = []
    for scope, (value, measure, period, verb) in rates.items():
        if not predicates_compatible(verb, ctx.query["verb"], measure, ctx.reg):
            return decline("the requested activity must match every component rate")
        elapsed, elapsed_unit, window, _ = extents[scope]
        if window and reporting and window != reporting:
            return decline(
                "the stated schedule and requested reporting period must agree"
            )
        duration = convert_duration(
            elapsed,
            elapsed_unit,
            period,
            ctx.reg,
            ctx.log,
            source="scoped-rate-extent-unit",
        )
        if duration is None:
            return decline(
                "each elapsed extent must be compatible with its own rate denominator"
            )
        rate = Rate(
            provenance=sources["rate"][scope].provenance,
            entity=actor.head,
            measure=measure,
            per=period,
            value=value,
            verb=verb,
        )
        amount = apply_rate(rate, duration, ctx.log, source="scoped-rate-component")
        amount = convert_units(
            amount, measure, unit, ctx.reg, ctx.log, source="scoped-rate-output-unit"
        )
        if amount is None:
            return decline("component outputs must have compatible requested units")
        amounts.append(amount)
    total = evaluate(
        " + ".join(str(value) for value in amounts),
        {},
        ctx.log,
        source="scoped-rate-total",
    )
    if ctx.query.get("projection"):
        if spans and ctx.query.get("span_unit") or not reporting:
            return decline(
                "a projected total needs exactly one span and an explicit schedule cadence"
            )
        span_unit = spans[0].measure if spans else ctx.query.get("span_unit")
        span_value = spans[0].value if spans else ctx.query.get("span_value")
        if span_unit is None or span_value is None:
            return decline("the projected account has no stated time span")
        periods = convert_duration(
            float(span_value),
            span_unit,
            reporting,
            ctx.reg,
            ctx.log,
            source="scoped-account-projection-periods",
        )
        if periods is None or periods < 0:
            return decline("the projection span and reporting cadence are incompatible")
        total = evaluate(
            "subtotal * periods",
            {"subtotal": total, "periods": periods},
            ctx.log,
            source="scoped-account-projection-total",
        )
    ctx.log.consumed_batch_keys.update(row.key() for row in rows)
    return Answer(
        "number",
        total,
        "sum each scope’s own rate multiplied by its stated extent for the reporting period",
        assumptions=(AnswerAssumption("extent-reporting-period",
            f"The stated work amounts are treated as totals for the requested {reporting}.",
            tuple(sorted({r.provenance.sentence for r in rows if r.kind in {"scoped-extent", "scoped-relative-extent"}}))),)
        if reporting and not windows else (),
    )
