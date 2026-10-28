"""Balance explicitly measured resources using shared formulas and conversions."""
from collections import Counter, defaultdict
from math import isfinite

from . import consumer
from ..answer import Answer
from ..evaluate import evaluate, EvaluationError
from ..model import RegionEvidence
from ..numeric_evidence import audit_numeric_mentions
from ..dimensions import conversion_factor
from ..resource_equations import resource_residual
from ..source_coverage import uncovered_document_units


@consumer("material-region-remainder", applicable=lambda s: bool(s.by_kind(RegionEvidence)))
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)
    rows = list(ctx.store.by_kind(RegionEvidence))
    if (len(rows) != len(ctx.store.facts) or ctx.store.collisions or ctx.store.quarantined
            or any(r.provenance.assumption and r.stage != "opening" for r in rows)):
        return decline("all evidence must belong to one explicit measured balance")
    contexts = [r for r in rows if r.stage == "context"]
    groups = defaultdict(list)
    for row in rows:
        if row.stage in ("opening", "removal"):
            groups[(row.provenance.sentence, row.position, row.stage)].append(row)
        elif row.stage not in ("context", "removal-count", "purpose-count"):
            return decline("unsupported measured-resource evidence")
    openings = [g for g in groups.values() if g[0].stage == "opening"]
    removals = [g for g in groups.values() if g[0].stage == "removal"]
    if len(openings) != 1 or len(contexts) > 1 or not removals:
        return decline("one resource stock and complete measured removals are required")
    opening = openings[0]
    if ctx.query.get("material") not in ("", opening[0].material):
        return decline("the question must identify the measured resource")
    quantity = ctx.query.get("quantity")
    unit = ctx.query.get("unit")
    if quantity == "inferred":
        # A dimensionless question may select only the single common basis
        # declared by the direct measurements or the shared shape formulas.
        candidates = None
        for group in (opening, *removals):
            row = group[0]
            bases = ({basis for shape, basis in ctx.reg.geometry_formulas if shape == row.shape}
                     if row.shape else {row.quantity} - {""})
            candidates = bases if candidates is None else candidates & bases
        if not candidates or len(candidates) != 1:
            return decline("an implicit measurement basis must be uniquely established")
        quantity = candidates.pop()
    if not quantity:
        return decline("the question must specify a measurement basis")
    if not unit:
        units = {r.unit for g in (opening, *removals) for r in g}
        if len(units) != 1:
            return decline("an implicit output unit must be uniquely stated")
        unit = units.pop()
    expected = defaultdict(Counter)
    values = {}
    dimensions = {}
    for key, group in groups.items():
        row = group[0]
        if len({(r.material, r.entity, r.shape, r.quantity) for r in group}) != 1:
            return decline("each measured region needs consistent identity and basis")
        if row.stage == "removal":
            anchors = {r.entity for r in rows if r.stage == "removal" and r.entity
                       and r.provenance.sentence == row.provenance.sentence}
            actor = row.entity or (next(iter(anchors)) if len(anchors) == 1 else "")
            if opening[0].entity and actor != opening[0].entity:
                return decline("a direct removal must identify the stock's owner")
            material = row.material
            if not material:
                scopes = [c for c in contexts if c.entity == actor
                          and c.provenance.sentence < row.provenance.sentence]
                if len(scopes) == 1:
                    material = scopes[0].material
                elif (row.source_scope == "opening"
                      or row.source_scope == "previous" and any(
                          r.entity == actor and r.source_scope == "opening"
                          and r.provenance.sentence == row.provenance.sentence
                          for r in rows if r.stage == "removal")):
                    material = opening[0].material
                elif (not row.shape and actor and actor == opening[0].entity
                      and opening[0].provenance.sentence < row.provenance.sentence):
                    material = opening[0].material
                else:
                    return decline("an omitted resource needs an explicit unique owner or fabrication scope")
            if material != opening[0].material:
                return decline("a removal names another resource")
        if any(not isfinite(r.value) or r.value <= 0 for r in group):
            return decline("measurements must be positive and finite")
        expected[row.provenance.sentence].update(r.value for r in group)
        factors = [conversion_factor(ctx.reg, r.unit, unit) for r in group]
        if any(factor is None for factor in factors):
            return decline("measurements and requested units must be compatible")
        operands = [evaluate("value * factor", {"value": r.value, "factor": factor},
                             ctx.log, source="resource-measurement")
                    for r, factor in zip(group, factors)]
        if row.shape:
            if (any(not r.dimension or r.quantity for r in group)
                    or len({r.dimension for r in group}) != len(group)):
                return decline("a region needs distinct named dimensions")
            formula = ctx.reg.geometry_formulas.get((row.shape, quantity))
            if formula is None:
                return decline("the stated shape needs a declared formula for this quantity")
            try:
                values[key] = evaluate(formula, dict(zip((r.dimension for r in group), operands)),
                                       ctx.log, source="measured-resource-formula")
            except (EvaluationError, NameError, KeyError):
                return decline("the formula needs dimensions that were not supplied")
            dimensions[key] = sorted(operands)
        else:
            if len(group) != 1 or row.dimension or row.quantity != quantity:
                return decline("direct amounts must have the requested physical basis")
            values[key] = operands[0]
    opening_key = next(k for k, g in groups.items() if g is opening)
    for key, group in groups.items():
        if group[0].stage != "removal":
            continue
        if key in dimensions and opening_key in dimensions:
            if (len(dimensions[key]) != len(dimensions[opening_key])
                    or any(cut > stock for cut, stock in zip(dimensions[key], dimensions[opening_key]))):
                return decline("a removed region must fit within the stock in some orientation")
        elif bool(group[0].shape) != bool(opening[0].shape):
            return decline("direct and geometric amounts need an explicit common measurement basis")
    for row in rows:
        if row.stage == "purpose-count":
            expected[row.provenance.sentence][row.value] += 1
        if row.stage == "removal-count":
            expected[row.provenance.sentence][row.value] += 1
            if row.value != sum(g[0].provenance.sentence == row.provenance.sentence for g in removals):
                return decline("the stated region count must match the complete measured list")
    if (any(c.material != opening[0].material for c in contexts)
            or uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises, ctx.question), expected,
                                      missing="missing", duplicate="duplicate")):
        return decline("all resources, measurements and removal conditions must be read")
    value = resource_residual([values[opening_key]],
                              [v for k, v in values.items() if k != opening_key],
                              ctx.log, source="measured-resource-remainder")
    if not isfinite(value) or value < 0:
        return decline("the removals exceed the measured stock")
    ctx.log.consumed_component_keys.update(r.key() for r in rows)
    detail = (f"opening {quantity} minus explicit removals; "
              f"input measurements normalized to {unit}")
    if opening[0].shape:
        detail += "; geometric accounting does not construct a packing layout"
    return Answer("number", value, detail)
