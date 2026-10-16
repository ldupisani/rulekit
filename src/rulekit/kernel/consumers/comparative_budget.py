"""Scale the complete cost of another participant's explicitly named purchases."""

from collections import Counter, defaultdict
from dataclasses import replace
from math import isfinite
from . import consumer
from ..answer import Answer
from ..model import Expenditure, BatchEvidence
from ..pricing import resolve_expenditure_prices, expenditure_mentions
from ..evaluate import evaluate
from ..resource_equations import resource_residual
from ..resource_accounting import purchase_collection_contains
from ..numeric_evidence import audit_numeric_mentions
from ..source_coverage import uncovered_document_units


@consumer("relative-purchase-budget")
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    expenses = list(ctx.store.by_kind(Expenditure))
    rows = list(ctx.store.by_kind(BatchEvidence))
    who, other = ctx.query["entity"], ctx.query["other"]
    factor = float(ctx.query["factor"])
    if (
        not expenses
        or ctx.store.collisions
        or ctx.store.quarantined
        or who == other
        or not isfinite(factor)
        or factor <= 0
    ):
        return decline(
            "a comparative budget needs a positive factor and another participant's purchases"
        )
    normalized = []
    for e in expenses:
        if not e.entity:
            owners = {
                p.entity
                for p in expenses
                if p.entity
                and p.provenance.sentence == e.provenance.sentence
                and p.position < e.position
            }
            if owners != {other}:
                return decline("a purchase continuation must have one preceding buyer")
            e = replace(e, entity=other)
        if (
            e.entity != other
            or e.basis != "purchase"
            or e.provenance.assumption
            or e.account
            or e.channel
            or e.supplier
        ):
            return decline("every cost must belong to the referenced buyer")
        normalized.append(e)
    requested = [ctx.query.get(k) for k in ("first", "second") if ctx.query.get(k)]
    if requested and (
        len(set(requested)) != len(requested)
        or set(requested) != {e.item for e in expenses}
    ):
        return decline("the referenced item list must identify the whole priced basket")
    collection = ctx.query.get("collection")
    if collection and not all(
        purchase_collection_contains(collection, e.item, ctx.reg) for e in expenses
    ):
        return decline("the referenced collection must contain the whole priced basket")
    contexts = [r for r in rows if r.kind == "shopping-context"]
    intents = [r for r in rows if r.kind in {"shopping-intent", "shopping-collection-intent"}]
    if (
        len(rows) != len(contexts) + len(intents)
        or len(contexts) > 1
        or len(intents) > 1
    ):
        return decline(
            "additional quantitative context is outside the budget comparison"
        )
    if rows:
        intent = intents[0] if intents else None
        context = contexts[0] if contexts else None
        participants = intent.members if intent and intent.members else (
            context.members if context else ()
        )
        if not {who, other}.issubset(participants):
            return decline("the introductory group must include both budget participants")
        if intent and intent.marker and len(set(participants)) != 2:
            return decline("the two-member group marker requires exactly two participants")
        if context and intent and (
            context.provenance.sentence >= intent.provenance.sentence
            or intent.members and set(intent.members) != set(context.members)
        ):
            return decline("the stated intention must retain the preceding group")
        if intent and (
            (not all(purchase_collection_contains(intent.measure, e.item, ctx.reg)
                     for e in expenses)
             if intent.kind == "shopping-collection-intent"
             else set((intent.measure, intent.attribute)) != {e.item for e in expenses})
            or intent.provenance.sentence >= min(e.provenance.sentence for e in expenses)
        ):
            return decline("the shopping intention must describe the actual priced items")
    resolved, error = resolve_expenditure_prices(normalized, ctx.log)
    if error:
        return decline(error)
    if (
        any(e.value is None or e.measure is None for e in resolved)
        or len({e.measure for e in resolved}) != 1
    ):
        return decline("every referenced purchase needs a price in one currency")
    expected = defaultdict(Counter)
    for e in expenses:
        expected[e.provenance.sentence].update(expenditure_mentions(e).values())
    expected[ctx.question.sentence_index][factor] += 1
    if uncovered_document_units(
        ctx.premises, ctx.question, ctx.match.consumed
    ) or audit_numeric_mentions(
        (*ctx.premises, ctx.question),
        expected,
        missing="missing",
        duplicate="duplicate",
    ):
        return decline("every purchase, ratio and contextual condition must be read")
    total = resource_residual(
        [e.value for e in resolved], [], ctx.log, source="referenced-basket-total"
    )
    value = evaluate(
        "total * factor",
        {"total": total, "factor": factor},
        ctx.log,
        source="comparative-purchase-budget",
    )
    ctx.log.consumed_expenditure_keys.update(e.key() for e in expenses)
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    return Answer(
        "number",
        value,
        "Scale the complete referenced purchase cost; a pair price is the price of the whole pair.",
    )
