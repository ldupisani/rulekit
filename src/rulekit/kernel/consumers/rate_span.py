"""`rate-span` — A total over a span at a stated rate.

Originally extracted unchanged from `answer.py`. Subsequent scope handling
preserves individual/group evidence and delegates explicit dependency chains
to their audited consumer rather than defaulting an unknown group to one.

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
    from ..model import ActivityDuration, Quantity, Rate, RateScope
    from ..totals import _entity_total
    from ..rate_calculation import activity_scope_matches, apply_rate, convert_duration
    from ..rate_query import normalize_rate_query, matching_rates, unsupported_rate_scope
    from ..rate_query import collective_rate_subject

    # Structural evidence supplements the stable semantic query contract.
    # Existing reviewed asks can replay unchanged while number and ownership
    # are enforced from their freshly parsed surface on every execution.
    ctx = normalize_rate_query(ctx)

    # Re-landing step 4 (docs/negative-results.md): conversion spans
    # and rate x population are both live. The entity slot type is
    # the one remaining parked piece.
    entity = ctx.query["entity"]
    measure = ctx.reg.plural_to_singular.get(ctx.query["measure"], ctx.query["measure"])
    # Plural class asks must not silently fall back to one member's quota.
    all_rates = ctx.store.by_kind(Rate)
    if (any(r.provenance.distributive for r in all_rates)
            and (len(all_rates) > 1 or len(ctx.store.by_kind(Quantity)) <= 1)):
        from .per_member_rate_chain import per_member_rate_chain
        return per_member_rate_chain(ctx)
    scope_error = unsupported_rate_scope(ctx.query, allow_population_owner=True)
    if scope_error:
        return Answer("decline", None, scope_error)
    rates = matching_rates(ctx, measure)
    if len(rates) != 1:
        return Answer(
            "decline", None,
            f"{len(rates)} rates known for {entity!r}/{measure!r} — "
            "the span ask needs exactly one",
        )
    rate = rates[0]
    collective = collective_rate_subject(ctx, rate)
    if ctx.query.get("subject_number") == "singular" and collective:
        return Answer("decline", None, "an individual ask cannot use a collective rate")
    from ..repeated_rates import repeated_rate_total
    repeated = repeated_rate_total(ctx, rate)
    if repeated is not None:
        return repeated
    if "span_unit" in ctx.query:
        span_unit = ctx.reg.plural_to_singular.get(ctx.query["span_unit"], ctx.query["span_unit"])
        span_value = float(ctx.query["span_value"])
    else:
        # A rate explicitly scoped to an activity may ONLY use elapsed time
        # for that same participant and activity.  Do not fall back to an
        # unqualified Quantity: doing so would let gardening time satisfy a
        # tutoring rate (or any other unrelated duration).
        scopes = [
            scope for scope in ctx.store.by_kind(RateScope)
            if scope.participant == entity and scope.verb == rate.verb
        ]
        if scopes:
            if len(scopes) != 1:
                return Answer(
                    "decline", None,
                    f"{len(scopes)} activity scopes known for {entity!r}/"
                    f"{rate.verb!r} — the span ask needs exactly one",
                )
            scope = scopes[0]
            durations = [
                duration for duration in ctx.store.by_kind(ActivityDuration)
                if activity_scope_matches(scope, rate, duration.participant, duration.activity)
            ]
            if len(durations) != 1:
                return Answer(
                    "decline", None,
                    f"no unique duration for {entity!r} doing "
                    f"{scope.activity!r} to pair with the rate",
                )
            span_unit = ctx.reg.plural_to_singular.get(
                durations[0].unit, durations[0].unit
            )
            span_value = durations[0].elapsed
        else:
            # The ask named no span in the QUESTION ("how much does Rob
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
            k = apply_rate(bridge, span_value, ctx.log, source="rate-span-bridge")
        elif (span_unit, rate.per) in ctx.reg.conversions:
            k = convert_duration(span_value, span_unit, rate.per, ctx.reg, ctx.log,
                                 source="rate-span-unit", record=False)
        elif (span_unit, rate.per) in ctx.reg.cadence_conversions:
            k = convert_duration(span_value, span_unit, rate.per, ctx.reg, ctx.log,
                                 source="rate-span-cadence", allow_cadence=True, record=False)
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
    if ctx.query.get("entity_owner"):
        holders = [holder for holder in holders if holder == ctx.query["entity_owner"]]
    if ctx.query.get("entity_owner") and (
        not holders or ctx.query.get("subject_number") == "singular"
    ):
        return Answer("decline", None, "the owned rate subject needs matching scoped evidence")
    if holders and ctx.query.get("subject_number") != "singular":
        if collective:
            return Answer("decline", None, "a collective rate cannot be multiplied by a population")
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
        member_periods = evaluate(
            f"{population} * {k}", {}, ctx.log, source="rate-population-span"
        )
        total = apply_rate(rate, member_periods, ctx.log, source="rate-span")
        return Answer(
            "number", total,
            f"{rate.value}/{rate.per} × {population} {rate.entity} × "
            f"{k} {rate.per}",
        )
    if ctx.query.get("subject_number") == "plural" and not collective:
        return Answer("decline", None, "the plural rate subject needs a resolved population")
    total = apply_rate(rate, k, ctx.log, source="rate-span")
    return Answer(
        "number", total,
        f"{rate.value}/{rate.per} × {k} {rate.per} for {entity!r}",
    )
