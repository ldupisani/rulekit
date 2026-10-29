"""Evaluate compiled derived attributes using the shared arithmetic and units."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, isclose
from typing import Mapping

from ..data.properties import Dimension, PropertyError
from .dimensions import conversion_factor
from .evaluate import ArithmeticLog, evaluate, EvaluationError


@dataclass(frozen=True)
class Measurement:
    value: float
    unit: str | None = None
    power: float = 1


@dataclass(frozen=True)
class PropertyResult:
    value: float
    dimension: Dimension
    consumed: frozenset[str]
    sources: tuple


def _unit_factor(reg, basis: str, source: str, target: str) -> float | None:
    category = reg.formula_unit_categories.get(basis)
    if category is not None:
        return conversion_factor(reg, source, target, category=category)
    # A legacy canonical unit alone does not identify a physical family.
    # Accept only identity or an explicitly declared edge in that case.
    return 1.0 if source == target else reg.conversions.get((source, target))


def evaluate_property(reg, subject: str, name: str, values: Mapping[str, float | Measurement],
                      log: ArithmeticLog | None = None, *, output_unit: str | None = None) -> PropertyResult:
    """Resolve declared equalities and dependencies; reject every unused input."""
    subject = subject.casefold()
    name = reg.property_aliases.get(name, name)
    formulas = reg.property_formulas.get(subject, {})
    scalars = reg.attrs.get(subject, {})
    bindings = reg.parameter_bindings.get(subject, {})
    if name not in formulas and name not in scalars:
        raise PropertyError(f"no declared property {name!r} for {subject!r}")
    consumed, origins = set(), set()
    visiting, cache = set(), {}

    def canonical(key):
        while key in bindings:
            origins.update(reg.property_sources.get((subject, 'binding:' + key), ()))
            key = bindings[key]
        return key

    expected_dims = {}
    for formula in formulas.values():
        for key, dim in formula.inputs.items():
            expected_dims[canonical(key)] = dim
    supplied = {}
    supplied_keys = {}
    for key, raw in values.items():
        target = canonical(key)
        if target not in expected_dims:
            raise PropertyError(f"unrecognized property input {key!r}")
        measurement = raw if isinstance(raw, Measurement) else Measurement(float(raw))
        value = measurement.value
        if not isfinite(value):
            raise PropertyError("property measurements must be finite")
        if measurement.unit:
            dim = expected_dims[target]
            if len(dim) != 1 or dim[0][1] != measurement.power:
                raise PropertyError("measurement has an incompatible physical dimension")
            base, power = dim[0]
            unit = reg.formula_units.get(base)
            factor = _unit_factor(reg, base, measurement.unit, unit) if unit else None
            if factor is None:
                raise PropertyError("measurement unit is incompatible with the formula parameter")
            value = evaluate('value * factor**power',
                             {'value': value, 'factor': factor, 'power': power}, log,
                             source='property-unit-conversion')
        if target in supplied and not isclose(supplied[target], value, rel_tol=1e-10, abs_tol=1e-10):
            raise PropertyError("stated parameters contradict a declared equality")
        supplied[target] = value
        supplied_keys.setdefault(target, set()).add(key)

    def resolve(key):
        key = canonical(key)
        if key in supplied:
            consumed.update(supplied_keys[key])
            return supplied[key]
        if key in cache:
            return cache[key]
        if key in visiting:
            raise PropertyError("circular property dependency")
        origins.update(reg.property_sources.get((subject, key), ()))
        if key in scalars:
            value = scalars[key]
        elif key in formulas:
            visiting.add(key)
            formula = formulas[key]
            env = dict(formula.constants)
            env.update({parameter: resolve(parameter) for parameter in formula.inputs})
            try:
                value = evaluate(formula.expr, env, log, source='property:' + subject + ':' + key)
            except (EvaluationError, ArithmeticError, OverflowError) as exc:
                raise PropertyError("formula cannot be evaluated for the stated measurements") from exc
            visiting.remove(key)
        else:
            raise PropertyError(f"missing property input {key!r}")
        if not isinstance(value, (int, float)) or not isfinite(value):
            raise PropertyError("property result must be finite and real")
        cache[key] = float(value)
        return cache[key]

    value = resolve(name)
    if set(values) != consumed:
        raise PropertyError("the formula does not consume all stated parameters")
    result_dimension = formulas[name].result_dimension if name in formulas else ()
    if output_unit:
        if len(result_dimension) != 1:
            raise PropertyError("the requested output unit needs a single physical basis")
        base, power = result_dimension[0]
        canonical_unit = reg.formula_units.get(base)
        factor = _unit_factor(reg, base, canonical_unit, output_unit) if canonical_unit else None
        if factor is None:
            raise PropertyError("requested output unit is incompatible with the result")
        value = evaluate('value * factor**power', {'value': value, 'factor': factor, 'power': power},
                         log, source='property-output-conversion')
    return PropertyResult(value, result_dimension, frozenset(consumed), tuple(sorted(origins)))
