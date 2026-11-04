"""Price a declared geometric property through shared formulas and units."""

from math import isfinite

from . import ConsumerContext, consumer
from ..answer import Answer, AnswerAssumption
from ..evaluate import evaluate
from ..properties import Measurement, evaluate_property
from ...data.properties import PropertyError
from ..source_coverage import uncovered_units


@consumer("measure-cost")
def measure_cost(ctx: ConsumerContext):
    op = ctx.query.get("op", "")
    if not ctx.reg.word_in_category(op, "priced_geometry_quantity"):
        return Answer("decline", None, f"unsupported measure operation {op!r}")
    try:
        rate = float(ctx.query.get("rate"))
        dimensions = [
            (ctx.query.get(f"dim{i}"), float(ctx.query[f"val{i}"]))
            for i in range(1, 4)
            if ctx.query.get(f"val{i}") not in (None, "")
        ]
        if not dimensions:
            dimensions = [
                (None, float(ctx.query["d1"])),
                (None, float(ctx.query["d2"])),
            ]
    except (TypeError, ValueError, KeyError):
        return Answer("decline", None, "measure-cost needs measures and a rate")
    if (
        any(not isfinite(v) or v <= 0 for _, v in dimensions)
        or not isfinite(rate)
        or rate < 0
    ):
        return Answer("decline", None, "a measure must be positive")
    quote = ctx.match.slots.get("rate") if ctx.match is not None else None
    if quote is not None and not ctx.reg.word_in_category(
        quote.features.get("lemma", ""), "currency_unit"
    ):
        return Answer(
            "decline", None, "a cost quote needs a concrete monetary denomination"
        )
    raw_tax = ctx.query.get("tax")
    try:
        tax = float(raw_tax) if raw_tax not in (None, "") else None
        if tax is not None and (not isfinite(tax) or tax < 0):
            raise ValueError
    except (TypeError, ValueError):
        return Answer("decline", None, f"unreadable tax rate {raw_tax!r}")
    shapes = ctx.reg.category_members.get("rectangular_costing_shape", ())
    shape = ctx.query.get("shape") or (shapes[0] if len(shapes) == 1 else None)
    if not shape or ctx.reg.derived_attribute(shape, op) is None:
        return Answer("decline", None, "costing needs a declared shape property")
    roles = ctx.reg.property_inputs(shape, op)
    if any(role is None for role, _ in dimensions):
        if len(roles) != len(dimensions):
            return Answer(
                "decline", None, "the dimensions do not identify the priced shape"
            )
        dimensions = [(role, pair[1]) for role, pair in zip(roles, dimensions)]
    units = []
    for i in range(1, len(dimensions) + 1):
        slot = ctx.match.slots.get(f"d{i}") if ctx.match is not None else None
        features = slot.features if slot is not None else {}
        head = features.get("lemma") if features.get("value_kind") == "count" else None
        qualifier = features.get("qualifier")
        if qualifier and ctx.reg.word_in_category(qualifier, "length_unit"):
            # A measured site (e.g. an explicitly sized floor) retains its
            # physical unit on the nominal modifier, rather than on the head.
            if not ctx.reg.word_in_category(head, "costing_surface_site"):
                return Answer(
                    "decline", None, "the measured site needs an explicit costing role"
                )
            unit = qualifier
        elif head and ctx.reg.word_in_category(head, "costing_surface_site"):
            unit = None
        else:
            unit = head
        if unit and not ctx.reg.word_in_category(unit, "length_unit"):
            return Answer(
                "decline", None, "shape dimensions need compatible length units"
            )
        if (
            qualifier
            and not ctx.reg.word_in_category(qualifier, "length_unit")
            and qualifier != dimensions[i - 1][0]
        ):
            return Answer(
                "decline", None, "the geometric dimension has an unread restriction"
            )
        units.append(unit)
    # The old W-by-H site construction states one rectangular site's axes.
    # An unlabelled axis shares the other axis's unit, or the explicit quote
    # basis when neither axis states one. Explicit unit modifiers take priority.
    inferred_axis_unit = len(units) == 2 and not all(units)
    if len(units) == 2 and ctx.match is not None:
        common = next((unit for unit in units if unit), ctx.query.get("rate_unit"))
        units = [unit or common for unit in units]
    if any(units) and not all(units):
        return Answer("decline", None, "all dimensions need a stated unit basis")
    if len({role for role, _ in dimensions}) != len(dimensions):
        return Answer("decline", None, "each geometry parameter must be stated once")
    if ctx.question is not None and uncovered_units(ctx.question, ctx.match.consumed):
        return Answer("decline", None, "the costing question has an unread condition")
    values = {
        role: Measurement(value, unit) for (role, value), unit in zip(dimensions, units)
    }
    output = ctx.query.get("rate_unit") if all(units) else None
    try:
        result = evaluate_property(
            ctx.reg, shape, op, values, ctx.log, output_unit=output
        )
    except (PropertyError, ArithmeticError, ValueError) as error:
        return Answer(
            "decline", None, f"the priced property needs compatible dimensions: {error}"
        )
    total = evaluate(
        "measure * rate",
        dict(measure=result.value, rate=rate),
        ctx.log,
        source="measure-cost",
    )
    if tax is not None:
        total = evaluate(
            "total * (1 + tax)",
            dict(total=total, tax=tax),
            ctx.log,
            source="measure-cost-tax",
        )
    assumptions = []
    if ctx.match is not None and len(dimensions) == 2 and "shape" not in ctx.match.slots:
        assumptions.append(AnswerAssumption("rectangular-costing-site",
            "The width-by-height site is rectangular.",
            (ctx.question.sentence_index,) if ctx.question else ()))
    if inferred_axis_unit:
        assumptions.append(AnswerAssumption("shared-axis-length-unit",
            "An unlabelled axis uses the other axis's stated length unit, or the quoted length unit.",
            (ctx.question.sentence_index,) if ctx.question else ()))
    return Answer("number", total, f"measure-cost: {op} {result.value:g} x {rate:g}",
                  assumptions=tuple(assumptions))
