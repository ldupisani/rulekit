"""Recover one paid-work count from a bounded, completely read savings story.

Prices, income cadences, service objects and purchase completion arrive as
typed facts. This consumer does not parse text or invent a cash holding.
"""

from collections import Counter
from dataclasses import replace
from math import isclose, isfinite

from ..answer import Answer, AnswerProof, ProofStep, SemanticNode
from ..evaluate import evaluate
from ..model import (AccumulationWindow, EarningRate, ServiceScope, PurchaseEndpoint,
                     EARNINGS_ACCOUNT_KINDS, Quantity)
from ..source_coverage import uncovered_document_units
from ..numeric_evidence import audit_numeric_mentions
from ..rate_calculation import apply_rate, convert_duration
from ..resource_equations import resource_residual


def earnings_account(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    windows = ctx.store.by_kind(AccumulationWindow)
    endpoints = ctx.store.by_kind(PurchaseEndpoint)
    quotes = [e for e in endpoints if e.stage == "quoted"]
    completed = [e for e in endpoints if e.stage == "completed"]
    rates = ctx.store.by_kind(EarningRate)
    scopes = ctx.store.by_kind(ServiceScope)
    quantities = ctx.store.by_kind(Quantity)
    if (len(windows) != 1 or len(quotes) != 1 or len(completed) != 1
            or len(endpoints) != 2 or not rates or ctx.store.quarantined):
        return decline("earnings need one saving interval and one uniquely priced, completed purchase")
    window, quote, closing = windows[0], quotes[0], completed[0]
    entity, measure, verb = (ctx.query.get(k) for k in ("entity", "measure", "verb"))
    if any(ctx.query.get(k) for k in ("entity_owner", "entity_qualifier", "measure_qualifier")):
        return decline("a qualified work ask needs equally scoped service evidence")
    facts = [*windows, *endpoints, *rates, *scopes, *quantities]
    if any(f.entity != entity for f in facts) or (window.owner and window.owner != entity):
        return decline("all saving, work and purchase evidence must have the same participant")
    if (quote.item != closing.item or (closing.qualifier and closing.qualifier != quote.qualifier)
            or (closing.unit and closing.unit != quote.unit)
            or quote.provenance.sentence >= closing.provenance.sentence
            or window.provenance.sentence >= closing.provenance.sentence):
        return decline("the completed purchase must identify the quoted target after the saving interval")
    if any(f.measure != quote.measure for f in [closing, *rates]):
        return decline("income quotes and purchase endpoints need one currency")
    if any(e.owner and e.owner != entity for e in endpoints):
        return decline("a purchase target belongs to a different participant")
    if not ctx.reg.word_in_category(window.measure, "currency"):
        return decline("the saving interval must describe the income resource")
    if any(f.provenance.assumption for f in [*windows, *endpoints, *rates, *scopes]):
        return decline("the saving interval, tariffs and purchase must be asserted")
    if any(f.provenance.sentence >= closing.provenance.sentence for f in [*rates, *scopes]):
        return decline("income sources must belong to the saving interval before settlement")
    periodic = [r for r in rates if r.basis == "periodic"]
    if len({r.source for r in periodic}) != len(periodic):
        return decline("a periodic income source has competing or repeated quotes")
    if any(not isinstance(f, (*EARNINGS_ACCOUNT_KINDS, Quantity)) for f in ctx.store.facts):
        return decline("additional facts leave the savings account incomplete")
    # Full source coverage rejects unpriced changes and qualifiers even when
    # they introduce no number. Conditional work counts are explicitly local
    # to this question; quoted prices and endpoint facts cannot be conditional.
    if uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed):
        return decline("the earnings account has an unread event, condition or qualifier")
    if any(not isfinite(f.value) or f.value < 0 for f in [*endpoints, *rates, *quantities]):
        return decline("earnings operands must be finite and nonnegative")
    if any(r.numerator is not None or r.denominator is not None for r in rates):
        return decline("a compound income quote needs complete source operands")
    if not isfinite(window.elapsed) or window.elapsed <= 0:
        return decline("the saving interval needs a positive finite duration")
    if any(not float(q.value).is_integer() for q in quantities):
        return decline("completed service objects need whole counts")
    expected = {window.provenance.sentence: Counter([window.elapsed])}
    for fact in [*endpoints, *rates, *quantities]:
        expected.setdefault(fact.provenance.sentence, Counter()).update([fact.value])
    if audit_numeric_mentions((*ctx.premises, ctx.question), expected,
                              missing="missing", duplicate="duplicate"):
        return decline("every source-local amount must belong to the earnings equation")

    known_income = []
    services = []
    for rate in rates:
        if rate.basis == "periodic":
            if rate.per != window.cadence:
                return decline("periodic income must match the stated saving cadence")
            periods = convert_duration(window.elapsed, window.unit, rate.per, ctx.reg, ctx.log,
                                       source="income-periods")
            if periods is None or not isfinite(periods) or not float(periods).is_integer():
                return decline("income needs complete, exactly convertible saving periods")
            known_income.append(apply_rate(rate, periods, ctx.log, source="periodic-income"))
        elif rate.basis == "service":
            candidates = {s.item for s in scopes if s.verb == rate.verb
                          and (not rate.per or s.item == rate.per)}
            if not rate.per:
                if len(candidates) != 1:
                    return decline("an omitted tariff object needs one matching declared service")
                rate = replace(rate, per=next(iter(candidates)))
            services.append(rate)
        else:
            return decline("the income basis is unsupported")
    if len({(r.verb, r.per) for r in services}) != len(services):
        return decline("a service has competing or repeated price quotes")
    if any(not any((s.verb, s.item) == (r.verb, r.per) for r in services) for s in scopes):
        return decline("every declared service needs a compatible price")
    unknown = []
    used_counts = []
    for rate in services:
        counts = [q for q in quantities if (q.verb, q.measure) == (rate.verb, rate.per)
                  and not q.qualifier and not q.measure_qualifier and not q.owner]
        if counts:
            total = evaluate(" + ".join(str(q.value) for q in counts), {}, ctx.log,
                             source="service-count-total")
            known_income.append(apply_rate(rate, total, ctx.log, source="service-income"))
            used_counts.extend(counts)
        else:
            unknown.append(rate)
    if len(used_counts) != len(quantities) or len(unknown) != 1:
        return decline("the closed account must leave exactly one unknown service count")
    target = unknown[0]
    if (target.verb, target.per) != (verb, measure) or target.value <= 0:
        return decline("the asked work must be the uniquely priced unknown service")
    if any(not isfinite(value) for value in known_income):
        return decline("the income calculation exceeds finite arithmetic")
    residual = resource_residual([quote.value, closing.value], known_income, ctx.log,
                                 source="unassigned-earnings")
    if not isfinite(residual):
        return decline("the balance exceeds finite arithmetic")
    count = apply_rate(target, residual, ctx.log, source="inverse-service-rate", inverse=True)
    if not isfinite(count) or count < 0 or not isclose(count, round(count), abs_tol=1e-8, rel_tol=0):
        return decline("the balance implies a negative or fractional service-object count")
    ctx.log.consumed_earnings_account_keys.update(f.key() for f in facts if not isinstance(f, Quantity))
    interpretation = "the stated income is all the money saved, with no initial savings or other income or spending"
    node = SemanticNode("service-count", (("entity", entity), ("verb", verb), ("measure", measure)))
    proof = AnswerProof(node, (
        ProofStep("closed-savings-interpretation", node, tuple(facts), interpretation),
        ProofStep("residual-income-inverse-rate", SemanticNode("count", (("value", count),)),
                  (target, quote, closing), "purchase cost + cash remaining − known income, divided by service price"),
    ))
    return Answer("number", float(round(count)),
                  f"{count:g} {measure}; interpreting that {interpretation}.", proof=proof)
