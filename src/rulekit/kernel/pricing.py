"""Shared price arithmetic; callers own transaction and discount scope."""

import math
from dataclasses import replace


def expenditure_mentions(expense):
    """Original source operands, not derived totals, keyed by unit identity."""
    mentions = {}
    if expense.unit_price is not None:
        mentions.update({expense.position: expense.unit_price,
                         expense.quantity_position: expense.quantity})
    elif expense.cost_factor is not None:
        mentions[expense.cost_factor_position] = expense.cost_factor
    elif expense.value is not None:
        mentions[expense.position] = expense.value
    if expense.lot_quantity is not None:
        mentions[expense.lot_position] = expense.lot_quantity
    return mentions


def resolve_expenditure_prices(expenses, log):
    """Resolve explicit unit prices and exact same-buyer lot-price references.

    Returns (resolved records, error). Unknown costs remain unknown, but an
    ambiguous, cyclic, or missing comparison is an error, never a residual.
    Callers still own account scope, event completeness and numeric auditing.
    """
    from .evaluate import evaluate

    resolved = []
    for expense in expenses:
        if not expense.complete:
            return [], "a purchase has an incomplete list or participant identity"
        if any(v is None or not math.isfinite(v) or v < 0
               for v in expenditure_mentions(expense).values()):
            return [], "purchase operands must be finite and nonnegative"
        if expense.unit_price is not None or expense.quantity is not None:
            if (expense.value is not None or expense.unit_price is None or expense.quantity is None
                    or expense.cost_reference):
                return [], "a priced purchase needs one count and one unit price"
            value = evaluate(purchase_total_expression([(expense.quantity, expense.unit_price)]),
                             {}, log, source="expenditure-unit-price")
            expense = replace(expense, value=value)
        resolved.append(expense)
    pending = {i for i, e in enumerate(resolved) if e.cost_reference}
    while pending:
        changed = False
        for i in tuple(pending):
            expense = resolved[i]
            anchors = [(j, e) for j, e in enumerate(resolved) if j != i
                       and e.entity == expense.entity and e.basis == expense.basis
                       and (e.item, e.qualifier) == (expense.cost_reference, expense.cost_reference_qualifier)]
            if (len(anchors) != 1 or expense.cost_factor is None or expense.cost_factor <= 0
                    or expense.value is not None):
                return [], "a price comparison needs exactly one distinct compatible purchase"
            j, anchor = anchors[0]
            if j in pending:
                continue
            if anchor.value is None or anchor.measure is None:
                return [], "the referenced purchase has no known total price"
            value = evaluate(f"{anchor.value} * {expense.cost_factor}", {}, log,
                             source="expenditure-relative-price")
            resolved[i] = replace(expense, value=value, measure=anchor.measure)
            pending.remove(i)
            changed = True
        if not changed:
            return [], "price comparisons form an unanchored cycle"
    return resolved, None


def purchase_total_expression(lines, discount=None):
    """Build an auditable expression from (quantity, unit price) pairs.

    Do not infer which purchases a discount belongs to here. The caller must
    establish that scope before supplying it.
    """
    if not lines:
        return None
    base = " + ".join(f"{quantity} * {price}" for quantity, price in lines)
    if discount is None:
        return base
    if discount.scope == "total":
        return (f"({base}) * (1 - {discount.value})" if discount.percent
                else f"({base}) - {discount.value}")
    if discount.scope == "per_unit" and not discount.percent:
        quantities = " + ".join(str(quantity) for quantity, _ in lines)
        return f"({base}) - ({quantities}) * {discount.value}"
    return None
