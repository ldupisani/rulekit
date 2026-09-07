"""Recover one unstated purchase cost using the shared account calculation."""

from . import ConsumerContext, consumer


@consumer("budget-item-cost")
def budget_item_cost(ctx: ConsumerContext):
    from ..account_totals import AccountTotal, resolve_account
    from ..answer import Answer

    item = ctx.query["item"]
    result = resolve_account(ctx, residual_item=(item, ctx.query.get("qualifier", "")))
    if not isinstance(result, AccountTotal):
        return result
    return Answer("number", result.value,
                  f"{result.opening.value:g} {result.opening.measure} budget − "
                  f"{result.closing.value:g} remaining − "
                  f"{sum(e.value for e in result.expenses):g} known costs = {result.value:g} for {item}")
