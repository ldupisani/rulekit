"""Carry unmet recurring minimums through an explicit, gap-free daily history."""

from collections import Counter, defaultdict
from math import isfinite

from . import consumer
from ..answer import Answer
from ..evaluate import evaluate
from ..model import BatchEvidence
from ..numeric_evidence import audit_numeric_mentions
from ..reference_bindings import referenced_forms_agree
from ..reference_identity import reference_from_unit
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
            "one recurring goal and a complete daily performance history are required"
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
                "an additional event lies outside the stated daily performance and make-up plan"
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
    declared = (
        {
            ctx.reg.attrs[q]["goal_cycle_days"]
            for q in goal.container_ref.qualifiers
            if "goal_cycle_days" in ctx.reg.attrs.get(q, {})
        }
        if goal.container_ref
        else set()
    )
    if goal.marker:
        if ctx.reg.word_in_category(goal.marker, "daily_recurrence_unit"):
            declared.add(1)
        elif ctx.reg.word_in_category(goal.marker, "weekday_cycle_period"):
            declared.add(cycle)
        else:
            return decline(
                "the goal period cannot be determined from this named-day history"
            )
    if len(declared) > 1:
        return decline("the goal states conflicting recurrence periods")
    cadence = next(iter(declared), 0)
    if goal.container_ref is None or any(
        not any(
            ctx.reg.word_in_category(qualifier, category)
            for category in (
                "performance_goal_context",
                "daily_goal_descriptor",
                "weekly_goal_descriptor",
                "minimum_goal_descriptor",
            )
        )
        for qualifier in goal.container_ref.qualifiers
    ):
        return decline(
            "the goal has an unsupported qualifier or recurrence restriction"
        )
    if cycle and cadence == cycle:
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
            any(index is None for index in indices)
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
    if cumulative or cadence not in (0, 1):
        return decline(
            "daily carryover needs indexed daily work; other quota periods need an explicit compatible scope"
        )
    indices = [
        ctx.reg.attrs.get(row.marker, {}).get("weekday_index") for row in history
    ]
    asked = ctx.reg.attrs.get(ctx.query["day"], {}).get("weekday_index")
    calendar_indices = {
        attributes["weekday_index"]
        for word, attributes in ctx.reg.attrs.items()
        if "weekday_index" in attributes
        and ctx.reg.word_in_category(word, "named_weekday")
    }
    cycle = len(calendar_indices)
    if (
        not cycle
        or calendar_indices != set(range(cycle))
        or asked is None
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
    return Answer("number", value, reason)
