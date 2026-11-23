"""Project an observed amount using a rate or a recurring work schedule."""

from dataclasses import replace

from . import consumer
from ..answer import Answer, AnswerAssumption
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..evaluate import evaluate
from ..model import BatchEvidence, Quantity
from ..rate_calculation import apply_ratio, convert_exact_duration, convert_units
from ..reference_identity import constrains, reference_from_unit
from ..resource_equations import resource_residual


@consumer(
    "quantity-projection",
    applicable=lambda store: any(
        row.kind in {"projected-pay", "projected-increase"}
        for row in store.by_kind(BatchEvidence)
    ),
)
def quantity_projection(ctx):
    rows = list(ctx.store.by_kind(BatchEvidence))
    actor = ctx.query_reference()
    if (actor is None or not actor.resolved or not rows
            or any(row.entity_ref != actor or row.value < 0 for row in rows)):
        return Answer("decline", None, "the projection needs one participant and compatible amounts")
    if ctx.query["mode"] == "savings":
        return _savings(ctx, rows, actor)
    return _dimension(ctx, rows)


def _dimension(ctx, rows):
    amounts = list(ctx.store.by_kind(Quantity))
    rates = [row for row in rows if row.kind == "projected-increase"]
    if len(rows) != 1 or len(amounts) != 1 or len(rates) != 1:
        return Answer("decline", None, "the projection needs one current measurement and one rate")
    current, rate = amounts[0], rates[0]
    axis = ctx.reg.attribute_value(ctx.query["dimension"], "projection_axis")
    evidence = [current, rate]
    if (axis is None or current.measurement_axis is None
            or ctx.reg.attribute_value(current.measurement_axis, "projection_axis") != axis
            or current.entity_ref != rate.entity_ref or current.time or rate.provenance.assumption or not closed_evidence(
                ctx, evidence, [(row, [row.value]) for row in evidence]
            )):
        return Answer("decline", None, "the current measurement and requested dimension must agree")
    span = convert_exact_duration(float(ctx.query["span_value"]), ctx.query["span_unit"], rate.container,
                                  ctx.reg, ctx.log, source="extent-projection-window")
    increment = convert_units(rate.value, rate.measure, current.measure, ctx.reg, ctx.log,
                              source="extent-projection-unit")
    if span is None or increment is None or span < 0:
        return Answer("decline", None, "the extent and rate must have compatible units")
    value = evaluate("current + rate * span", dict(current=current.value, rate=increment, span=span),
                     ctx.log, source="linear-projection")
    return finish_batch_answer(ctx, evidence, value, "add the stated increase over the requested interval")


def _savings(ctx, rows, actor):
    quantities = list(ctx.store.by_kind(Quantity))
    wages = [row for row in rows if row.kind == "projected-pay"]
    prices = [row for row in rows if row.kind == "projected-savings-outlay"]
    spans = [row for row in rows if row.kind == "projected-tenure"] + quantities
    evidence = rows + quantities
    if (len(evidence) != 3 or len(wages) != 1 or len(prices) != 1 or len(spans) != 1
            or any(row.provenance.assumption for row in evidence)):
        return Answer("decline", None, "the balance needs one work schedule, savings duration and price")
    wage, tenure, price = wages[0], spans[0], prices[0]
    if isinstance(tenure, Quantity) and (
        tenure.entity_ref != actor or tenure.time or tenure.measure_qualifier
        or not ctx.reg.word_in_category(tenure.verb, "crew_activity")
        or not ctx.reg.word_in_category(tenure.measure, "duration_measure")
    ):
        return Answer("decline", None, "the duration must belong to the same work schedule")
    explicit_duration = isinstance(tenure, Quantity) or tenure.marker == "explicit"
    target = ctx.query_reference("target")
    owner = ctx.match.slots.get("owner")
    if (target is None or target.owner not in (None, actor) or price.container_ref is None
            or not constrains(replace(target, owner=None), price.container_ref)
            or price.verb != ctx.query["verb"]
            or reference_from_unit(ctx.match.slots["actor"]) != actor
            or owner is not None and reference_from_unit(owner) != actor
            or not closed_evidence(
                ctx, evidence, [(wage, [wage.value, wage.per_member]),
                                (tenure, [tenure.value] if explicit_duration else []), (price, [price.value])]
            )):
        return Answer("decline", None, "the quoted purchase, saving and question must refer to the same plan")
    span = convert_exact_duration(tenure.value, tenure.measure, wage.marker, ctx.reg, ctx.log,
                                  source="work-savings-duration")
    assumptions = ()
    if span is None and ctx.reg.word_in_category(wage.marker, "calendar_week_unit"):
        weeks = ctx.reg.attribute_value(tenure.measure, "undated_budget_weeks")
        if weeks:
            span = tenure.value * weeks
            assumptions = (
                AnswerAssumption(
                    "undated-work-budget-weeks",
                    f"Treat each undated {tenure.measure} as {weeks:g} scheduled weeks.",
                    (wage.provenance.sentence, tenure.provenance.sentence),
                ),
            )
    expenditure = convert_units(price.value, price.measure, wage.measure, ctx.reg, ctx.log,
                                source="work-savings-currency")
    available_time = convert_exact_duration(1, wage.marker, wage.container, ctx.reg, ctx.log,
                                            source="work-period-length")
    if span is None or expenditure is None or available_time is None or wage.per_member > available_time:
        return Answer("decline", None, "the schedule and price need compatible periods and currency")
    earn_per_period = apply_ratio(wage.value, 1, wage.per_member, ctx.log, source="scheduled-earnings")
    saved = apply_ratio(earn_per_period, 1, span, ctx.log, source="scheduled-savings")
    value = resource_residual([saved], [expenditure], ctx.log, source="projected-purchase-balance")
    if value is None or value < 0:
        return Answer("decline", None, "the projected savings do not cover the purchase")
    return finish_batch_answer(ctx, evidence, value, "subtract the purchase from retained earnings", assumptions=assumptions)
