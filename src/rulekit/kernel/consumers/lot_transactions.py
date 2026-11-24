"""Amount paid for measured packages, promotional awards, discounts and cash tender."""

from .indexed_path import ordinal_index
from .group_members import eligible_member_count, read_group_members
from ..monetary import convert_money, price_terms
from ..model import EventTime, Price, Quantity
from ..source_coverage import (
    covered_temporal_annotation,
    partitive_quantity_source_units,
    price_source_units,
)
from ..quantity_account import quantity_account, require, whole_count
from ..rate_calculation import convert_units


def purchase_lines(a, ctx, kinds):
    """Read explicit package facts and ordinary folded purchases through the same item identity."""
    purchases = [
        (row.entity_ref, row.container_ref, row.measure, row.value)
        for kind in kinds
        for row in a.select(kind, "value")
    ]
    for row in ctx.store.by_kind(Quantity):
        if ctx.reg.word_in_category(row.verb, "purchase_transaction_verb"):
            reading = next(r for r in ctx.premises if r.sentence_index == row.provenance.sentence)
            units = partitive_quantity_source_units(reading, row, ctx.reg)
            require(units, "A package purchase needs explicitly identified buyer, package and contents.")
            a.covered.setdefault(reading.sentence_index, set()).update(units)
            a.include(row, row.value)
            purchases.append((row.entity_ref, row.content_ref, row.measure, row.value))
    return purchases


@quantity_account("measured-purchase", "purchase-package-size")
def measured_purchase(a, ctx):
    purchases = purchase_lines(a, ctx, ["measured-purchase-packages"])
    require(len(purchases) == 1, "The package count must identify one purchase.")
    buyer, goods, package, count = purchases[0]
    size = a.one("purchase-package-size", "value")
    quotes = list(ctx.store.by_kind(Price))
    require(len(quotes) == 1, "The material needs a single quote with a stated denominator.")
    quote = quotes[0]
    unit_price, _, price_unit = price_terms(quote, ctx.reg)
    a.include(quote, unit_price)
    require(
        ctx.query_reference() == buyer
        and buyer.resolved
        and goods.head == quote.item
        and not quote.qualifier
        and price_unit
        and package == size.container
        and (not size.acquisition or size.acquisition_ref == goods),
        "The buyer, goods and package type must match the purchase and quote.",
    )
    require(
        count.is_integer() and count >= 0 and size.value > 0,
        "Package counts must be whole and the amount per package positive.",
    )
    measured = convert_units(
        size.value, size.measure, price_unit, ctx.reg, ctx.log, source="package-quote-denominator"
    )
    require(measured is not None, "The measured contents must convert to the quoted unit.")
    ctx.log.consumed_quoted_price_keys.add(quote.key())
    return a.finish(
        a.calculate("count * amount * price", count=count, amount=measured, price=unit_price),
        "Number of packages times measured amount per package times unit price.",
    )


@quantity_account("periodic-giveaway", "periodic-promotion")
def periodic_giveaway(a, ctx):
    offer = a.one("periodic-promotion")
    seller = a.one("promotion-seller", optional=True)
    quotes = list(ctx.store.by_kind(Price))
    require(len(quotes) == 1, "The promoted item needs one unit price.")
    price = quotes[0]
    a.include(price, price.value)
    sales = a.one("promoted-sales-value", "value")
    stop = a.one("promotion-paid-ending", optional=True)
    requested = ctx.match.slots["free"]
    if requested.features.get("measure_anaphor"):
        item = requested.features.get("antecedent_lemma") or offer.measure
    else:
        item = ctx.query["item"]
    interval = ordinal_index(offer.marker, ctx.reg)
    require(
        interval
        and interval > 1
        and price.value > 0
        and not price.per
        and not price.qualifier
        and ctx.reg.word_in_category(offer.attribute, "complimentary_descriptor")
        and offer.measure == price.item == sales.container
        and item == offer.measure
        and ctx.query_reference() == sales.entity_ref
        and sales.entity_ref.resolved
        and (not seller or seller.entity_ref == sales.entity_ref)
        and (not stop or stop.entity_ref == sales.entity_ref),
        "The recurring free item, price, seller and sales must describe one promotion.",
    )
    revenue = convert_units(
        sales.value, sales.measure, price.measure, ctx.reg, ctx.log, source="sales-revenue-denomination"
    )
    require(revenue is not None, "Revenue and unit price must share a currency.")
    ctx.log.consumed_currency_price_keys.add(price.key())
    count = a.calculate("revenue / price", revenue=revenue, price=price.value)
    count = whole_count(count, "The revenue must cover a whole number of paid units.")
    a.assume(
        "one-item-per-customer",
        "Each customer receives one item and the promotion starts with the first customer.",
        offer,
    )
    awards = a.calculate("paid // cycle", paid=count, cycle=interval - 1)
    if count and count % (interval - 1) == 0:
        if stop:
            awards -= 1
        else:
            a.assume(
                "earned-free-item-delivered",
                "The next customer received the final earned free item.",
                offer,
                sales,
            )
    return a.finish(awards, "Each complete promotion cycle contains one free item.")


@quantity_account("cohort-purchase", "cohort-discount")
def cohort_purchase(a, ctx):
    groups, sizes, observations = read_group_members(a)
    discount = a.one("cohort-discount", "value")
    if discount.boundary_value is not None:
        a.extra_value(discount, discount.boundary_value)
    eligible = eligible_member_count(a, discount, sizes, observations)
    change_requested = ctx.query["mode"] == "change"
    tender = a.one("group-tender", "value", optional=not change_requested)
    quotes = list(ctx.store.by_kind(Price))
    require(len(quotes) == 1, "The group purchase needs one unit price.")
    quote = quotes[0]
    price, currency, basis = price_terms(quote, ctx.reg)
    require(
        not quote.qualifier and (not basis or basis == quote.item) and price >= 0,
        "The price must apply to one unit of the purchased offering.",
    )
    a.include(quote, price)
    if quote.provenance.source == "fold":
        reading = next(r for r in ctx.premises if r.sentence_index == quote.provenance.sentence)
        a.covered[reading.sentence_index] = price_source_units(reading, quote, ctx.reg)

    purchase = a.one("purchase-per-person", "value", optional=True)
    if purchase:
        if purchase.marker:
            roster_sentence = groups[0].provenance.sentence
            referents = [discount, *(row for rows in observations.values() for row in rows)]
            require(
                roster_sentence < purchase.provenance.sentence
                and not any(
                    roster_sentence < row.provenance.sentence < purchase.provenance.sentence
                    for row in referents
                ),
                "Specify whether the whole group or the last mentioned subgroup bought the items.",
            )
        require(purchase.entity == quote.item, "The purchase and quote must name the same offering.")
        quantity = whole_count(purchase.value, "The purchase needs a whole count per person.")
        require(quantity > 0, "Each person must purchase at least one unit.")
    else:
        quantity = ctx.reg.attribute_value(quote.item, "assumed_units_per_member")
        require(quantity is not None, "How many units does each person purchase?")
        a.assume(
            "assumed-purchase-per-member",
            f"Each person purchases {quantity:g} unit of the quoted {quote.item}.",
            *groups,
            quote,
        )
    require(
        not discount.entity or discount.entity == quote.item,
        "The discount and purchase must name the same offering.",
    )
    require(
        quantity == 1 or discount.entity,
        "For multiple units, specify whether the discount applies to each item.",
    )
    saving = convert_money(discount.value, discount.measure, currency, ctx.reg, ctx.log)
    require(
        saving is not None and saving <= price, "The unit discount must be compatible with the price."
    )
    total = a.calculate(
        "quantity * (people * price - eligible * saving)",
        quantity=quantity,
        people=sum(sizes.values()),
        price=price,
        eligible=eligible,
        saving=saving,
    )
    if tender:
        payable = convert_money(total, currency, tender.measure, ctx.reg, ctx.log)
        require(
            payable is not None and tender.value >= payable,
            "The cash tendered must cover the discounted purchase.",
        )
    for group in groups:
        if group.marker == "lexical" and group.entity_ref != discount.container_ref:
            a.assume(
                "regular-price-for-unspecified-members",
                "Members of the accompanying collective pay the regular price. Their eligibility is unspecified.",
                group,
                discount,
            )
    ctx.log.consumed_currency_price_keys.add(quote.key())
    if change_requested:
        return a.finish(
            a.calculate("cash - total", cash=tender.value, total=payable),
            "Subtract the discounted purchase total from the cash tendered.",
        )
    return a.finish(total, "Sum the unit prices and apply the discount to eligible purchases.")


@quantity_account("purchase-savings", ("unit-saving", "ordinary-unit-price"))
def purchase_savings(a, ctx):
    regular = a.select("ordinary-unit-price", "value")
    reduced = a.select("reduced-unit-price", "value")
    for current in reduced:
        if current.attribute:
            periods = {(current.provenance.sentence, current.attribute)}
            for annotation in ctx.store.by_kind(EventTime):
                if covered_temporal_annotation(annotation, ctx.premises, current.entity, periods):
                    a.include(annotation)
    direct = a.select("unit-saving", "value")
    purchases = purchase_lines(a, ctx, ["saving-purchase-line", "measured-purchase-packages"])
    key = lambda r: (r.entity_ref, r.marker)
    prices = {key(r): r for r in regular}
    discounts = {key(r): (r.value, r.measure) for r in direct}
    require(
        len(prices) == len(regular) and len(discounts) == len(direct) and len(reduced) == len(regular),
        "A purchase lot must have one unit discount or a pair of prices.",
    )
    for r in reduced:
        old = prices.pop(key(r), None)
        require(old and key(r) not in discounts, "Both prices must identify the same lot.")
        price = convert_units(
            r.value, r.measure, old.measure, ctx.reg, ctx.log, source="sale-price-denomination"
        )
        require(
            price is not None and old.value >= price,
            "The reduced price must be in a compatible currency.",
        )
        discounts[key(r)] = (
            a.calculate("regular - reduced", regular=old.value, reduced=price),
            old.measure,
        )
    require(
        purchases and {(goods, package) for _, goods, package, _ in purchases} == set(discounts),
        "Every purchased product and package size needs a matching unit saving.",
    )
    total = 0
    currency = direct[0].measure if direct else regular[0].measure
    for buyer, goods, package, count in purchases:
        require(
            buyer == ctx.query_reference(), "The purchases and question must identify the same buyer."
        )
        amount, unit = discounts[(goods, package)]
        saving = convert_units(
            amount, unit, currency, ctx.reg, ctx.log, source="unit-saving-denomination"
        )
        require(saving is not None, "The savings must share a currency.")
        total = a.calculate("total + count * saving", total=total, count=count, saving=saving)
    return a.finish(total, "Sum the saving per purchase unit multiplied by the number bought.")
