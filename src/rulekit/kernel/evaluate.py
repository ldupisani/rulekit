"""The safe arithmetic evaluator — the ONLY math path in rulekit.

`ast.parse` + a node/operator whitelist; never eval/exec. Every call is
appended to an ArithmeticLog with provenance so guards can audit that each
stated value was actually used (hop-by-hop, raw factors visible).
"""

from __future__ import annotations

import ast
import operator
from dataclasses import dataclass, field
from typing import Any

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {"abs": abs, "min": min, "max": max, "round": round}


class EvaluationError(Exception):
    pass


@dataclass
class LogEntry:
    expression: str
    env: dict[str, float]
    result: float
    source: str  # rule/synth id or stage name


@dataclass
class ArithmeticLog:
    entries: list[LogEntry] = field(default_factory=list)
    # The deictic journal (kernel.deixis.Journal), or None when tracing is off.
    #
    # It rides HERE rather than on its own parameter because this object is already
    # threaded to every deep site in the kernel — notably it is the third positional
    # argument of every SynthPlugin, so the eight saturate.py resolution sites can each
    # migrate onto deixis.resolve() with ZERO signature changes. Nothing reads it yet;
    # that is the point of landing it now.
    #
    # Typed loosely to keep evaluate.py free of a kernel.deixis import.
    journal: Any = None

    def uses_value(self, value: float, tol: float = 1e-9) -> bool:
        """Did any logged expression literally contain this value (as a
        constant or bound variable)? The dropped-multiplier guard's probe."""
        for e in self.entries:
            for v in e.env.values():
                if abs(v - value) < tol:
                    return True
            try:
                tree = ast.parse(e.expression, mode="eval")
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                    if abs(node.value - value) < tol:
                        return True
        return False


def _eval_node(node: ast.AST, env: dict[str, float]) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, env)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        raise EvaluationError(f"non-numeric constant {node.value!r}")
    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        raise EvaluationError(f"unbound variable {node.id!r}")
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval_node(node.left, env), _eval_node(node.right, env))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand, env))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS:
        if node.keywords:
            raise EvaluationError("keyword arguments not allowed")
        return _FUNCS[node.func.id](*(_eval_node(a, env) for a in node.args))
    raise EvaluationError(f"disallowed syntax: {ast.dump(node)[:80]}")


def evaluate(
    expression: str,
    env: dict[str, float] | None = None,
    log: ArithmeticLog | None = None,
    source: str = "?",
) -> float:
    """Evaluate one arithmetic expression over named variables."""
    env = env or {}
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise EvaluationError(f"unparseable expression {expression!r}: {exc}") from exc
    result = _eval_node(tree, env)
    if log is not None:
        log.entries.append(LogEntry(expression, dict(env), result, source))
    return result


def run_program(text: str, log: ArithmeticLog | None = None, source: str = "program") -> float:
    """Multi-line `name = expr` program; the last line (or `answer`) is the
    result. Kept for tooling parity with difg's translate.run_program."""
    env: dict[str, float] = {}
    last: float | None = None
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line and not any(op in line.split("=")[0] for op in "<>!"):
            name, expr = line.split("=", 1)
            name = name.strip()
            if not name.isidentifier():
                raise EvaluationError(f"bad assignment target {name!r}")
            env[name] = evaluate(expr.strip(), env, log, source)
            last = env[name]
        else:
            last = evaluate(line, env, log, source)
    if last is None:
        raise EvaluationError("empty program")
    return env.get("answer", last)
