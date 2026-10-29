"""Shape properties use the shared typed-property resolver and arithmetic log."""
from __future__ import annotations

from math import isfinite

from . import ConsumerContext, consumer
from ..answer import Answer, AnswerProof, ProofStep, SemanticNode
from ..properties import Measurement, evaluate_property
from ..evaluate import EvaluationError
from ...data.properties import PropertyError


@consumer("geometry")
def geometry(ctx: ConsumerContext):
    shape, quantity = ctx.query.get("shape"), ctx.query.get("quantity")
    definition = ctx.reg.derived_attribute(shape or "", quantity or "")
    legacy = ctx.reg.geometry_formulas.get((shape, quantity))
    if definition is None and legacy is None:
        return Answer("decline", None, f"no geometry formula for {quantity!r} of a {shape!r}")
    values = {}
    units_present = []
    for index in range(1, 4):
        role, raw = ctx.query.get(f'dim{index}'), ctx.query.get(f'val{index}')
        if not role or raw in (None, ""):
            continue
        if role in values:
            return Answer("decline", None, "each geometry parameter must be stated once")
        value = float(raw)
        if not isfinite(value) or value < 0:
            return Answer("decline", None, "geometry measurements must be finite and nonnegative")
        slot = ctx.match.slots.get(f'val{index}') if ctx.match is not None else None
        features = slot.features if slot is not None else {}
        unit = features.get("lemma") if features.get("value_kind") == "count" else None
        if unit == role and ctx.reg.word_in_category(unit, "geometry_dimension"):
            unit = None
        power = ctx.reg.attribute_value(features.get("qualifier", ""), "measurement_power") or 1
        values[role] = Measurement(value, unit, power)
        units_present.append(bool(unit))
    if any(units_present) and not all(units_present):
        return Answer("decline", None, "geometry measurements need an explicit common unit basis")
    output_unit = ctx.query.get("output_unit")
    if output_unit:
        slot = ctx.match.slots.get("output_unit") if ctx.match is not None else None
        qualifier = ctx.query.get("output_power") or (slot.features.get("qualifier", "") if slot is not None else "")
        power = ctx.reg.attribute_value(qualifier, "measurement_power") or 1
        if (not units_present or not all(units_present) or definition is None
                or len(definition.result_dimension) != 1 or definition.result_dimension[0][1] != power):
            return Answer("decline", None, "requested geometry units must match the measured result dimension")
    try:
        if definition is None:
            # Existing external packs retain the legacy geometry table. It is
            # deliberately unitless: typed inheritance is opt-in, never guessed.
            if any(units_present) or output_unit:
                raise PropertyError("a legacy formula has no declared unit contract")
            from ..evaluate import evaluate
            value = evaluate(legacy, {**ctx.reg.formula_constants,
                                     **{key: measurement.value for key, measurement in values.items()}},
                             ctx.log, source="geometry")
            sources = ()
        else:
            result = evaluate_property(ctx.reg, shape, quantity, values, ctx.log, output_unit=output_unit)
            value, sources = result.value, result.sources
    except (PropertyError, ArithmeticError, ValueError, EvaluationError) as exc:
        return Answer("decline", None,
                      f"{quantity!r} of a {shape!r} needs dimensions its given ones do not supply: {exc}")
    node = SemanticNode("derived-property", (("subject", shape), ("property", quantity)))
    description = "; ".join(f'{origin.pack}:{origin.kind}:{origin.owner}' for origin in sources)
    return Answer("number", round(value, 2), f'geometry: {quantity} of {shape} = {value:g}',
                  AnswerProof(node, (ProofStep("derived-property", node, detail=description),)))
