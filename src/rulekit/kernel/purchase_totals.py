"""Complete actual purchase totals with exact relative lot-price evidence."""

from collections import Counter

from .model import Expenditure, ResourceAccountingIssue
from .pricing import expenditure_mentions, resolve_expenditure_prices


def has_relative_purchase_prices(store):
    return any(e.cost_reference for e in store.by_kind(Expenditure))


def relative_purchase_total(ctx, *, collection=None):
    from .answer import Answer
    from .learn import _lemma
    from .numeric_evidence import audit_numeric_mentions
    from .resource_equations import resource_residual

    expenses = list(ctx.store.by_kind(Expenditure))
    if (not expenses or any(e.entity != ctx.query["entity"] or e.provenance.assumption
                            or e.basis != "purchase" for e in expenses)):
        return Answer("decline", None, "the purchase total needs one participant's actual purchases")
    if collection and (not ctx.reg.word_in_category(collection, "purchase_collection_noun")
                       or ctx.query.get("qualifier")
                       or any(not ctx.reg.word_in_category(e.item, collection) for e in expenses)):
        return Answer("decline", None, "the named collection does not contain the complete purchase basket")
    # A bare total or one declared collective noun can cover this basket.
    # Other item, time, supplier and account restrictions cannot be discarded.
    tail = [u for u in ctx.question.units if u.uid not in ctx.match.consumed
            and u.sense() not in {"article", "punct"}]
    if tail:
        if (len(tail) != 2 or not ctx.reg.word_in_category(_lemma(tail[0]), "spend_target_prep")
                or not ctx.reg.word_in_category(_lemma(tail[1]), "purchase_collection_noun")
                or tail[1].features.get("qualifier") or tail[1].features.get("owner")
                or any(not ctx.reg.word_in_category(e.item, _lemma(tail[1])) for e in expenses)):
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
