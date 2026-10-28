"""Fund recurring active-period costs through work in its complementary window."""
from collections import Counter, defaultdict
from dataclasses import replace
from math import isfinite

from . import consumer
from ..answer import Answer
from ..evaluate import evaluate
from ..model import BatchEvidence, EarningRate, Rate, ServiceScope
from ..numeric_evidence import audit_numeric_mentions
from ..rate_calculation import apply_rate, convert_duration
from ..source_coverage import uncovered_document_units
from ..reference_identity import constrains


@consumer("cyclic-saving-average")
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)
    rows = ctx.store.by_kind(BatchEvidence)
    costs, tariffs, tasks = (ctx.store.by_kind(k) for k in (Rate, EarningRate, ServiceScope))
    kinds = ("expense-purpose", "active-period", "inactive-saving-plan")
    scopes = [r for r in rows if r.kind == "expense-active-period"]
    if (len(scopes) > 1 or len(rows) != 3 + len(scopes)
            or any(sum(r.kind == k for r in rows) != 1 for k in kinds)
            or len(costs) != 1 or len(tariffs) != 1 or not tasks
            or any(not isinstance(f, (BatchEvidence, Rate, EarningRate, ServiceScope)) for f in ctx.store.facts)
            or ctx.store.collisions or ctx.store.quarantined):
        return decline("one recurring cost, active period, complementary saving plan and uniform task price are required")
    purpose, active, plan = (next(r for r in rows if r.kind == k) for k in kinds)
    cost, tariff = costs[0], tariffs[0]
    who = ctx.query["entity"]
    scope = scopes[0] if scopes else None

    def period_reference(row):
        ref = row.container_ref
        if ref is not None and (row.marker == "measured-period" or row.attribute == "measured-period"):
            # The counted modifier measures the period; other modifiers still
            # identify the activity. Its possessor is explicitly bound by the
            # complete expense construction, even if count condensation kept
            # the determiner separate from the nominal unit.
            ref = replace(ref, qualifiers=tuple(q for q in ref.qualifiers if q != row.measure),
                          owner=ref.owner or row.entity_ref)
        return ref

    active_ref = period_reference(active)
    if scope is not None:
        scope_ref = period_reference(scope)
        if (scope.attribute != who or scope.provenance.sentence != purpose.provenance.sentence
                or scope_ref is None or active_ref is None
                or not (constrains(scope_ref, active_ref) or constrains(active_ref, scope_ref))):
            return decline("the expense must explicitly name the same owned active period")
    period_qualifiers = set(active_ref.qualifiers if active_ref else ())
    if scope is not None:
        period_qualifiers.update(scope_ref.qualifiers)
    if (len(period_qualifiers) > 1
            or period_qualifiers and any(
                named and named not in period_qualifiers for named in (purpose.attribute, plan.container))
            or scope is None and period_qualifiers and not period_qualifiers.intersection(
                (purpose.attribute, plan.container))):
        return decline("the expense period and saving activity must agree")
    if scope is None and plan.container and not purpose.attribute:
        return decline("a named activity does not establish when an unrelated recurring expense is incurred")
    if (any(f.entity != who for f in [*rows, cost, tariff]) or ctx.query["owner"] != who
            or purpose.measure != ctx.query["target"] or tariff.basis != "uniform-service"
            or purpose.container and purpose.container != who
            or ctx.query.get("target_qualifier") and ctx.query["target_qualifier"] != purpose.attribute
            or purpose.attribute and plan.container and purpose.attribute != plan.container
            or cost.measure != tariff.measure or plan.measure != active.measure
            or not purpose.provenance.sentence < plan.provenance.sentence < tariff.provenance.sentence
            or any(t.entity or t.provenance.sentence != plan.provenance.sentence for t in tasks)
            or len({t.verb for t in tasks}) != len(tasks)
            or any(f.provenance.assumption for f in ctx.store.facts)):
        return decline("the purpose, participant, saving window and quoted activities must agree")
    if any(not isfinite(v) or v <= 0 for v in (cost.value, active.value, tariff.value)):
        return decline("the cost, duration and task price must be positive and finite")
    unit, count = active.marker, active.fraction
    if not unit or not isinstance(count, (int, float)) or count <= 0:
        return decline("the activity period needs an explicit declared enclosing cycle")
    whole = convert_duration(count, unit, active.measure, ctx.reg, ctx.log,
                             source="enclosing-cycle-duration", allow_cadence=True)
    charged_periods = convert_duration(active.value, active.measure, cost.per, ctx.reg, ctx.log, source="active-cost-periods")
    if whole is None or charged_periods is None or whole <= active.value:
        return decline("the active period must leave a positive compatible saving window")
    window = evaluate("whole - active", {"whole": whole, "active": active.value}, ctx.log, source="complementary-saving-window")
    periods = convert_duration(window, active.measure, ctx.query["period"], ctx.reg, ctx.log, source="saving-average-periods")
    if periods is None or periods <= 0:
        return decline("the requested average period must match the saving window")
    expected = defaultdict(Counter)
    expected[cost.provenance.sentence][cost.value] += 1
    expected[active.provenance.sentence][active.value] += 1
    expected[tariff.provenance.sentence][tariff.value] += 1
    if (uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises, ctx.question), expected, missing="missing", duplicate="duplicate",
                                      additional_kinds=("attributive_count",))):
        return decline("every cost, activity and saving condition must be represented")
    total = apply_rate(cost, charged_periods, ctx.log, source="active-period-cost")
    task_count = apply_rate(tariff, total, ctx.log, source="required-task-count", inverse=True)
    value = evaluate("tasks / periods", {"tasks": task_count, "periods": periods}, ctx.log, source="average-tasks-per-saving-period")
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    ctx.log.consumed_earnings_account_keys.update(f.key() for f in [tariff, *tasks])
    return Answer("number", value,
                  f"{total:g} required, earned over {periods:g} saving periods; using the declared {count:g} {unit} cycle for the activity period")
