"""Recover one unstated line-item cost from a closed resource allocation."""

from collections import Counter
import math

from . import ConsumerContext, consumer


@consumer("budget-item-cost")
def budget_item_cost(ctx: ConsumerContext):
    from ..answer import Answer, _ACCOUNTED_VALUE_KINDS
    from ..evaluate import evaluate
    from ..model import Expenditure, ResourceAccountingIssue, ResourceAllocation, ResourceBalance

    entity = ctx.query["entity"]
    item = ctx.query["item"]
    qualifier = ctx.query.get("qualifier", "")
    balances = list(ctx.store.by_kind(ResourceBalance))
    opening = [b for b in balances if b.stage == "opening"]
    closing = [b for b in balances if b.stage == "closing"]
    if len(opening) != 1 or len(closing) != 1:
        return Answer("decline", None, "a residual cost needs one opening and one closing budget balance")
    start, end = opening[0], closing[0]
    if (start.entity != entity or end.entity != entity or start.account != end.account
            or start.qualifier != end.qualifier
            or any(b.owner and b.owner != entity for b in balances)
            or start.measure != end.measure
            or start.provenance.sentence >= end.provenance.sentence):
        return Answer("decline", None, "budget endpoints disagree on participant, account, unit, or order")
    expenses = [e for e in ctx.store.by_kind(Expenditure)
                if start.provenance.sentence <= e.provenance.sentence < end.provenance.sentence]
    if any(e.provenance.sentence >= end.provenance.sentence for e in ctx.store.by_kind(Expenditure)):
        return Answer("decline", None, "a later purchase is outside the closed budget interval")
    if any(e.provenance.assumption for e in [*balances, *expenses]):
        return Answer("decline", None, "budget evidence must be asserted rather than conditional")
    if any(e.entity != entity or (e.measure and e.measure != start.measure) for e in expenses):
        return Answer("decline", None, "all costs must belong to the same participant and currency")
    if any(e.account and (
        e.account != start.account or e.account_qualifier != start.qualifier
        or (e.account_owner and e.account_owner != entity)
    ) for e in expenses):
        return Answer("decline", None, "a transaction names a different resource account")
    unknown = [e for e in expenses if e.value is None]
    if len(unknown) != 1 or (unknown[0].item, unknown[0].qualifier) != (item, qualifier):
        return Answer("decline", None, "the requested item must be the one unknown purchase cost")
    known = [e for e in expenses if e.value is not None]
    if any((e.item, e.qualifier) == (item, qualifier) for e in known):
        return Answer("decline", None, "the requested item also has a separate stated cost")
    if any(
        a.basis != b.basis and (a.item, a.qualifier) == (b.item, b.qualifier)
        for i, a in enumerate(expenses) for b in expenses[i + 1:]
    ):
        return Answer("decline", None, "a purchase and payment may describe the same transaction")
    evidence = [start, end, *known]
    if any(not math.isfinite(e.value) or e.value < 0 for e in evidence):
        return Answer("decline", None, "budget amounts must be finite and non-negative")

    # Audit original numeric mentions, not just whichever facts survived the
    # reader. This catches incomplete lists and omitted adjustments, including
    # equal-valued mentions that a global set or arithmetic log would conceal.
    captured = {}
    for fact in evidence:
        captured.setdefault(fact.provenance.sentence, Counter())[fact.value] += 1
    for reading in ctx.premises:
        available = captured.get(reading.sentence_index, Counter()).copy()
        for unit in reading.units:
            if unit.features.get("value_kind") in _ACCOUNTED_VALUE_KINDS:
                value = float(unit.features["value"])
                if available[value] <= 0:
                    return Answer("decline", None, "a stated value lies outside the complete budget equation")
                available[value] -= 1
        if any(available.values()):
            return Answer("decline", None, "budget evidence repeats a numeric mention")
    issue_reasons = {
        "nonactual": "budget events must be actual and affirmative",
        "alternative": "an alternative event cannot close a definite budget",
        "unread-event": "a purchase or spending event has no complete cost target",
        "additional-change": "an additional resource change is outside the budget equation",
        "unsettled-request": "an order does not establish an actual purchase or payment",
        "owner-reference": "the account's possessive reference does not establish a personal owner",
    }
    for issue in ctx.store.by_kind(ResourceAccountingIssue):
        if start.provenance.sentence <= issue.provenance.sentence <= end.provenance.sentence:
            return Answer("decline", None, issue_reasons.get(issue.reason, "resource accounting is incomplete"))
    allocations = list(ctx.store.by_kind(ResourceAllocation))
    if any(
        a.provenance.sentence != start.provenance.sentence or a.head_span != start.allocation_span
        for a in allocations
    ):
        return Answer("decline", None, "an allocation phrase has no unique participant and account")
    parts = " + ".join(str(e.value) for e in known) or "0"
    result = evaluate(f"{start.value} - {end.value} - ({parts})", {}, ctx.log, source="budget-item-cost")
    if result < 0:
        return Answer("decline", None, "known spending and remainder exceed the opening budget")
    ctx.log.consumed_resource_balance_keys.update(b.key() for b in balances)
    ctx.log.consumed_resource_balance_keys.update(a.key() for a in allocations)
    ctx.log.consumed_expenditure_keys.update(e.key() for e in known)
    return Answer("number", result,
                  f"{start.value:g} {start.measure} budget − {end.value:g} remaining "
                  f"− {sum(e.value for e in known):g} known costs = {result:g} for {item}")
