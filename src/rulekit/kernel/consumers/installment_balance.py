"""Project a financed purchase after its initial payment and scheduled periods."""

from collections import Counter, defaultdict
from math import isfinite, isclose

from . import consumer
from ..answer import Answer, AnswerAssumption
from ..model import BatchEvidence, PurchaseEndpoint
from ..evaluate import evaluate
from ..numeric_evidence import audit_numeric_mentions
from ..rate_calculation import convert_duration, convert_units
from ..reference_bindings import referenced_forms_agree
from ..reference_identity import reference_from_unit
from ..resource_equations import resource_residual
from ..source_coverage import uncovered_document_units


@consumer("installment-balance")
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    quotes = list(ctx.store.by_kind(PurchaseEndpoint))
    rows = list(ctx.store.by_kind(BatchEvidence))
    rates = [r for r in rows if r.kind == "installment-rate"]
    shares = [r for r in rows if r.kind == "initial-payment-share"]
    extras = [r for r in rows if r.kind == "initial-payment-supplement"]
    if (
        len(quotes) != 1
        or len(rates) != 1
        or len(shares) != 1
        or len(extras) > 1
        or len(rows) != 2 + len(extras)
        or len(ctx.store.facts) != len(rows) + 1
        or ctx.store.collisions
        or ctx.store.quarantined
    ):
        return decline(
            "one quoted purchase and one complete installment policy are required"
        )
    quote = quotes[0]
    rate = rates[0]
    share = shares[0]
    if (
        quote.stage != "quoted"
        or quote.entity != ctx.query["entity"]
        or quote.provenance.assumption
        or rate.provenance.assumption
        or share.provenance.assumption
        or rate.container_ref != share.container_ref
        or rate.provenance.sentence != share.provenance.sentence
        or any(
            not isfinite(v) or v < 0
            for v in [quote.value, rate.value, share.value, *[r.value for r in extras]]
        )
        or share.value > 1
        or any(r.entity != quote.entity for r in extras)
    ):
        return decline(
            "price, payment policy and any additional deposit must identify the same purchase"
        )
    owner = reference_from_unit(ctx.match.slots["balance"]).owner
    if (
        owner is None
        or owner.head != quote.entity
        or not referenced_forms_agree((*ctx.premises, ctx.question), owner, ctx.reg)
    ):
        return decline("the projected balance must belong to the quoted buyer")
    elapsed = float(ctx.query["elapsed"])
    periods = convert_duration(
        elapsed,
        ctx.query["period"],
        rate.marker,
        ctx.reg,
        ctx.log,
        source="installment-periods",
    )
    if (
        periods is None
        or periods < 0
        or not isfinite(periods)
        or not isclose(periods, round(periods), abs_tol=1e-8)
    ):
        return decline("the projection needs complete, compatible payment periods")
    expected = defaultdict(Counter)
    for r in [quote, rate, share, *extras]:
        expected[r.provenance.sentence][r.value] += 1
    expected[ctx.question.sentence_index][elapsed] += 1
    if uncovered_document_units(
        ctx.premises, ctx.question, ctx.match.consumed
    ) or audit_numeric_mentions(
        (*ctx.premises, ctx.question),
        expected,
        missing="missing",
        duplicate="duplicate",
    ):
        return decline(
            "every price, payment condition and projection period must be accounted for"
        )
    initial = evaluate(
        "price * fraction",
        {"price": quote.value, "fraction": share.value},
        ctx.log,
        source="initial-payment",
    )
    payments = convert_units(
        rate.value,
        rate.measure,
        quote.measure,
        ctx.reg,
        ctx.log,
        source="installment-unit",
    )
    additional = [
        convert_units(
            r.value,
            r.measure,
            quote.measure,
            ctx.reg,
            ctx.log,
            source="additional-deposit-unit",
        )
        for r in extras
    ]
    if payments is None or any(v is None for v in additional):
        return decline("the payment currencies disagree")
    recurring = evaluate(
        "payment * periods",
        {"payment": payments, "periods": periods},
        ctx.log,
        source="scheduled-payment-total",
    )
    value = resource_residual(
        [quote.value],
        [initial, recurring, *additional],
        ctx.log,
        source="financed-purchase-balance",
    )
    if value < 0:
        return decline("the stated payments exceed the purchase balance")
    ctx.log.consumed_earnings_account_keys.add(quote.key())
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    return Answer(
        "number",
        value,
        "project the quoted balance after the percentage deposit, additional deposit and complete installment periods",
        assumptions=(AnswerAssumption("closed-finance-charges",
            "The balance includes only the stated purchase price and payments, with no unlisted interest or fees.",
            (quote.provenance.sentence, rate.provenance.sentence)),),
    )
