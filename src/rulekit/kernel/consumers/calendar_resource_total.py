"""Finite calendar schedules with explicit exception days and stated assumptions."""

from collections import Counter, defaultdict
from calendar import isleap
from math import isfinite
from . import consumer
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..answer import Answer
from ..model import BatchEvidence, Rate
from ..reference_identity import ReferenceIdentity, reference_from_unit, constrains
from ..evaluate import evaluate
from ..rate_calculation import rate_operands, convert_units
from ..predicate_compatibility import predicates_compatible
from ..source_coverage import (
    uncovered_document_units,
    covered_temporal_annotation,
)
from ..numeric_evidence import audit_numeric_mentions
from ..learn import simple_rate_evidence_units
from ..source_coverage import uncovered_units
from ..resource_equations import resource_residual


@consumer("calendar-resource-total")
def consume(ctx):
    rows = list(ctx.store.by_kind(BatchEvidence))
    rates = list(ctx.store.by_kind(Rate))
    operands = []
    facts = [*rows, *rates]
    op = ctx.query["operation"]
    covered = {}
    for rate in rates:
        reading = next(
            (r for r in ctx.premises if r.sentence_index == rate.provenance.sentence),
            None,
        )
        footprint = (
            simple_rate_evidence_units(reading, rate, ctx.reg) if reading else ()
        )
        if (
            reading is None
            or not footprint
            and uncovered_units(reading)
            or any(
                reference_from_unit(u).described
                for u in reading.units
                if u.sense() in ("noun", "name", "pronoun")
            )
        ):
            return Answer(
                "decline",
                None,
                "each ordinary rate must have a complete, unqualified source clause",
            )
        covered[reading.sentence_index] = footprint

    def fail(s):
        return Answer("decline", None, s)

    if op == "week":
        base = [r for r in rows if r.kind == "schedule-baseline"]
        changes = [r for r in rows if r.kind == "schedule-exception"]
        sites = [r for r in rows if r.kind == "schedule-site"]
        direct_base = bool(base)
        if not base and len(rates) == 1:
            rate = rates[0]
            base = [
                BatchEvidence(
                    provenance=rate.provenance,
                    kind="schedule-baseline",
                    entity=rate.entity,
                    entity_ref=ReferenceIdentity(rate.entity),
                    measure=rate.measure,
                    value=rate.value,
                    marker=rate.per,
                    verb=rate.verb,
                    position=0,
                )
            ]
        if (
            len(base) != 1
            or direct_base
            and rates
            or len(rates) > 1
            or len(sites) > 1
            or len(rows) != int(direct_base) + len(changes) + len(sites)
        ):
            return fail(
                "one daily baseline and explicit weekday exceptions are required"
            )
        base = base[0]
        if (
            not constrains(ctx.query_reference(), base.entity_ref)
            or base.measure != ctx.query["measure"]
            or ctx.reg.attribute_value(base.marker, "calendar_day_unit") != 1
            or ctx.reg.attribute_value(ctx.query["period"], "calendar_week_unit") != 1
            or base.verb != ctx.query["verb"]
            or any(r.entity_ref != base.entity_ref for r in rows)
            or sites
            and sites[0].container != ctx.query["site"]
        ):
            return fail("the actor, activity and open-site schedule must agree")
        first = ctx.reg.attribute_value(ctx.query["first"], "weekday_index")
        last = ctx.reg.attribute_value(ctx.query["last"], "weekday_index")
        if first is None or last is None:
            return fail("the weekday window is unknown")
        cycle = sorted(
            {a["weekday_index"] for a in ctx.reg.attrs.values() if "weekday_index" in a}
        )
        window = [
            (first + i) % len(cycle)
            for i in range(int((last - first) % len(cycle)) + 1)
        ]
        if len({r.marker for r in changes}) != len(changes):
            return fail("a weekday has competing exceptions")
        values = [base.value] * len(window)
        for r in changes:
            index = ctx.reg.attribute_value(r.marker, "weekday_index")
            if index not in window or r.measure != base.measure or r.verb != base.verb:
                return fail(
                    "an exception falls outside the stated schedule or activity"
                )
            values[window.index(index)] = evaluate(
                "base * (1 + delta)",
                dict(base=base.value, delta=r.value),
                ctx.log,
                source="weekday-rate-exception",
            )
        operands = [
            (base, [base.value]),
            *((r, [r.value]) for r in changes),
            *((r, []) for r in sites),
        ]
        value = evaluate(
            " + ".join(map(str, values)), {}, ctx.log, source="open-week-total"
        )
        metadata = [f for f in ctx.store.facts if f not in facts]
        periods = {(r.provenance.sentence, r.marker) for r in changes}
        if any(
            not covered_temporal_annotation(f, ctx.premises, base.entity, periods)
            for f in metadata
        ):
            return fail("an additional event lies outside the weekly schedule")
        facts += metadata
        reason = (
            ("Approximate total; " if any(r.attribute for r in changes) else "")
            + "ordinary-day baseline with the stated weekday exceptions, over the inclusive opening schedule"
        )
    elif op == "months":
        schedules = [r for r in rows if r.kind == "calendar-months"]
        portions = [r for r in rows if r.kind == "daily-portion"]
        if (
            len(schedules) != 1
            or not portions
            or rates
            or len(rows) != 1 + len(portions)
        ):
            return fail("one month schedule and complete daily portions are required")
        schedule = schedules[0]
        months = schedule.members
        metadata = [f for f in ctx.store.facts if f not in facts]
        if any(
            not covered_temporal_annotation(
                f,
                ctx.premises,
                schedule.entity,
                {(schedule.provenance.sentence, m) for m in months},
            )
            for f in metadata
        ):
            return fail("an additional event lies outside the calendar schedule")
        facts += metadata
        if (
            len(months) != int(float(ctx.query["month_count"]))
            or len(set(months)) != len(months)
            or not constrains(ctx.query_reference(), schedule.entity_ref)
            or len({r.marker for r in portions}) != len(portions)
            or any(
                r.entity_ref != schedule.entity_ref or r.verb != schedule.verb
                for r in portions
            )
        ):
            return fail(
                "the requested month count, participant and daily portions must agree"
            )
        year = int(schedule.subtotal) if schedule.subtotal else None
        if year is not None and (not 1 <= year <= 9999 or schedule.subtotal != year):
            return fail("the calendar year must be explicit and valid")
        length = "leap_year_days" if year and isleap(year) else "common_year_days"
        recipients = [
            u
            for rd in ctx.premises
            if rd.sentence_index == schedule.provenance.sentence
            for u in rd.units
            if u.features.get("lemma") == schedule.container and u.sense() == "noun"
        ]
        if len(recipients) != 1:
            return fail("the daily portions need one explicit recipient group")
        for r in portions:
            entry = ctx.reg.lexicon.get(r.container)
            form = entry.anaphoric_form if entry else None
            if (
                form is None
                or recipients[0].features.get("number") not in form.referent_numbers
            ):
                return fail(
                    "the portion recipient pronoun must agree with the scheduled recipients"
                )
        days = [ctx.reg.attribute_value(m, length) for m in months]
        if any(v is None for v in days):
            return fail("month lengths are unknown")
        amounts = []
        for r in portions:
            if not isfinite(r.value) or r.value < 0:
                return fail("daily portions must be finite and nonnegative")
            v = convert_units(
                r.value,
                r.measure,
                ctx.query["measure"],
                ctx.reg,
                ctx.log,
                source="daily-portion-unit",
            )
            if v is None:
                return fail("daily portions use incompatible units")
            amounts.append(v)
        value = evaluate(
            "daily * days",
            dict(daily=sum(amounts), days=sum(days)),
            ctx.log,
            source="named-month-resource-total",
        )
        operands = [
            (schedule, [schedule.subtotal] if schedule.subtotal else []),
            *((r, [r.value]) for r in portions),
        ]
        # The month count occurs in the question, rather than in the schedule evidence.
        expected = defaultdict(Counter)
        for r, vs in operands:
            expected[r.provenance.sentence].update(vs)
        expected[ctx.question.sentence_index][float(ctx.query["month_count"])] += 1
        if (
            ctx.store.collisions
            or ctx.store.quarantined
            or len(facts) != len(ctx.store.facts)
            or uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)
            or audit_numeric_mentions(
                (*ctx.premises, ctx.question),
                expected,
                missing="missing",
                duplicate="duplicate",
            )
        ):
            return fail("every daily portion and calendar condition must be read")
        return finish_batch_answer(
            ctx,
            facts,
            value,
            f'{"Calendar year "+str(year) if year else "Assuming a non-leap year"}: {sum(days):g} days, with all stated portions supplied every day',
        )
    elif op == "savings":
        groups = [r for r in rows if r.kind == "saving-group"]
        shares = [r for r in rows if r.kind == "saving-share"]
        if len(groups) != 1 or len(shares) != 1 or len(rows) != 2 or len(rates) != 2:
            return fail(
                "one explicit saving group, shared policy and each participant’s income are required"
            )
        group, share = groups[0], shares[0]
        if (
            group.entity != ctx.query.get("event", group.entity)
            or share.entity != group.entity
            or {r.entity for r in rates} != {group.container, group.acquisition}
            or group.container_ref == group.acquisition_ref
            or not 0 <= share.value <= 1
            or len({r.per for r in rates}) != 1
            or len({r.measure for r in rates}) != 1
            or any(not ctx.reg.word_in_category(r.verb, "income_action") for r in rates)
            or any(
                ctx.reg.attribute_value(r.per, "calendar_day_unit") != 1 for r in rates
            )
        ):
            return fail("the joint policy must cover exactly these two daily incomes")
        days = ctx.reg.attribute_value(ctx.query["period"], "common_year_days")
        if days is None:
            return fail("the annual earning-day interpretation is unknown")
        value = evaluate(
            "income * fraction * days",
            dict(
                income=resource_residual(
                    [r.value for r in rates], [], ctx.log, source="joint-daily-income"
                ),
                fraction=share.value,
                days=days,
            ),
            ctx.log,
            source="joint-calendar-savings",
        )
        operands = [
            (group, []),
            (share, [share.value]),
            *((r, rate_operands(r)) for r in rates),
        ]
        reason = f"Assuming both earn on all {days:g} days of the year, and each saves the stated share"
    else:
        return fail("unsupported calendar schedule operation")
    if any(
        not isfinite(r.value) or r.value < 0 for r in (*rows, *rates)
    ) or not closed_evidence(ctx, facts, operands, covered=covered):
        return fail("every quantity, schedule and condition must be explained")
    return finish_batch_answer(ctx, facts, value, reason)
