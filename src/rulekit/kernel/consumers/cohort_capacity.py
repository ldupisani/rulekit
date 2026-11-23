"""Compose provisions, observed occupancy, and reserve capacity over cohorts."""

from math import ceil, isclose

from . import consumer
from ..answer import Answer, AnswerAssumption
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..evaluate import evaluate
from ..model import BatchEvidence
from ..reference_identity import constrains


KINDS = {
    "capacity-provision", "capacity-reservation-demand", "capacity-attendance-plan",
}


@consumer("cohort-capacity", applicable=lambda store: any(
    row.kind in KINDS for row in store.by_kind(BatchEvidence)
))
def cohort_capacity(ctx):
    rows = list(ctx.store.by_kind(BatchEvidence))
    mode = ctx.query["mode"]
    if mode == "provision":
        return _provision(ctx, rows)
    if mode == "reservation":
        return _reservation(ctx, rows)
    return _attendance(ctx, rows)


def _provision(ctx, rows):
    if len(rows) != 1 or rows[0].kind != "capacity-provision":
        return Answer("decline", None, "one complete plan must specify the separate recipient groups")
    plan = rows[0]
    actor = ctx.query_reference()
    amounts = [plan.per_member, plan.value, plan.subtotal]
    if (actor is None or plan.entity_ref != actor or plan.provenance.assumption
            or plan.measure != ctx.query["measure"] or (ctx.query.get("verb") and plan.verb != ctx.query["verb"])
            or not all(float(amount).is_integer() for amount in amounts)
            or not closed_evidence(ctx, rows, [(plan, amounts)])):
        return Answer("decline", None, "all groups and the requested output must belong to the same plan")
    total = _grouped_total(ctx, plan.per_member, plan.value, plan.subtotal)
    assumption = AnswerAssumption(
        "one-item-per-recipient",
        f"Allow one {plan.measure} for each recipient in the stated groups.",
        (plan.provenance.sentence,),
    )
    return finish_batch_answer(ctx, rows, total, "add the recipients in the stated groups",
                               assumptions=(assumption,))


def _reservation(ctx, rows):
    roles = {row.kind: row for row in rows}
    if len(rows) != 2 or set(roles) != {"capacity-reservation-demand", "capacity-reservation-fittings"}:
        return Answer("decline", None, "one reservation demand and one per-unit capacity are required")
    demand, fittings = (roles[kind] for kind in ("capacity-reservation-demand", "capacity-reservation-fittings"))
    actor = ctx.query_reference()
    unit = ctx.query_reference("measure")
    if (actor is None or demand.entity_ref is None or not constrains(actor, demand.entity_ref)
            or demand.container_ref is None or fittings.entity_ref is None or unit is None
            or demand.container != fittings.entity or not constrains(unit, demand.container_ref)
            or not _same_reservation_unit(demand.container_ref, fittings.entity_ref)
            or demand.verb != ctx.query["verb"] or demand.measure != fittings.measure
            or ctx.query.get("people", demand.measure) != demand.measure
            or ctx.query.get("cohort", demand.acquisition) != demand.acquisition
            or fittings.container_ref is None or fittings.acquisition_ref is None
            or fittings.container_ref == fittings.acquisition_ref
            or any(row.provenance.assumption for row in rows)):
        return Answer("decline", None, "the demand, room or vehicle capacity and question must describe the same plan")
    counts = [fittings.per_member, fittings.value, fittings.subtotal]
    if (not all(float(value).is_integer() for value in [demand.value, *counts])
            or not closed_evidence(ctx, rows, [(demand, [demand.value]), (fittings, counts)])):
        return Answer("decline", None, "all stated counts are required and must be whole")
    capacity = _grouped_total(ctx, fittings.per_member, fittings.value, fittings.subtotal)
    if capacity <= 0:
        return Answer("decline", None, "each unit must provide some usable capacity")
    needed = ceil(evaluate("demand / capacity", dict(demand=demand.value, capacity=capacity),
                           ctx.log, source="minimum-capacity-units"))
    return finish_batch_answer(ctx, rows, needed, "add the capacities inside each unit and round the required count up")


def _same_reservation_unit(planned, observed):
    if planned.owner:
        return constrains(planned, observed)
    if observed.owner:
        return (observed.owner.resolved and not observed.owner.described
                and planned.qualifiers == (observed.owner.head,))
    return constrains(planned, observed)


def _attendance(ctx, rows):
    roles = {row.kind: row for row in rows}
    if len(rows) != 2 or set(roles) != {"capacity-attendance-plan", "capacity-attendance-use"}:
        return Answer("decline", None, "one capacity and one occupied share are required")
    plan, used = (roles[kind] for kind in ("capacity-attendance-plan", "capacity-attendance-use"))
    group = ctx.query_reference("measure")
    if (group is None or (plan.measure and group.head != plan.measure)
            or not plan.measure and group.head != used.measure
            and not ctx.reg.word_in_category(group.head, "generic_membership_role")
            or group.owner or group.label or not group.resolved
            or group.qualifiers and group.qualifiers != (plan.attribute,)
            or plan.acquisition.casefold() != ctx.query["event"].casefold()
            or (plan.marker and ctx.reg.plural_to_singular.get(plan.marker, plan.marker) != plan.container)
            or plan.container_ref != used.container_ref
            or plan.verb != used.measure or used.per_member > plan.per_member
            or plan.provenance.assumption or plan.provenance.sentence >= used.provenance.sentence
            or not all(float(value).is_integer() for value in (plan.value, plan.per_member, used.per_member))
            or not closed_evidence(ctx, rows, [(plan, [plan.value, plan.per_member]), (used, [used.value, used.per_member])])):
        return Answer("decline", None, "the capacity, occupants and membership must belong to the same event")
    filled = evaluate("total * (1 - empty_fraction)", dict(total=plan.value, empty_fraction=used.value),
                      ctx.log, source="occupied-capacity-units")
    if not isclose(filled, round(filled), abs_tol=1e-9, rel_tol=0):
        return Answer("decline", None, "the occupied share must give a whole number of units")
    value = _grouped_total(ctx, round(filled), used.per_member, 0)
    assumption = AnswerAssumption(
        "occupied-places-belong-to-group",
        "Count the occupied places as attendees from the stated membership.",
        (plan.provenance.sentence, used.provenance.sentence),
    )
    return finish_batch_answer(ctx, rows, value, "multiply the occupied units by the attendance per unit",
                               assumptions=(assumption,))


def _grouped_total(ctx, groups, per_group, separate):
    return evaluate("groups * per_group + separate",
                    dict(groups=groups, per_group=per_group, separate=separate),
                    ctx.log, source="grouped-capacity")
