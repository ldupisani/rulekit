"""Connected quantity ratios with explicit unit and resource identities.

Callers decide whether relationships describe actual contents, requirements or
capacity. This arithmetic helper never turns a capacity into an observation.
"""

from math import isfinite

from .affine_graph import AffineGraph, AffineError
from .evaluate import evaluate
from .rate_calculation import convert_units


def quantity_through_ratios(value, source, target, ratios, reg, log):
    """Nodes are (unit, resource); links are (output, input, numerator, denominator)."""
    if not isfinite(value) or value < 0:
        raise AffineError("the starting quantity must be finite and nonnegative")
    nodes = {source, target}
    edges = []
    definitions = set()
    for output, basis, numerator, denominator in ratios:
        if (
            not all(isfinite(v) and v > 0 for v in (numerator, denominator))
            or output == basis
            or (output, basis) in definitions
        ):
            raise AffineError("each quantity ratio needs a unique positive basis")
        definitions.add((output, basis))
        nodes.update((output, basis))
        factor = evaluate(
            "numerator / denominator",
            dict(numerator=numerator, denominator=denominator),
            log,
            source="quantity-ratio",
        )
        edges.append((output, basis, factor, 0))
    # Conversion joins only the same resource. A shared physical dimension
    # does not make quantities of different substances interchangeable.
    ordered = sorted(nodes)
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            if left[1] != right[1] or left[0] == right[0]:
                continue
            factor = convert_units(
                1, left[0], right[0], reg, log, source="quantity-ratio-unit"
            )
            if factor is not None:
                edges.append((right, left, factor, 0))
    graph = AffineGraph([(source, value)], edges, log)
    for node in nodes:
        resolved = graph.value(node)
        if not isfinite(resolved) or resolved < 0:
            raise AffineError(
                "all quantity ratios must form one nonnegative connected account"
            )
    return graph.value(target)
