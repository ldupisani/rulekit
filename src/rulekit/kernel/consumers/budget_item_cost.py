"""A scoped purchase cost, or one unstated cost in a closed account."""

from . import ConsumerContext, consumer


@consumer("budget-item-cost")
def budget_item_cost(ctx: ConsumerContext):
    from ..account_totals import AccountTotal, resolve_account
    from ..answer import Answer

    item = ctx.query["item"]
    from ..account_totals import has_resource_account
    from ..purchase_totals import has_relative_purchase_prices, relative_purchase_total
    if (not has_resource_account(ctx.store) and has_relative_purchase_prices(ctx.store)
            and ctx.reg.word_in_category(item, "purchase_collection_noun")):
        return relative_purchase_total(ctx, collection=item)
    result = resolve_account(ctx, residual_item=(item, ctx.query.get("qualifier", "")))
    if not isinstance(result, AccountTotal):
        return result
    return Answer("number", result.value,
                  f"{result.opening.value:g} {result.opening.measure} budget − "
                  f"{result.closing.value:g} remaining − "
                  f"{sum(e.value for e in result.expenses):g} known costs = {result.value:g} for {item}")
