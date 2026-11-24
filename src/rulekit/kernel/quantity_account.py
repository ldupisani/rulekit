"""Collect the exact operands of a composed account and verify complete source coverage."""

from math import isclose, isfinite

from .answer import Answer, AnswerAssumption
from .composition_evidence import closed_evidence, finish_batch_answer
from .evaluate import evaluate
from .model import BatchEvidence


class IncompleteAccount(ValueError):
    """The stated evidence does not determine the requested account."""


def require(condition, reason):
    if not condition:
        raise IncompleteAccount(reason)


def whole_count(value, reason):
    """Accept only nonnegative whole counts, allowing arithmetic roundoff."""
    require(
        isfinite(value) and value >= 0 and isclose(value, round(value), rel_tol=0, abs_tol=1e-9), reason
    )
    return round(value)


class QuantityAccount:
    def __init__(self, ctx):
        self.ctx = ctx
        self.rows = list(ctx.store.by_kind(BatchEvidence))
        self.operands = []
        self.covered = {}
        self.assumptions = []

    def select(self, kind, *fields):
        rows = [r for r in self.rows if r.kind == kind]
        for row in rows:
            self.include(row, *(getattr(row, f) for f in fields))
        return rows

    def include(self, row, *values):
        """Record an ordinary projection alongside declarative evidence."""
        self.operands.append((row, list(values)))

    def extra_value(self, row, value):
        """Some grammatical variants bind an additional numeric operand."""
        next(values for fact, values in self.operands if fact is row).append(value)

    def one(self, kind, *fields, optional=False):
        rows = self.select(kind, *fields)
        if optional and not rows:
            return None
        require(len(rows) == 1, f"Expected one {kind} statement.")
        return rows[0]

    def assume(self, key, description, *rows):
        indices = tuple(sorted({r.provenance.sentence for r in rows}))
        self.assumptions.append(AnswerAssumption(key, description, indices))

    def calculate(self, expression, **values):
        return evaluate(expression, values, self.ctx.log, source=self.ctx.query["consumer"])

    def finish(self, value, reason):
        facts = [r for r, _ in self.operands]
        require(
            len({r.key() for r in facts}) == len(facts)
            and closed_evidence(self.ctx, facts, self.operands, covered=self.covered),
            "Every quantity and condition must belong to the same account.",
        )
        return finish_batch_answer(self.ctx, facts, value, reason, assumptions=tuple(self.assumptions))


def quantity_account(name, prerequisite):
    """An overlapping ask is eligible only after its distinctive premise was read."""
    from .consumers import consumer

    kinds = {prerequisite} if isinstance(prerequisite, str) else set(prerequisite)

    def register(function):
        @consumer(
            name, applicable=lambda store: any(r.kind in kinds for r in store.by_kind(BatchEvidence))
        )
        def solve_account(ctx):
            try:
                return function(QuantityAccount(ctx), ctx)
            except IncompleteAccount as exc:
                return Answer("decline", None, str(exc))

        return solve_account

    return register
