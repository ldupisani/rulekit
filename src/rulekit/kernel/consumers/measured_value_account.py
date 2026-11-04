"""Use a measured unit price for inverse purchases and changes in asset value."""

from math import isfinite

from . import consumer
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..answer import Answer
from ..evaluate import evaluate
from ..model import BatchEvidence, Price, Quantity
from ..rate_calculation import convert_units
from ..reference_identity import reference_from_unit, constrains
from ..resource_equations import resource_residual
from ..source_coverage import quantity_ledger_source_units, purchase_purpose_roles


@consumer("measured-value-account")
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    prices = list(ctx.store.by_kind(Price))
    quantities = list(ctx.store.by_kind(Quantity))
    if len(prices) != 1:
        return decline("one unambiguous measured unit quote is required")
    price = prices[0]
    if (
        not isfinite(price.value)
        or price.value <= 0
        or not price.per
        or not price.measure
    ):
        return decline(
            "the measured quote needs a positive price and explicit denomination and unit"
        )
    facts = rows + prices + quantities
    operands = [(price, [price.value])]
    covered = {}
    if ctx.query["operation"] == "inverse-purchase":
        purposes = [
            (r, roles)
            for r in ctx.premises
            if (roles := purchase_purpose_roles(r, ctx.reg)) is not None
        ]
        openings = [r for r in rows if r.kind == "purchase-cash-opening"]
        closings = [r for r in rows if r.kind == "purchase-cash-closing"]
        if (
            len(purposes) != 1
            or len(openings) != 1
            or len(closings) != 1
            or len(rows) != 2
            or quantities
        ):
            return decline(
                "an inverse purchase needs one product purpose and before-and-after cash amounts"
            )
        (purpose, (purpose_actor, purpose_item)), opening, closing = (
            purposes[0],
            openings[0],
            closings[0],
        )
        actor = reference_from_unit(ctx.match.slots["who"])
        if (
            any(r.entity_ref != actor for r in rows)
            or price.item != ctx.query["item"]
            or purpose_actor != actor
            or purpose_item.head != price.item
            or purpose_item.described
            or opening.provenance.sentence <= purpose.sentence_index
            or closing.provenance.sentence != opening.provenance.sentence
            or closing.position <= opening.position
            or any(not isfinite(r.value) or r.value < 0 for r in (opening, closing))
        ):
            return decline(
                "the cash change and quoted product must belong to the same single purchase"
            )
        amounts = [
            convert_units(
                r.value,
                r.measure,
                price.measure,
                ctx.reg,
                ctx.log,
                source="purchase-cash-denomination",
            )
            for r in (opening, closing)
        ]
        if any(v is None for v in amounts) or amounts[0] < amounts[1]:
            return decline(
                "the closing cash must not exceed the opening amount in a compatible currency"
            )
        spent = resource_residual(
            [amounts[0]], [amounts[1]], ctx.log, source="purchase-cash-spent"
        )
        amount = evaluate(
            "spent / unit_price",
            dict(spent=spent, unit_price=price.value),
            ctx.log,
            source="inverse-measured-purchase",
        )
        value = convert_units(
            amount,
            price.per,
            ctx.query["unit"],
            ctx.reg,
            ctx.log,
            source="purchased-measure-output",
        )
        if value is None:
            return decline(
                "the purchased measure must match the quoted measurement dimension"
            )
        operands += [(opening, [opening.value]), (closing, [closing.value])]
    elif ctx.query["operation"] == "valuation-change":
        scales = [r for r in rows if r.kind == "valuation-scale"]
        sellers = [r for r in rows if r.kind == "valuation-seller"]
        if (
            len(scales) != 1
            or len(sellers) != 1
            or len(rows) != 2
            or len(quantities) != 1
        ):
            return decline(
                "a value change needs one observed measurement, scale and matching unit quote"
            )
        scale, seller, opening = scales[0], sellers[0], quantities[0]
        asset = reference_from_unit(ctx.match.slots["who"])
        if (
            asset != opening.entity_ref
            or scale.entity_ref != asset
            or not constrains(seller.container_ref, asset)
            or asset.owner != seller.entity_ref
            or price.item != asset.head
            or ctx.query.get("property")
            and scale.measure != ctx.query["property"]
            or not ctx.reg.word_in_category(opening.verb, "measurement_mass_verb")
            or not ctx.reg.word_in_category(opening.measure, "mass_unit")
            or not isfinite(opening.value)
            or opening.value < 0
            or not isfinite(scale.fraction)
            or scale.fraction < 1
            or scale.provenance.sentence <= opening.provenance.sentence
            or seller.provenance.sentence <= scale.provenance.sentence
        ):
            return decline(
                "the valuation must identify the same owned asset, measurement and subsequent increase"
            )
        reading = next(
            r for r in ctx.premises if r.sentence_index == opening.provenance.sentence
        )
        footprint = quantity_ledger_source_units(reading, [opening], ctx.reg)
        if not footprint:
            return decline(
                "the observed measurement must have a complete source clause"
            )
        covered[reading.sentence_index] = footprint
        growth = evaluate(
            "opening * (factor - 1)",
            dict(opening=opening.value, factor=scale.fraction),
            ctx.log,
            source="measured-asset-growth",
        )
        growth = convert_units(
            growth,
            opening.measure,
            price.per,
            ctx.reg,
            ctx.log,
            source="valuation-measure-unit",
        )
        if growth is None:
            return decline(
                "the asset measurement must match the quoted price dimension"
            )
        value = evaluate(
            "growth * unit_price",
            dict(growth=growth, unit_price=price.value),
            ctx.log,
            source="measurement-based-value-increase",
        )
        operands += [(opening, [opening.value]), (scale, [scale.fraction])]
    else:
        return decline("the measured value operation is not declared")
    if not closed_evidence(ctx, facts, operands, covered=covered):
        return decline(
            "every measurement, cash amount, quote and condition must be explained"
        )
    ctx.log.consumed_currency_price_keys.add(price.key())
    ctx.log.consumed_quoted_price_keys.add(price.key())
    return finish_batch_answer(
        ctx,
        facts,
        value,
        "apply the explicit unit quote to the conserved measurement or monetary difference",
    )
