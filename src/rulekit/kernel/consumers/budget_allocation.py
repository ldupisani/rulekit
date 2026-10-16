"""Allocate fractions of one budget to named purposes and its explicit remainder."""

from collections import Counter, defaultdict
from math import isfinite
from . import consumer
from ..answer import Answer
from ..model import (
    BatchEvidence,
    ResourceBalance,
    ResourceAllocation,
    FractionQuantity,
    ResourceAccountingIssue,
)
from ..evaluate import evaluate
from ..resource_equations import resource_residual
from ..numeric_evidence import audit_numeric_mentions
from ..source_coverage import uncovered_document_units


@consumer(
    "budget-purpose-amount",
    applicable=lambda s: any(
        b.kind == "budget-share" for b in s.by_kind(BatchEvidence)
    ),
)
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    balances = list(ctx.store.by_kind(ResourceBalance))
    rows = list(ctx.store.by_kind(BatchEvidence))
    shares = [r for r in rows if r.kind == "budget-share"]
    rest = [r for r in rows if r.kind == "budget-remainder"]
    if (
        len(balances) != 1
        or len(rest) != 1
        or not shares
        or len(rows) != len(shares) + 1
        or ctx.store.collisions
        or ctx.store.quarantined
    ):
        return decline(
            "one budget and one complete allocation with an explicit remainder are required"
        )
    budget = balances[0]
    owner = ctx.query["entity"]
    if (
        budget.entity != owner
        or budget.stage != "opening"
        or budget.owner
        or budget.qualifier
        or budget.provenance.assumption
        or not isfinite(budget.value)
        or budget.value < 0
        or any(
            r.provenance.assumption
            or r.provenance.sentence <= budget.provenance.sentence
            for r in rows
        )
    ):
        return decline("all allocations must belong to the same prior budget")
    for r in rows:
        if r.entity and r.entity != owner:
            return decline("another participant cannot allocate this budget")
        if not r.entity and not any(
            s.entity == owner
            and s.provenance.sentence == r.provenance.sentence
            and s.position < r.position
            for s in shares
        ):
            return decline(
                "an elliptical allocation needs a preceding same-sentence owner"
            )
    destinations = [(r.measure, r.attribute) for r in rows]
    if len(set(destinations)) != len(destinations) or any(
        not isfinite(r.value) or not 0 <= r.value <= 1 for r in shares
    ):
        return decline(
            "budget destinations must be distinct and fractions must lie in one whole"
        )
    residual = resource_residual(
        [1], [r.value for r in shares], ctx.log, source="budget-unallocated-fraction"
    )
    if residual < -1e-9:
        return decline("the allocated fractions exceed the budget")
    target = (ctx.query["purpose"], ctx.query.get("qualifier", ""))
    if target not in destinations:
        return decline("the requested destination is not in the allocation")
    expected = defaultdict(Counter)
    expected[budget.provenance.sentence][budget.value] += 1
    for r in shares:
        expected[r.provenance.sentence][r.value] += 1
    if uncovered_document_units(
        ctx.premises, ctx.question, ctx.match.consumed
    ) or audit_numeric_mentions(
        (*ctx.premises, ctx.question),
        expected,
        missing="missing",
        duplicate="duplicate",
    ):
        return decline("every budget amount, allocation and condition must be read")
    phrases = list(ctx.store.by_kind(ResourceAllocation))
    if any(
        a.provenance.sentence != budget.provenance.sentence
        or a.value != budget.value
        or a.measure != budget.measure
        for a in phrases
    ):
        return decline("an extra allocation is outside this budget")
    fractions = list(ctx.store.by_kind(FractionQuantity))
    if any(
        f.entity != owner
        or not any(
            r.value == f.fraction and r.provenance.sentence == f.provenance.sentence
            for r in shares
        )
        for f in fractions
    ):
        return decline(
            "an additional fractional event is not explained by the allocation"
        )
    for issue in ctx.store.by_kind(ResourceAccountingIssue):
        reading = next(
            (r for r in ctx.premises if r.sentence_index == issue.provenance.sentence),
            None,
        )
        unit = reading.unit(issue.position) if reading else None
        if (
            issue.reason != "unread-event"
            or unit is None
            or not unit.features.get("pattern_consumed")
            or not any(
                r.verb == unit.features.get("lemma")
                and r.provenance.sentence == issue.provenance.sentence
                for r in shares
            )
        ):
            return decline("an unresolved accounting event lies outside the allocation")
    fraction = (
        residual
        if target == (rest[0].measure, rest[0].attribute)
        else next(r.value for r in shares if (r.measure, r.attribute) == target)
    )
    value = evaluate(
        "budget * fraction",
        {"budget": budget.value, "fraction": max(0, fraction)},
        ctx.log,
        source="budget-purpose-amount",
    )
    if target == (rest[0].measure, rest[0].attribute):
        allocated = [
            evaluate(
                "budget * fraction",
                {"budget": budget.value, "fraction": r.value},
                ctx.log,
                source="budget-purpose-share",
            )
            for r in shares
        ]
        value = resource_residual(
            [budget.value], allocated, ctx.log, source="budget-purpose-remainder"
        )
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    ctx.log.consumed_resource_balance_keys.update(r.key() for r in [budget, *phrases])
    ctx.log.consumed_fraction_keys.update(r.key() for r in fractions)
    return Answer(
        "number",
        value,
        "Apply the destination share to the original budget, including an explicitly named remainder.",
    )
