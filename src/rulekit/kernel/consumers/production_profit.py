"""Closed production accounts: scheduled sales less unit and setup costs."""

from collections import Counter
from math import isfinite

from . import consumer
from ..model import CommercialTerm, Rate
from ..source_coverage import uncovered_document_units
from ..numeric_evidence import audit_numeric_mentions
from ..rate_calculation import apply_rate, convert_duration
from ..resource_equations import resource_residual
from ..evaluate import evaluate


def compatible_products(reg, items):
    """A declared work/representation family, not global noun synonymy."""
    if len(set(items)) == 1:
        return True
    families = [category for category in reg.cat_descendants("commercial_product_family")
                if category != "commercial_product_family"
                and all(reg.word_in_category(item, category) for item in items)]
    return len(families) == 1


@consumer("production-profit")
def consume(ctx):
    from ..answer import Answer, AnswerAssumption, AnswerProof, ProofStep, SemanticNode

    def decline(reason):
        return Answer("decline", None, reason)

    terms = list(ctx.store.by_kind(CommercialTerm))
    groups = {basis: [f for f in terms if f.basis == basis]
              for basis in ("setup", "unit-cost", "sale-factor", "sale-price")}
    setups, costs = groups["setup"], groups["unit-cost"]
    sales = groups["sale-factor"] + groups["sale-price"]
    if (len(setups) != 1 or len(costs) != 1 or len(sales) != 1 or len(terms) != 3):
        return decline("profit needs one fixed setup cost, one unit cost and one unit sale quote")
    setup, cost, sale = setups[0], costs[0], sales[0]
    entity = ctx.query["entity"]
    if (setup.entity != entity or sale.entity != entity or cost.entity not in ("", entity)
            or any(f.provenance.assumption for f in terms)):
        return decline("production costs and sale price must belong to one actual participant")
    if (setup.measure != cost.measure or (sale.measure and sale.measure != cost.measure)):
        return decline("production account currencies disagree")
    if not setup.provenance.sentence < cost.provenance.sentence < sale.provenance.sentence:
        return decline("the production account needs a preceding setup and unit-cost reference")
    if sale.basis == "sale-factor" and sale.provenance.sentence != cost.provenance.sentence + 1:
        return decline("the relative sale quote needs an immediately preceding unit-cost reference")
    rates = list(ctx.store.by_kind(Rate))
    unit_rates = [r for r in rates if r.entity == entity
                  and ctx.reg.word_in_category(r.measure, "commercial_product")
                  and ctx.reg.word_in_category(r.verb, "sell")]
    if len(unit_rates) != 1:
        return decline("profit needs one unambiguous unit-sales rate")
    rate = unit_rates[0]
    bridges = [r for r in rates if r.entity == entity and r.measure == rate.per
               and r.verb == rate.verb and r is not rate]
    if len(bridges) != 1 or len(rates) != 2:
        return decline("profit needs one complete active-period schedule")
    bridge = bridges[0]
    items = [setup.item, cost.item, rate.measure] + ([sale.item] if sale.item else [])
    if not compatible_products(ctx.reg, items):
        return decline("the work, unit cost and sold units do not identify one product family")
    if any(not isfinite(f.value) or f.value < 0 for f in (*terms, *rates)):
        return decline("production costs, prices and schedules must be finite and nonnegative")
    if any(f.provenance.assumption for f in rates):
        return decline("the sales schedule is not asserted")
    # This is a closed account, not a guess that unread cash flows are zero.
    if uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed):
        return decline("the production account contains an unread condition or transaction")
    expected = {}
    for f in (*terms, *rates):
        expected.setdefault(f.provenance.sentence, Counter()).update([f.value])
    elapsed = float(ctx.query["elapsed"])
    expected.setdefault(ctx.question.sentence_index, Counter()).update([elapsed])
    error = audit_numeric_mentions((*ctx.premises, ctx.question), expected,
                                   missing="a number lies outside the production account",
                                   duplicate="production evidence repeats a source amount")
    if error:
        return decline(error)
    periods = convert_duration(elapsed, ctx.query["unit"], bridge.per, ctx.reg,
                               ctx.log, source="profit-period", allow_cadence=True)
    if periods is None or not isfinite(periods) or periods < 0:
        return decline("the asked duration cannot be converted to the sales period")
    active = apply_rate(bridge, periods, ctx.log, source="profit-active-periods")
    units = apply_rate(rate, active, ctx.log, source="profit-units")
    if not units.is_integer():
        return decline("the sales schedule implies a fractional count of units")
    price = (evaluate(f"{cost.value} * {sale.value}", {}, ctx.log,
                      source="relative-unit-sale-price")
             if sale.basis == "sale-factor" else sale.value)
    revenue = evaluate(f"{units} * {price}", {}, ctx.log, source="sales-revenue")
    variable = evaluate(f"{units} * {cost.value}", {}, ctx.log, source="unit-production-costs")
    value = resource_residual([revenue], [variable, setup.value], ctx.log,
                              source="production-profit")
    ctx.log.consumed_commercial_term_keys.update(f.key() for f in terms)
    ctx.log.consumed_rate_keys.update(f.key() for f in rates)
    detail = (f"One closed production stream: {setup.item} and {cost.item} identify the "
              f"work and its saleable units; {units:g} units sold, revenue {revenue:g}, "
              f"unit costs {variable:g}, setup cost {setup.value:g}. No other costs are assumed.")
    node = SemanticNode("production-profit", (("entity", entity), ("measure", cost.measure)))
    proof = AnswerProof(node, (ProofStep("closed-production-account", node,
                                        tuple(terms + rates), detail),))
    return Answer("number", value, detail, proof=proof,
                  assumptions=(AnswerAssumption("closed-production-costs",
                      "The profit calculation includes only the stated costs of this production stream.",
                      tuple(sorted({r.provenance.sentence for r in terms}))),))
