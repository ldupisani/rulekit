"""Quote a complete activity's actual item counts across named participants."""

from collections import Counter, defaultdict
from . import consumer
from ..answer import Answer
from ..evaluate import evaluate
from ..model import BatchEvidence, Expenditure, Price, Quantity
from ..numeric_evidence import audit_numeric_mentions
from ..pricing import resolve_expenditure_prices, resolve_unit_quotes
from ..monetary import canonical_currency
from ..source_coverage import quantity_ledger_source_units, uncovered_units


@consumer(
    "named-activity-cost",
    applicable=lambda s: any(
        r.kind == "named-cost-account" for r in s.by_kind(BatchEvidence)
    ),
)
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    quantities = list(ctx.store.by_kind(Quantity))
    prices = list(ctx.store.by_kind(Price))
    if (
        len(rows) != 1
        or rows[0].kind != "named-cost-account"
        or rows[0].measure != ctx.query["activity"]
        or not quantities
        or not prices
        or len(ctx.store.facts) != len(rows) + len(quantities) + len(prices)
        or ctx.store.collisions
        or ctx.store.quarantined
    ):
        return decline(
            "one complete named activity account and its explicit prices are required"
        )
    group = rows[0]
    if {q.entity for q in quantities} != set(group.members):
        return decline("every named participant needs explicit item counts")
    expected = defaultdict(Counter)
    covered = defaultdict(set)
    expenses = []
    for reading in ctx.premises:
        local = [
            q for q in quantities if q.provenance.sentence == reading.sentence_index
        ]
        if local:
            footprint = quantity_ledger_source_units(reading, local, ctx.reg)
            if not footprint:
                return decline("every participant item count must be fully read")
            covered[reading.sentence_index].update(footprint)
    used = set()
    for q in quantities:
        if (
            q.entity not in group.members
            or q.provenance.assumption
            or q.time
            or q.owner
            or q.label
            or q.qualifier
            or q.provenance.sentence <= group.provenance.sentence
            or not ctx.reg.word_in_category(q.verb, "possession_state")
            or q.value < 0
            or not float(q.value).is_integer()
        ):
            return decline(
                "all actual item counts must belong to the stated participants"
            )
        item = q.content_ref.head if q.content_ref else q.measure
        per = q.measure
        qualifier = (
            q.content_ref.qualifiers[0]
            if q.content_ref and q.content_ref.qualifiers
            else q.measure_qualifier if not q.content_ref else None
        )
        matches = [
            p
            for p in prices
            if p.item == item
            and (p.per or p.item) == per
            and (p.qualifier or None) == qualifier
        ]
        p = resolve_unit_quotes(matches, ctx.reg, ctx.log, per=per)
        if p is None:
            return decline(
                "each item and serving unit needs one matching currency price"
            )
        used.update(price.key() for price in matches)
        expenses.append(
            Expenditure(
                provenance=q.provenance,
                entity=q.entity,
                item=item,
                measure=p.measure or canonical_currency(ctx.reg),
                value=None,
                quantity=q.value,
                unit_price=p.value,
                basis="quote",
                position=q.provenance.sentence,
                verb=q.verb,
            )
        )
        expected[q.provenance.sentence][q.value] += 1
    if (
        len(used) != len(prices)
        or len({p.measure or canonical_currency(ctx.reg) for p in prices}) != 1
    ):
        return decline("all stated prices must be used, in one explicit currency")
    for p in prices:
        expected[p.provenance.sentence][p.value] += 1
    if (
        any(uncovered_units(r, covered[r.sentence_index]) for r in ctx.premises)
        or uncovered_units(ctx.question, ctx.match.consumed)
        or audit_numeric_mentions(
            (*ctx.premises, ctx.question),
            expected,
            missing="missing",
            duplicate="duplicate",
        )
    ):
        return decline(
            "all costs, quantities and activity conditions must be accounted for"
        )
    resolved, error = resolve_expenditure_prices(expenses, ctx.log)
    if error:
        return decline(error)
    value = evaluate(
        " + ".join(str(e.value) for e in resolved),
        {},
        ctx.log,
        source="named-activity-item-cost",
    )
    ctx.log.consumed_batch_keys.add(group.key())
    ctx.log.consumed_currency_price_keys.update(p.key() for p in prices)
    ctx.log.consumed_quoted_price_keys.update(p.key() for p in prices)
    return Answer(
        "number",
        value,
        "sum each participant’s counted items at the matching unit or serving price",
    )
