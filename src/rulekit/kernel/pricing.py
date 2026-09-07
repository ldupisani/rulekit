"""Shared price arithmetic; callers own transaction and discount scope."""


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
