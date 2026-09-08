"""Resolve one explicit resource account without turning it into cash holdings."""

from collections import Counter
import math

from dataclasses import dataclass, replace
from .model import Expenditure, ResourceBalance


@dataclass(frozen=True)
class AccountTotal:
    opening: ResourceBalance
    closing: ResourceBalance | None
    expenses: tuple[Expenditure, ...]
    value: float


def has_resource_account(store):
    from .model import ResourceAllocation
    return bool(store.by_kind(ResourceBalance) or store.by_kind(ResourceAllocation))


def resolve_account(ctx, *, residual_item=None, extra_evidence=()):
    """One-account remainder, or one missing cost between explicit endpoints.

    Additional pricing evidence must be selected and checked by its caller.
    The same complete-event and numeric audit applies to every consumer.
    """
    from .answer import Answer
    from .evaluate import evaluate
    from .model import ResourceAccountingIssue, ResourceAllocation

    entity = ctx.query["entity"]
    if any(u.uid not in ctx.match.consumed and not u.features.get("pattern_consumed")
           and u.sense() not in {"article", "punct"} for u in ctx.question.units):
        return Answer("decline", None, "the account ask has an unread condition or qualifier")
    item, qualifier = residual_item or (None, None)
    balances = list(ctx.store.by_kind(ResourceBalance))
    opening = [b for b in balances if b.stage == "opening"]
    closing = [b for b in balances if b.stage == "closing"]
    if len(opening) != 1 or len(closing) > 1 or (residual_item and len(closing) != 1):
        return Answer("decline", None, "a residual cost needs one opening and one closing budget balance")
    start, end = opening[0], closing[0] if closing else None
    end_sentence = end.provenance.sentence if end else ctx.question.sentence_index
    if (start.entity != entity
            or any(b.owner and b.owner != entity for b in balances)
            or (end and (end.entity != entity or start.account != end.account
                         or start.qualifier != end.qualifier or start.measure != end.measure
                         or start.provenance.sentence >= end_sentence))):
        return Answer("decline", None, "budget endpoints disagree on participant, account, unit, or order")
    expenses = [e for e in ctx.store.by_kind(Expenditure)
                if start.provenance.sentence <= e.provenance.sentence < end_sentence]
    if any(e.provenance.sentence >= end_sentence for e in ctx.store.by_kind(Expenditure)):
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
    from .pricing import purchase_total_expression
    resolved = []
    for expense in expenses:
        if expense.unit_price is not None or expense.quantity is not None:
            if (expense.value is not None or expense.unit_price is None or expense.quantity is None
                    or not all(math.isfinite(v) and v >= 0 for v in (expense.unit_price, expense.quantity))):
                return Answer("decline", None, "a priced purchase needs a nonnegative count and unit price")
            value = evaluate(purchase_total_expression([(expense.quantity, expense.unit_price)]),
                             {}, ctx.log, source="expenditure-unit-price")
            expense = replace(expense, value=value)
        resolved.append(expense)
    expenses = resolved
    unknown = [e for e in expenses if e.value is None]
    if residual_item and (len(unknown) != 1 or (unknown[0].item, unknown[0].qualifier) != (item, qualifier)):
        return Answer("decline", None, "the requested item must be the one unknown purchase cost")
    if not residual_item and unknown:
        return Answer("decline", None, "an unpriced purchase leaves the available budget unknown")
    known = [e for e in expenses if e.value is not None]
    if any((e.item, e.qualifier) == (item, qualifier) for e in known):
        return Answer("decline", None, "the requested item also has a separate stated cost")
    if any(
        a.basis != b.basis and (a.item, a.qualifier) == (b.item, b.qualifier)
        for i, a in enumerate(expenses) for b in expenses[i + 1:]
    ):
        return Answer("decline", None, "a purchase and payment may describe the same transaction")
    evidence = [*balances, *known, *extra_evidence]
    if any(not math.isfinite(e.value) or e.value < 0 for e in evidence):
        return Answer("decline", None, "budget amounts must be finite and non-negative")

    # Audit original numeric mentions, not just whichever facts survived the
    # reader. This catches incomplete lists and omitted adjustments, including
    # equal-valued mentions that a global set or arithmetic log would conceal.
    captured = {}
    for fact in evidence:
        amounts = ((fact.quantity, fact.unit_price) if isinstance(fact, Expenditure)
                   and fact.unit_price is not None else (fact.value,))
        captured.setdefault(fact.provenance.sentence, Counter()).update(amounts)
    from .numeric_evidence import audit_numeric_mentions
    error = audit_numeric_mentions(ctx.premises, captured,
                                   missing="a stated value lies outside the complete budget equation",
                                   duplicate="budget evidence repeats a numeric mention")
    if error:
        return Answer("decline", None, error)
    issue_reasons = {
        "nonactual": "budget events must be actual and affirmative",
        "alternative": "an alternative event cannot close a definite budget",
        "unread-event": "a purchase or spending event has no complete cost target",
        "additional-change": "an additional resource change is outside the budget equation",
        "unsettled-request": "an order does not establish an actual purchase or payment",
        "owner-reference": "the account's possessive reference does not establish a personal owner",
    }
    for issue in ctx.store.by_kind(ResourceAccountingIssue):
        if start.provenance.sentence <= issue.provenance.sentence <= end_sentence:
            return Answer("decline", None, issue_reasons.get(issue.reason, "resource accounting is incomplete"))
    allocations = list(ctx.store.by_kind(ResourceAllocation))
    if any(
        a.provenance.sentence != start.provenance.sentence or a.head_span != start.allocation_span
        for a in allocations
    ):
        return Answer("decline", None, "an allocation phrase has no unique participant and account")
    from .resource_equations import resource_residual
    result = resource_residual([start.value], [e.value for e in known],
                               ctx.log, source="account-remainder")
    if residual_item:
        result = evaluate(f"{result} - {end.value}", {}, ctx.log, source="budget-item-cost")
    elif end and not math.isclose(result, end.value, rel_tol=1e-9, abs_tol=1e-9):
        return Answer("decline", None, "the stated remainder disagrees with the complete account")
    if result < 0:
        return Answer("decline", None, "known spending and remainder exceed the opening budget")
    ctx.log.consumed_resource_balance_keys.update(b.key() for b in balances)
    ctx.log.consumed_resource_balance_keys.update(a.key() for a in allocations)
    ctx.log.consumed_expenditure_keys.update(e.key() for e in known)
    return AccountTotal(start, end, tuple(known), result)
