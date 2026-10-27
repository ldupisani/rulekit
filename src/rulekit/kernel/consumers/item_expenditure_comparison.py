"""Compare ordinary acquisitions priced by explicit package/content quotes."""
from collections import Counter, defaultdict
from math import isfinite

from . import consumer
from ..answer import Answer
from ..model import Expenditure, Price, Quantity
from ..numeric_evidence import audit_numeric_mentions
from ..pricing import resolve_expenditure_prices
from ..resource_equations import resource_residual
from ..source_coverage import partitive_quantity_source_units, uncovered_units


@consumer("item-expenditure-comparison")
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    acquisitions = list(ctx.store.by_kind(Quantity))
    prices = list(ctx.store.by_kind(Price))
    if (not acquisitions or not prices or ctx.store.collisions or ctx.store.quarantined
            or any(not isinstance(f, (Quantity, Price)) for f in ctx.store.facts)):
        return decline("the comparison needs a complete acquisition ledger and explicit unit quotes")
    expected = defaultdict(Counter)
    expenses, used = [], []
    covered = defaultdict(set)
    readings = {r.sentence_index: r for r in ctx.premises}
    for acquisition in acquisitions:
        unit, contents = acquisition.measure_ref, acquisition.content_ref
        if (acquisition.entity != ctx.query["entity"] or acquisition.provenance.assumption
                or acquisition.is_state or acquisition.time
                or acquisition.provenance.source != "fold"
                or not ctx.reg.word_in_category(acquisition.verb, "purchase")
                or acquisition.entity_ref.described or not acquisition.entity_ref.resolved
                or unit is None or contents is None
                or not unit.resolved or not contents.resolved or unit.described or contents.described
                or acquisition.value <= 0 or not isfinite(acquisition.value)
                or not float(acquisition.value).is_integer()):
            return decline("every acquisition needs one actual buyer, bare package/content identities and a positive whole count")
        quotes = [p for p in prices if (p.item, p.per, p.qualifier or "") ==
                  (contents.head, unit.head, "")]
        if len(quotes) != 1:
            return decline("each acquisition needs exactly one quote for the same item and package")
        quote = quotes[0]
        reading = readings.get(acquisition.provenance.sentence)
        footprint = partitive_quantity_source_units(reading, acquisition, ctx.reg) if reading else ()
        if not footprint:
            return decline("each acquisition needs a unique, explicitly bound partitive source")
        covered[reading.sentence_index].update(footprint)
        if quote.provenance.assumption or not isfinite(quote.value) or quote.value < 0:
            return decline("prices must be asserted, finite and nonnegative")
        expected[acquisition.provenance.sentence][acquisition.value] += 1
        expenses.append(Expenditure(
            acquisition.provenance, entity=acquisition.entity, item=contents.head,
            verb=acquisition.verb, position=acquisition.segment or 0,
            quantity=acquisition.value, unit_price=quote.value, measure=quote.measure,
        ))
        used.append(quote)
    if set(used) != set(prices) or len({p.measure for p in prices}) != 1:
        return decline("all quotes must be used in one currency")
    for price in prices:
        expected[price.provenance.sentence][price.value] += 1
    if (any(uncovered_units(r, covered[r.sentence_index]) for r in ctx.premises)
            or uncovered_units(ctx.question, ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises, ctx.question), expected,
                                      missing="missing", duplicate="duplicate")):
        return decline("every acquisition, quote and condition must be read")
    resolved, error = resolve_expenditure_prices(expenses, ctx.log)
    if error:
        return decline(error)
    a = [e.value for e in resolved if e.item == ctx.query["first"]]
    b = [e.value for e in resolved if e.item == ctx.query["second"]]
    if not a or not b or len(a) + len(b) != len(resolved) or ctx.query["first"] == ctx.query["second"]:
        return decline("the two distinct requested items must partition the ledger")
    if ctx.reg.word_in_category(ctx.query["direction"], "less_dir"):
        a, b = b, a
    value = resource_residual(a, b, ctx.log, source="item-expenditure-difference")
    if value < 0:
        return decline("the stated comparison direction contradicts the costs")
    ctx.log.consumed_quoted_price_keys.update(p.key() for p in prices)
    return Answer("number", value, "difference between package counts multiplied by their explicit unit prices")
