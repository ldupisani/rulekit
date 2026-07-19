"""Extracted answer consumers, one module per consumer family.

WHY. `answer.py` reached 3,479 lines against architecture.md's "each module
≤ ~400", and every one of its 41 consumers lives in one if-chain. That matters
beyond tidiness: the file is where every GUARD lives, and a guard is the
failure the corpus gates cannot see — a broken happy path costs a `correct`,
a broken guard produces a confident WRONG or nothing at all.

THE MOVE IS MECHANICAL AND MUST STAY THAT WAY. Each extraction is one consumer,
byte-for-byte, behind `ConsumerContext`, gated on the full eight slices AND the
consumer golden master (tests/test_consumer_golden_master.py), which asserts
both the routing and the behaviour of 102 probes. An extraction that changes an
answer is a bug, not a cleanup.

AN EXTRACTED CONSUMER IS ALSO DIRECTLY TESTABLE, and that turned out to be the
main prize rather than a side effect. Roughly half of answer.py's 92 guards
have no probe, and many are unreachable through ordinary input BY DESIGN —
molar-mass re-checks a symbol the formula reader already validated, and its
"needs a numeric rate" branch cannot fire because the ask's slot is
`type: counted`. Those are defensive guards, and inside a 3,479-line if-chain
there is no way to call them. Extraction is what makes them reachable, so the
honest order is EXTRACT FIRST, then close the guard gaps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:  # pragma: no cover - import cycle at runtime, types only
    from ..model import FactStore, Reading
    from ...data.registry import Registry
    from ..evaluate import ArithmeticLog


@dataclass(frozen=True)
class ConsumerContext:
    """Everything `answer()` has when it dispatches.

    Passed whole rather than as parameters chosen per consumer: the point of
    the extraction is a STABLE interface, and a signature that grows a field
    each time a consumer needs one is not stable. Frozen because a consumer
    computes an Answer — it has no business mutating the dispatch state.
    """

    query: dict[str, str]
    question: "Reading"
    store: "FactStore"
    reg: "Registry"
    log: "ArithmeticLog"
    match: Any            # patterns.Match — the matched span, for read-checks
    ask: Any              # patterns.AskRule


# name -> handler. `answer()` consults this BEFORE its if-chain, so an
# extracted consumer is unreachable from the chain and the two can never
# silently diverge.
CONSUMERS: dict[str, Callable[[ConsumerContext], Any]] = {}


def consumer(name: str):
    """Register a handler under the name its asks resolve to."""

    def register(fn):
        if name in CONSUMERS:
            raise RuntimeError(f"consumer {name!r} registered twice")
        CONSUMERS[name] = fn
        return fn

    return register


from . import (  # noqa: E402,F401  (import registers each handler)
    affine_convert as _affine_convert,
    arithmetic as _arithmetic,
    calendar as _calendar,
    coordinate as _coordinate,
    discounted_total as _discounted_total,
    measure_cost as _measure_cost,
    molar_mass as _molar_mass,
    number_theory as _number_theory,
    rate_cost as _rate_cost,
    trigonometry as _trigonometry,
    unit_convert as _unit_convert,
)
