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

    query: dict[str, Any]
    question: "Reading"
    store: "FactStore"
    reg: "Registry"
    log: "ArithmeticLog"
    match: Any            # patterns.Match — the matched span, for read-checks
    ask: Any              # patterns.AskRule
    # Premise readings are optional for backward compatibility with direct
    # consumer probes. Most consumers reason over the saturated FactStore;
    # whole-document numeric consumers may additionally audit the original
    # unit-bearing values without reconstructing them from facts.
    premises: tuple["Reading", ...] = ()
    # An explicit absolute calendar coordinate supplied by the caller. The
    # kernel never reads the wall clock: deictic asks such as ``now`` decline
    # when this context is absent, keeping benchmarks and replay deterministic.
    reference_year: int | None = None


# name -> handler, dispatched BEFORE `answer()`'s if-chain so an extracted
# consumer is unreachable from the chain and the two cannot silently diverge.
CONSUMERS: dict[str, Callable[[ConsumerContext], Any]] = {}

# ⚠ THE TEMPORAL ORIGO SPLITS `answer()` IN TWO, and this is the trap the rest
# of the extraction has to respect.
#
# `answer()` resolves the question's reference time PART-WAY DOWN its body and
# rebinds `store` to a time-filtered copy. Consumers written ABOVE that point
# never see the filter; the 26 written BELOW it always do. So "dispatch the
# registry before the chain" is behaviour-preserving for an above-origo
# consumer and a SILENT REGRESSION for a below-origo one — it would drop the
# time scoping, and no corpus item need phrase the difference.
#
# Moving the single dispatch below the origo is not the fix either: the origo
# can itself DECLINE ("the question names more than one time"), so running it
# first would let above-origo consumers newly decline on questions they answer
# today.
#
# Hence two dispatch points and a flag. A consumer extracted from below the
# origo registers with `time_scoped=True` and is dispatched AFTER it, with
# `ctx.store` already filtered. All 15 extracted so far are above it — verified
# against the pre-refactor file, not assumed.
TIME_SCOPED: set[str] = set()


def consumer(name: str, *, time_scoped: bool = False):
    """Register a handler under the name its asks resolve to.

    `time_scoped` marks a consumer that lived BELOW the temporal origo and must
    therefore receive the time-filtered store. Getting it wrong is invisible in
    the answer of any single question, so it is recorded per consumer at the
    point of extraction rather than inferred later.
    """

    def register(fn):
        if name in CONSUMERS:
            raise RuntimeError(f"consumer {name!r} registered twice")
        CONSUMERS[name] = fn
        if time_scoped:
            TIME_SCOPED.add(name)
        return fn

    return register


from . import (  # noqa: E402,F401  (import registers each handler)
    single_entity as _single_entity,
    rate_span as _rate_span,
    rate_span_inverse as _rate_span_inverse,
    capacity as _capacity,
    difference as _difference,
    completion_duration_difference as _completion_duration_difference,
    change as _change,
    unique_entity as _unique_entity,
    money_left as _money_left,
    single_entity_elided_measure as _single_entity_elided_measure,
    combined_elided_measure as _combined_elided_measure,
    combined as _combined,
    per_holder as _per_holder,
    average as _average,
    unit_price_from_total as _unit_price_from_total,
    cost_of_quantity as _cost_of_quantity,
    partition_complement as _partition_complement,
    partition_percentage as _partition_percentage,
    label_difference as _label_difference,
    item_cost as _item_cost,
    deficit as _deficit,
    age_at_year as _age_at_year,
    age_projected as _age_projected,
    membership_verdict as _membership_verdict,
    logic_disjunction_verdict as _logic_disjunction_verdict,
    verbal_obj_class_verdict as _verbal_obj_class_verdict,
    universal_verdict as _universal_verdict,
    existential_verdict as _existential_verdict,
    logic_verdict as _logic_verdict,
    passive_agent_verdict as _passive_agent_verdict,
    affine_convert as _affine_convert,
    arithmetic as _arithmetic,
    calendar as _calendar,
    coordinate as _coordinate,
    discounted_total as _discounted_total,
    geometry as _geometry,
    list_statistic as _list_statistic,
    location_witnesses as _location_witnesses,
    measure_cost as _measure_cost,
    molar_mass as _molar_mass,
    number_theory as _number_theory,
    rate_cost as _rate_cost,
    physics as _physics,
    reference_aggregate as _reference_aggregate,
    reference_lookup as _reference_lookup,
    trigonometry as _trigonometry,
    unit_convert as _unit_convert,
    vector as _vector,
)
