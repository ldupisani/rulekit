"""Logged conservation arithmetic shared by resource-account consumers."""

from .evaluate import evaluate


def resource_residual(available, allocated, log, *, source):
    """One remaining term of a resource equation, retaining every operand."""
    left = " + ".join(str(v) for v in available) or "0"
    right = " + ".join(str(v) for v in allocated) or "0"
    return evaluate(f"({left}) - ({right})", {}, log, source=source)
