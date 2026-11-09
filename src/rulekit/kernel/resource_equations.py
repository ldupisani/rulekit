"""Logged conservation arithmetic shared by resource-account consumers."""

from .evaluate import evaluate
from enum import Enum
from math import isfinite


class FractionBasis(Enum):
    OPENING = "opening"
    REMAINDER = "remainder"


class FractionalAllocation:
    """An ordered balance with an explicit, caller-validated base per step.

    Resource, owner, purpose and reference resolution remain caller policies.
    This calculation neither chooses a basis nor interprets an omitted one.
    """

    def __init__(self, opening, log):
        if not isfinite(opening) or opening < 0:
            raise ValueError("the opening amount must be finite and nonnegative")
        self.opening = self.balance = opening
        self.log = log

    def allocate(self, fraction, basis, *, source):
        if not isfinite(fraction) or not 0 <= fraction <= 1:
            raise ValueError("an allocation fraction must lie within one whole")
        if not isinstance(basis, FractionBasis):
            raise ValueError("an allocation needs an explicit fraction basis")
        base = self.opening if basis is FractionBasis.OPENING else self.balance
        amount = evaluate(
            "base * fraction",
            {"base": base, "fraction": fraction},
            self.log,
            source=source,
        )
        return self.allocate_amount(amount, source=source)

    def allocate_amount(self, amount, *, source):
        """Allocate an explicit amount from the same checked balance."""
        if not isfinite(amount) or amount < 0:
            raise ValueError("an allocation amount must be finite and nonnegative")
        balance = resource_residual([self.balance], [amount], self.log, source=source)
        if balance < -1e-9:
            raise ValueError("the stated allocations exceed the resource stock")
        self.balance = max(0, balance)
        return amount


def resource_residual(available, allocated, log, *, source):
    """One remaining term of a resource equation, retaining every operand."""
    left = " + ".join(str(v) for v in available) or "0"
    right = " + ".join(str(v) for v in allocated) or "0"
    return evaluate(f"({left}) - ({right})", {}, log, source=source)
