"""Complete-source and operand auditing shared by quantitative compositions.

Callers supply admissible facts and their exact source operands. This module
never decides event scope, resource identity or which assumptions are valid.
"""

from collections import Counter, defaultdict
from math import isfinite

from .answer import Answer
from .model import BatchEvidence
from .numeric_evidence import audit_numeric_mentions


def closed_evidence(ctx, rows, operands, *, additional_kinds=(), covered=None):
    if (
        ctx.store.collisions
        or ctx.store.quarantined
        or len(rows) != len(ctx.store.facts)
    ):
        return False
    expected = defaultdict(Counter)
    for row, values in operands:
        if any(not isfinite(v) or v < 0 for v in values):
            return False
        expected[row.provenance.sentence].update(values)
    if "span_value" in ctx.query:
        expected[ctx.question.sentence_index].update([float(ctx.query["span_value"])])
    covered = covered or {}
    from .source_coverage import uncovered_units

    return not (
        audit_numeric_mentions(
            (*ctx.premises, ctx.question),
            expected,
            missing="missing",
            duplicate="duplicate",
            additional_kinds=additional_kinds,
        )
        or any(
            uncovered_units(
                r,
                (
                    ctx.match.consumed
                    if r is ctx.question
                    else covered.get(r.sentence_index, ())
                ),
            )
            for r in (*ctx.premises, ctx.question)
        )
    )


def finish_batch_answer(ctx, rows, value, reason, *, assumptions=()):
    if value is None or not isfinite(value):
        return Answer("decline", None, "the calculated result must be finite")
    ctx.log.consumed_batch_keys.update(
        r.key() for r in rows if isinstance(r, BatchEvidence)
    )
    return Answer("number", value, reason, assumptions=tuple(assumptions))
