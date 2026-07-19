"""`rate-span` — A total over a span at a stated rate.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("rate-span", time_scoped=True)
def rate_span(ctx: ConsumerContext):
    from ..answer import Answer
    from ..evaluate import evaluate
    from ..model import Quantity, Rate
    from ..totals import _entity_total

    # Re-landing step 4 (docs/negative-results.md): conversion spans
    # and rate x population are both live. The entity slot type is
    # the one remaining parked piece.
    entity = ctx.query["entity"]
    measure = ctx.reg.plural_to_singular.get(ctx.query["measure"], ctx.query["measure"])
    rates = [
        r for r in ctx.store.by_kind(Rate)
        if r.entity == entity
        and (
            r.measure == measure
            or (
                measure in ctx.reg.category_parents
                and ctx.reg.word_in_category(r.measure, measure)
            )
        )
    ]
    if len(rates) != 1:
        return Answer(
            "decline", None,
            f"{len(rates)} rates known for {entity!r}/{measure!r} — "
            "the span ask needs exactly one",
        )
    rate = rates[0]
    if "span_unit" in ctx.query:
        span_unit = ctx.reg.plural_to_singular.get(ctx.query["span_unit"], ctx.query["span_unit"])
        span_value = float(ctx.query["span_value"])
    else:
        # the ask named no span in the QUESTION ("how much does Rob
        # earn?") — a standalone quantity fact stated for the entity
        # in the rate's OWN per-unit ("Rob works 8 hours") stands in
        # for it, on the same unique-fact-or-decline discipline as
        # the bridge lookup below: exactly one such fact, else decline.
        spans = [
            q for q in ctx.store.by_kind(Quantity)
            if q.entity == entity and q.measure == rate.per
        ]
        if len(spans) != 1:
            return Answer(
                "decline", None,
                f"no unique {rate.per!r} span known for {entity!r} to "
                "pair with the rate",
            )
        span_unit = rate.per
        span_value = spans[0].value
    if span_unit == rate.per:
        k = span_value
    else:
        # CHAINED RATES ("30 pages an hour" x "4 hours a day" x "3
        # days"): a SECOND Rate fact for the same entity, stated in the
        # text, bridges span_unit to the first rate's per-unit — e.g.
        # Rate(entity='machine', measure='hour', per='day', value=4)
        # bridges a 'day' span to the 'hour' the first rate is per.
        # A text-stated bridge takes priority over the generic
        # reg.conversions table (a day is 24 HOURS in general, but
        # THIS machine only runs 4 of them) — checked first, and only
        # a UNIQUE bridge is trusted; anything else falls through to
        # the untouched single-rate path below, byte-for-byte.
        bridges = [
            r2 for r2 in ctx.store.by_kind(Rate)
            if r2 is not rate
            and r2.entity == entity
            and r2.measure == rate.per
            and r2.per == span_unit
        ]
        if len(bridges) == 1:
            bridge = bridges[0]
            k = evaluate(
                f"{span_value} * {bridge.value}", {}, ctx.log, source="rate-span-bridge"
            )
        elif (span_unit, rate.per) in ctx.reg.conversions:
            k = span_value * ctx.reg.conversions[(span_unit, rate.per)]
        else:
            return Answer(
                "decline", None,
                f"no conversion from {span_unit!r} to the rate's "
                f"{rate.per!r} — cannot span",
            )
    # a PER-INDIVIDUAL rate ("a bird eats 7 berries a day") multiplies
    # by the population when every holder's total resolves
    holders = sorted(
        {q.entity for q in ctx.store.by_kind(Quantity) if q.measure == rate.entity}
    )
    if holders:
        pop_totals = [
            _entity_total(ctx.store, ctx.reg, h, rate.entity, ctx.log) for h in holders
        ]
        if any(t is None for t in pop_totals):
            return Answer(
                "decline", None,
                f"the rate is per-{rate.entity} but the population "
                "does not resolve",
            )
        population = evaluate(
            " + ".join(str(t) for t in pop_totals), {}, ctx.log, source="rate-population"
        )
        total = evaluate(
            f"{rate.value} * {population} * {k}", {}, ctx.log, source="rate-span"
        )
        return Answer(
            "number", total,
            f"{rate.value}/{rate.per} × {population} {rate.entity} × "
            f"{k} {rate.per}",
        )
    if rate.numerator is not None and rate.denominator is not None:
        # a COMPOUND rate ("8 pages in 20 minutes") — multiply through
        # the raw stated numerator/denominator directly so value-
        # accounting (guards.py) credits the text's own two numbers as
        # read; using the derived `value` quotient here would leave
        # them unaccounted (see Rate's docstring).
        total = evaluate(
            f"{rate.numerator} * {k} / {rate.denominator}", {}, ctx.log,
            source="rate-span",
        )
    else:
        total = evaluate(f"{rate.value} * {k}", {}, ctx.log, source="rate-span")
    return Answer(
        "number", total,
        f"{rate.value}/{rate.per} × {k} {rate.per} for {entity!r}",
    )
