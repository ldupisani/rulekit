"""Affine constraints over caller-owned identities, including unanchored differences.

No arbitrary origin is asserted as an observed quantity. A linear result is
determined only if all free component origins cancel, or observed anchors fix them.
"""

from collections import defaultdict, deque
from math import isclose, isfinite

from .evaluate import evaluate


class AffineError(ValueError):
    pass


def dependency_graph(amounts, relations, log):
    """Use affine arithmetic for a caller's strictly anchored directed DAG.

    Unlike general affine constraints, these dependency definitions may not
    infer a base from an inverse edge or solve a cycle. A zero multiplier
    still requires its stated standard to have an anchored definition.
    """
    amounts, relations = list(amounts), list(relations)
    dependencies = defaultdict(set)
    successors = defaultdict(list)
    for node, standard, _, _ in relations:
        dependencies[node].add(standard)
        dependencies[standard]
        if node not in successors[standard]:
            successors[standard].append(node)
    ready_nodes = deque(node for node in dependencies if not dependencies[node])
    visited = set()
    while ready_nodes:
        node = ready_nodes.popleft()
        visited.add(node)
        for target in successors[node]:
            dependencies[target].discard(node)
            if not dependencies[target]:
                ready_nodes.append(target)
    if len(visited) != len(dependencies):
        raise AffineError("dependencies must be anchored and acyclic")
    known = {node for node, _ in amounts}
    pending = list(relations)
    zero_anchors = []
    while pending:
        ready = [edge for edge in pending if edge[1] in known]
        if not ready:
            raise AffineError("dependencies must be anchored and acyclic")
        for edge in ready:
            node, standard, factor, offset = edge
            if not isfinite(factor) or factor < 0 or not isfinite(offset):
                raise AffineError("dependency factors must be finite and nonnegative")
            if factor == 0:
                zero_anchors.append(
                    (
                        node,
                        evaluate(
                            "factor + offset",
                            dict(factor=factor, offset=offset),
                            log,
                            source="zero-dependency",
                        ),
                    )
                )
            known.add(node)
            pending.remove(edge)
    return AffineGraph(
        [*amounts, *zero_anchors], [edge for edge in relations if edge[2] != 0], log
    )


class AffineGraph:
    def __init__(self, amounts, relations, log):
        """Amounts are (node, value); relations are (subject, standard, factor, offset)."""
        self.log = log
        self.forms = {}
        adjacency = defaultdict(list)
        anchors = defaultdict(list)
        for node, value in amounts:
            if not isfinite(value):
                raise AffineError("anchors must be finite")
            anchors[node].append(value)
            adjacency[node]
        for subject, standard, factor, offset in relations:
            if not isfinite(factor) or not isfinite(offset) or factor <= 0:
                raise AffineError(
                    "comparisons need positive finite factors and finite offsets"
                )
            adjacency[standard].append((subject, factor, offset))
            inverse = evaluate(
                "1 / factor", {"factor": factor}, log, source="affine-inverse-factor"
            )
            delta = evaluate(
                "-offset / factor",
                {"factor": factor, "offset": offset},
                log,
                source="affine-inverse-offset",
            )
            adjacency[subject].append((standard, inverse, delta))
        for root in adjacency:
            if root in self.forms:
                continue
            local = {root: (1.0, 0.0)}
            pending = deque([root])
            origins = []
            while pending:
                node = pending.popleft()
                a, b = local[node]
                origins.extend(
                    evaluate(
                        "(value - offset) / factor",
                        {"value": v, "offset": b, "factor": a},
                        log,
                        source="affine-observed-origin",
                    )
                    for v in anchors[node]
                )
                for target, factor, offset in adjacency[node]:
                    x = evaluate(
                        "factor * a",
                        {"factor": factor, "a": a},
                        log,
                        source="affine-path-factor",
                    )
                    y = evaluate(
                        "factor * b + offset",
                        {"factor": factor, "b": b, "offset": offset},
                        log,
                        source="affine-path-offset",
                    )
                    if target not in local:
                        local[target] = (x, y)
                        pending.append(target)
                        continue
                    c, d = local[target]
                    if isclose(c, x, abs_tol=1e-9):
                        if not isclose(d, y, rel_tol=1e-9, abs_tol=1e-9):
                            raise AffineError("comparison paths disagree")
                    else:
                        origins.append(
                            evaluate(
                                "(y - d) / (c - x)",
                                dict(y=y, d=d, c=c, x=x),
                                log,
                                source="affine-cycle-origin",
                            )
                        )
            if origins and any(
                not isclose(origins[0], value, rel_tol=1e-9, abs_tol=1e-9)
                for value in origins[1:]
            ):
                raise AffineError("observed quantities and comparisons disagree")
            origin = origins[0] if origins else None
            for node, (a, b) in local.items():
                if origin is None:
                    self.forms[node] = (root, a, b)
                else:
                    value = evaluate(
                        "a * origin + b",
                        dict(a=a, origin=origin, b=b),
                        log,
                        source="affine-observed-value",
                    )
                    self.forms[node] = (None, 0.0, value)

    def linear(self, terms):
        coefficients = defaultdict(float)
        offsets = []
        for node, weight in terms:
            if node not in self.forms:
                raise AffineError("a requested quantity has no comparison evidence")
            root, a, b = self.forms[node]
            coefficients[root] += weight * a
            offsets.append(
                evaluate(
                    "weight * offset",
                    dict(weight=weight, offset=b),
                    self.log,
                    source="affine-result-term",
                )
            )
        if any(
            root is not None and not isclose(a, 0, abs_tol=1e-9)
            for root, a in coefficients.items()
        ):
            raise AffineError(
                "the requested quantity still depends on an unknown amount"
            )
        return evaluate(
            " + ".join(map(str, offsets)) or "0",
            {},
            self.log,
            source="affine-linear-result",
        )

    def value(self, node):
        return self.linear([(node, 1)])
