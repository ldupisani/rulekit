"""Complete actual purchase totals with exact relative lot-price evidence."""

from collections import Counter

from .model import Expenditure, ResourceAccountingIssue
from .pricing import expenditure_mentions, resolve_expenditure_prices


def has_relative_purchase_prices(store):
    return any(e.cost_reference for e in store.by_kind(Expenditure))


def residual_purchase_unit_price(ctx):
    """One equal-price lot in a complete, single-buyer transaction envelope."""
    import math
    from .answer import Answer, AnswerProof, ProofStep, SemanticNode
    from .evaluate import evaluate
    from .model import Predication, Price, PurchaseTotal, Quantity, QuantityEventContext
    from .numeric_evidence import audit_numeric_mentions
    from .resource_equations import resource_residual

    def decline(reason):
        return Answer("decline", None, reason)

    totals = ctx.store.by_kind(PurchaseTotal)
    if len(totals) != 1 or ctx.store.collisions or ctx.store.quarantined:
        return decline("a residual unit price needs one unambiguous transaction total")
    total = totals[0]
    if not math.isfinite(total.value) or total.value < 0:
        return decline("the transaction total must be finite and nonnegative")
    from .resource_accounting import purchase_background_facts
    background = purchase_background_facts(ctx.store, total)
    if any(not isinstance(f, (PurchaseTotal, Expenditure, Quantity, Price, Predication, QuantityEventContext))
           and f not in background
           for f in ctx.store.facts):
        return decline("the purchase equation has additional or incomplete resource evidence")
    if any(p.provenance.sentence >= total.provenance.sentence for p in ctx.store.by_kind(Predication)):
        return decline("a transaction clause lies outside the complete purchase ledger")
    if any(u.uid not in ctx.match.consumed and u.sense() not in {"article", "punct"}
           for u in ctx.question.units):
        return decline("the unit-price ask has an unread scope or condition")
    target_slot = ctx.match.slots.get("item", ctx.match.slots.get("qty"))
    if target_slot is None or target_slot.features.get("qualifier") or target_slot.features.get("owner"):
        return decline("a residual price needs one unqualified item target")
    expenses = list(ctx.store.by_kind(Expenditure))
    from .resource_accounting import purchase_context_error
    contexts = list(ctx.store.by_kind(QuantityEventContext))
    context_error = purchase_context_error(contexts, expenses, ctx.reg)
    if context_error:
        return decline(context_error)
    if any(c.provenance.sentence >= total.provenance.sentence for c in contexts):
        return decline("a purchase introduction must precede its stated transaction total")
    if (not expenses or any(e.entity != total.entity or e.basis != "purchase"
                            or e.provenance.sentence < total.provenance.sentence
                            or e.account or e.channel or e.supplier for e in expenses)
            or any(e.provenance.assumption for e in [total, *expenses])):
        return decline("all purchase lines must belong to one actual buyer and transaction")
    if not any(e.provenance.sentence == total.provenance.sentence and e.event == total.event
               for e in expenses):
        return decline("the fronted total has no complete purchase event")
    resolved, error = resolve_expenditure_prices(expenses, ctx.log)
    if error:
        return decline(error)
    unknown = [e for e in resolved if e.value is None]
    if len(unknown) != 1:
        return decline("exactly one purchase lot may have an unknown cost")
    target = unknown[0]
    item = ctx.reg.plural_to_singular.get(ctx.query["item"], ctx.query["item"])
    if (target.item != item or target.qualifier or not target.uniform_price
            or target.lot_measure != item or target.lot_quantity is None
            or target.lot_quantity <= 0 or not float(target.lot_quantity).is_integer()
            or sum(e.item == item for e in expenses) != 1):
        return decline("the requested item needs one positive count and explicitly equal individual prices")
    known = [e for e in resolved if e.value is not None]
    if any(e.measure != total.measure for e in known):
        return decline("purchase lines and transaction total use different currencies")
    expected = {total.provenance.sentence: Counter([total.value])}
    for expense in expenses:
        expected.setdefault(expense.provenance.sentence, Counter()).update(expenditure_mentions(expense).values())
    error = audit_numeric_mentions(ctx.premises, expected,
                                   missing="a stated value is outside the complete purchase equation",
                                   duplicate="purchase evidence repeats a source amount")
    if error:
        return decline(error)
    residual = resource_residual([total.value], [e.value for e in known], ctx.log,
                                 source="purchase-residual")
    if residual < 0:
        return decline("known purchases exceed the stated total")
    unit_price = evaluate("remaining / count", {"remaining": residual, "count": target.lot_quantity},
                          ctx.log, source="purchase-unit-price")
    value = unit_price
    if ctx.query.get("qty_value") is not None:
        value = evaluate("price * count", {"price": unit_price, "count": float(ctx.query["qty_value"])},
                         ctx.log, source="requested-purchase-cost")
    ctx.log.consumed_expenditure_keys.update(e.key() for e in expenses)
    ctx.log.consumed_purchase_total_keys.add(total.key())
    node = SemanticNode("unit-price", (("entity", total.entity), ("item", item), ("value", value)))
    return Answer("number", value, f"{residual:g} {total.measure} remaining ÷ {target.lot_quantity:g} equal-priced items",
                  proof=AnswerProof(node, (
                      ProofStep("transaction-envelope", node, (total, *contexts),
                                "The fronted total covers the complete single-buyer purchase sequence, including its continuation."
                                + (" The introductory collection describes these items, not an additional purchase." if contexts else "")),
                      ProofStep("known-purchase-costs", node, tuple(known),
                                "Each counted purchase uses its own item and per-lot price; pairs are not individual pieces."),
                      ProofStep("residual-equal-unit-price", node, (target,),
                                f"({total.value:g} − {sum(e.value for e in known):g}) / {target.lot_quantity:g} = {unit_price:g}."),
                  ) + ((ProofStep("purchase-background", node, background,
                                  "Earlier non-quantitative context and unquantified balance evidence is retained, "
                                  "but does not determine the cost of this explicitly totalled transaction."),)
                       if background else ())))


def relative_purchase_total(ctx, *, collection=None):
    from .answer import Answer
    from .learn import _lemma
    from .numeric_evidence import audit_numeric_mentions
    from .resource_equations import resource_residual
    from .resource_accounting import purchase_collection_contains

    expenses = list(ctx.store.by_kind(Expenditure))
    if (not expenses or any(e.entity != ctx.query["entity"] or e.provenance.assumption
                            or e.basis != "purchase" for e in expenses)):
        return Answer("decline", None, "the purchase total needs one participant's actual purchases")
    if collection and (not ctx.reg.word_in_category(collection, "purchase_collection_noun")
                       or ctx.query.get("qualifier")
                       or any(not purchase_collection_contains(collection, e.item, ctx.reg) for e in expenses)):
        return Answer("decline", None, "the named collection does not contain the complete purchase basket")
    # A bare total or one declared collective noun can cover this basket.
    # Other item, time, supplier and account restrictions cannot be discarded.
    # Only ordinary definiteness is harmless here. Skipped selectors can
    # restrict the basket even when the item slot matched its collection.
    tail = [u for u in ctx.question.units if u.uid not in ctx.match.consumed
            and u.sense() != "punct"
            and not (u.sense() == "article" and ctx.reg.word_in_category(_lemma(u), "definite_article"))]
    if tail:
        if (len(tail) != 2 or not ctx.reg.word_in_category(_lemma(tail[0]), "spend_target_prep")
                or not ctx.reg.word_in_category(_lemma(tail[1]), "purchase_collection_noun")
                or tail[1].features.get("qualifier") or tail[1].features.get("owner")
                or any(not purchase_collection_contains(_lemma(tail[1]), e.item, ctx.reg) for e in expenses)):
            return Answer("decline", None, "the purchase ask has an unsupported or mismatched scope")
    if ctx.store.by_kind(ResourceAccountingIssue):
        return Answer("decline", None, "a purchase or resource event is incomplete or nonactual")
    resolved, error = resolve_expenditure_prices(expenses, ctx.log)
    if error:
        return Answer("decline", None, error)
    if any(e.value is None or e.measure is None for e in resolved):
        return Answer("decline", None, "every purchased item needs a known price")
    if len({e.measure for e in resolved}) != 1:
        return Answer("decline", None, "purchase prices use different currencies")
    expected = {}
    for expense in expenses:
        expected.setdefault(expense.provenance.sentence, Counter()).update(expenditure_mentions(expense).values())
    error = audit_numeric_mentions(ctx.premises, expected,
                                   missing="a stated value lies outside the complete purchase total",
                                   duplicate="purchase evidence repeats a numeric mention")
    if error:
        return Answer("decline", None, error)
    value = resource_residual([e.value for e in resolved], [], ctx.log, source="purchase-lot-total")
    ctx.log.consumed_expenditure_keys.update(e.key() for e in expenses)
    return Answer("number", value, "sum of complete purchase costs; relative prices refer to whole purchased lots")
