"""Compute a period's shortfall, or carry daily minimums forward."""

from collections import Counter, defaultdict
from math import isfinite

from . import consumer
from ..answer import Answer, AnswerAssumption
from ..evaluate import evaluate
from ..model import BatchEvidence
from ..numeric_evidence import audit_numeric_mentions
from ..reference_bindings import referenced_forms_agree
from ..reference_identity import ReferenceIdentity, reference_from_unit
from ..reporting_periods import reporting_period
from ..resource_equations import resource_residual
from ..source_coverage import covered_temporal_annotation, uncovered_document_units


@consumer("recurring-goal-shortfall")
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = sorted(
        ctx.store.by_kind(BatchEvidence),
        key=lambda r: (r.provenance.sentence, r.position),
    )
    goals = [row for row in rows if row.kind == "recurring-minimum-goal"]
    history = [row for row in rows if row.kind == "indexed-performance"]
    cumulative = [row for row in rows if row.kind == "performance-progress-to-date"]
    plans = [row for row in rows if row.kind == "make-up-intention"]
    annotations = [
        fact for fact in ctx.store.facts if not isinstance(fact, BatchEvidence)
    ]
    if (
        len(goals) != 1
        or not (history or cumulative)
        or len(rows) != len(goals) + len(history) + len(plans) + len(cumulative)
        or ctx.store.collisions
        or ctx.store.quarantined
    ):
        return decline(
            "one recurring goal and a performance history are required"
        )
    goal = goals[0]
    actor = reference_from_unit(ctx.match.slots["who"])
    if not referenced_forms_agree((*ctx.premises, ctx.question), actor, ctx.reg):
        return decline(
            "the participant and goal owners need compatible reference forms"
        )
    periods = {
        (row.provenance.sentence, row.marker) for row in (*history, *plans, *cumulative)
    }
    for fact in annotations:
        if not covered_temporal_annotation(fact, ctx.premises, actor.head, periods):
            return decline(
                "an additional event lies outside the stated performance and make-up plan"
            )
    if (
        any(
            row.entity_ref != actor
            or row.measure != ctx.query["measure"]
            or row.provenance.assumption
            or not isfinite(row.value)
            or row.value < 0
            or not float(row.value).is_integer()
            for row in rows
        )
        or goal.provenance.sentence
        >= min(row.provenance.sentence for row in (*history, *cumulative))
        or any(
            reference_from_unit(ctx.match.slots[slot]) != actor
            for slot in ("owner", "subject")
            if slot in ctx.match.slots
        )
    ):
        return decline(
            "the target, actual work, make-up intention and question must describe one participant and unit"
        )
    calendar_indices = {
        attributes["weekday_index"]
        for word, attributes in ctx.reg.attrs.items()
        if "weekday_index" in attributes
        and ctx.reg.word_in_category(word, "named_weekday")
    }
    cycle = len(calendar_indices)
    if goal.container_ref is None or any(
        not any(
            ctx.reg.word_in_category(qualifier, category)
            for category in (
                "performance_goal_context",
                "goal_recurrence_descriptor",
                "minimum_goal_descriptor",
            )
        )
        for qualifier in goal.container_ref.qualifiers
    ):
        return decline(
            "the goal has an unsupported qualifier or recurrence restriction"
        )
    declared = {goal.marker} if goal.marker else set()
    for qualifier in goal.container_ref.qualifiers:
        if not ctx.reg.word_in_category(qualifier, "goal_recurrence_descriptor"):
            continue
        units = {
            ctx.reg.plural_to_singular.get(unit, unit)
            for unit in ctx.reg.cat_members_deep("reporting_period_unit")
            if ctx.reg.attribute_applies_to(qualifier, unit)
        }
        if len(units) != 1:
            return decline("the goal descriptor needs one declared reporting unit")
        declared.update(units)
    if len(declared) > 1:
        return decline("the goal states conflicting recurrence periods")
    cadence = next(iter(declared), "")
    daily = ctx.reg.word_in_category(cadence, "calendar_day_unit")
    if ctx.query.get("mode") == "condition":
        return _condition_shortfall(ctx, rows, goal, history, cadence, actor)
    named_day_history = all(
        row.acquisition_ref is None or row.acquisition_ref == ReferenceIdentity(row.marker)
        for row in history
    )
    if cycle and ctx.reg.word_in_category(cadence, "calendar_week_unit"):
        if plans or cumulative and (history or len(cumulative) != 1):
            return decline(
                "a cycle quota cannot add overlapping cumulative progress or daily make-up plans"
            )
        observations = [*history, *cumulative]
        indices = [
            ctx.reg.attrs.get(row.marker, {}).get("weekday_index")
            for row in observations
        ]
        asked = ctx.reg.attrs.get(ctx.query.get("day", ""), {}).get("weekday_index")
        if (
            not named_day_history
            or any(index is None for index in indices)
            or len(set(indices)) != len(indices)
            or indices != sorted(indices)
            or asked is not None
            and any(index >= asked for index in indices)
        ):
            return decline(
                "the observed work must belong to the same cycle and precede the requested day"
            )
        expected = defaultdict(Counter)
        for row in [goal, *observations]:
            expected[row.provenance.sentence][row.value] += 1
        if uncovered_document_units(
            ctx.premises, ctx.question, ctx.match.consumed
        ) or audit_numeric_mentions(
            (*ctx.premises, ctx.question),
            expected,
            missing="missing",
            duplicate="duplicate",
        ):
            return decline(
                "every quota, observation and period restriction must be read"
            )
        value = max(
            0,
            resource_residual(
                [goal.value],
                [row.value for row in observations],
                ctx.log,
                source="cycle-goal-remainder",
            ),
        )
        ctx.log.consumed_batch_keys.update(row.key() for row in rows)
        return Answer(
            "number",
            value,
            "the remaining cycle quota after stated progress, capped at zero when the goal is met",
        )
    if cumulative or cadence and not daily:
        return decline(
            "daily carryover needs indexed daily work; other quota periods need an explicit compatible scope"
        )
    indices = [
        ctx.reg.attrs.get(row.marker, {}).get("weekday_index") for row in history
    ]
    asked = ctx.reg.attrs.get(ctx.query["day"], {}).get("weekday_index")
    if (
        not cycle
        or calendar_indices != set(range(cycle))
        or asked is None
        or not named_day_history
        or any(index is None for index in indices)
        or len(set(indices)) != len(indices)
        or any(
            (after - before) % cycle != 1 for before, after in zip(indices, indices[1:])
        )
        or (asked - indices[-1]) % cycle != 1
    ):
        return decline(
            "daily observations must be consecutive and end immediately before the requested day"
        )
    for plan in plans:
        actual = [
            row
            for row in history
            if row.provenance.sentence == plan.provenance.sentence
        ]
        next_index = ctx.reg.attrs.get(plan.marker, {}).get("weekday_index")
        if (
            len(actual) != 1
            or next_index is None
            or (next_index - ctx.reg.attrs[actual[0].marker]["weekday_index"]) % cycle
            == 0
        ):
            return decline("a make-up intention must identify a later named day")
    expected = defaultdict(Counter)
    expected[goal.provenance.sentence][goal.value] += 1
    for row in history:
        expected[row.provenance.sentence][row.value] += 1
    if uncovered_document_units(
        ctx.premises, ctx.question, ctx.match.consumed
    ) or audit_numeric_mentions(
        (*ctx.premises, ctx.question),
        expected,
        missing="missing",
        duplicate="duplicate",
    ):
        return decline("every target, observation and make-up condition must be read")
    arrears = 0
    for row in history:
        arrears = max(
            0,
            resource_residual(
                [arrears, goal.value],
                [row.value],
                ctx.log,
                source="carried-minimum-shortfall",
            ),
        )
    value = evaluate(
        "minimum + arrears",
        {"minimum": goal.value, "arrears": arrears},
        ctx.log,
        source="next-day-minimum-with-make-up",
    )
    ctx.log.consumed_batch_keys.update(row.key() for row in rows)
    reason = (
        "carry unmet daily minimums forward, then add the requested day’s own minimum"
    )
    if not goal.marker:
        reason += "; interpreting the target as applying to each named day in the make-up schedule"
    return Answer("number", value, reason, assumptions=() if goal.marker else (
        AnswerAssumption("daily-goal-with-carryover",
            "The unqualified target is a daily minimum, with missed amounts carried forward.",
            (goal.provenance.sentence,)),
    ))


def _period_position(reference, cadence, reg):
    if not reference or not reference.resolved or reference.owner or reference.label:
        return None
    if not reference.qualifiers:
        for unit, names, attribute in (
            ("calendar_day_unit", "named_weekday", "weekday_index"),
            ("calendar_month_unit", "named_month", "month_index"),
        ):
            if reg.word_in_category(cadence, unit) and reg.word_in_category(reference.head, names):
                index = reg.attribute_value(reference.head, attribute)
                return (attribute, index) if index is not None else None
    if reference.head != cadence or len(reference.qualifiers) != 1:
        return None
    (qualifier,) = reference.qualifiers
    ordinal = reg.attribute_value(qualifier, "ordinal_index")
    if ordinal is not None and reg.word_in_category(qualifier, "holder_ordinal"):
        return "ordinal", ordinal
    relative = reporting_period(reference, reg)
    if relative is not None:
        return "relative", relative.offset
    return None


def _condition_shortfall(ctx, rows, goal, history, cadence, actor):
    def decline(reason):
        return Answer("decline", None, reason)

    period = ctx.query_reference("period")
    requested_position = _period_position(period, cadence, ctx.reg)
    if not cadence or period is None or period.head != cadence and requested_position is None:
        return decline("the question needs an explicit goal at the requested recurrence")
    if period.qualifiers and requested_position is None:
        return decline("the requested period needs a recognized ordinal or relative reference")
    if not history or any(row.kind == "performance-progress-to-date" for row in rows):
        return decline("a condition-specific shortfall needs individual period totals")

    observations = {}
    for row in history:
        reference = row.acquisition_ref or ReferenceIdentity(row.marker)
        position = _period_position(reference, cadence, ctx.reg)
        if position is None or position in observations:
            return decline("each observation needs a distinct period at the goal recurrence")
        observations[position] = row
    if len({position[0] for position in observations}) != 1:
        return decline("the observed periods need a common frame of reference")
    matches = [
        row for position, row in observations.items()
        if (requested_position is None or position == requested_position)
        and (attribution := row.provenance.attribution) is not None
        and attribution.reason_actor == actor
        and attribution.reason_predicate == ctx.query["condition"]
        and any(ref.resolved and ref.head == ctx.query["state"]
                for ref in attribution.reason_entities)
    ]
    if len(matches) != 1:
        return decline("one observed period must match the stated condition")
    expected = defaultdict(Counter)
    for row in [goal, *history]:
        expected[row.provenance.sentence][row.value] += 1
    if uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed) or audit_numeric_mentions(
        (*ctx.premises, ctx.question), expected, missing="missing", duplicate="duplicate",
    ):
        return decline("every target, observation and condition must be read")
    value = max(0, resource_residual([goal.value], [matches[0].value], ctx.log,
                                     source="condition-specific-shortfall"))
    ctx.log.consumed_batch_keys.update(row.key() for row in rows)
    return Answer("number", value, "subtract the observed work in the identified period from its target")
