"""`rate-span-inverse` — The span implied by a rate and a total.

Shares forward-rate query scope and activity selection. A duration cannot
borrow a same-item rate for a different activity.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("rate-span-inverse", time_scoped=True)
def rate_span_inverse(ctx: ConsumerContext):
    from ..answer import Answer
    from ..model import Quantity
    from ..rate_calculation import apply_rate, convert_duration
    from ..rate_query import normalize_rate_query, matching_rates, unsupported_rate_scope
    from ..rate_query import collective_rate_subject

    # The inverse uses the same scoped rate candidates as a forward ask,
    # but divides the requested amount by the rate to recover a duration.
    ctx = normalize_rate_query(ctx)
    scope_error = unsupported_rate_scope(ctx.query)
    if scope_error:
        return Answer("decline", None, scope_error)
    entity = ctx.query["entity"]
    measure = ctx.reg.plural_to_singular.get(ctx.query["item"], ctx.query["item"])
    rates = matching_rates(ctx, measure)
    if len(rates) != 1:
        return Answer(
            "decline", None,
            f"{len(rates)} rates known for {entity!r}/{measure!r} — "
            "the inverse span ask needs exactly one",
        )
    rate = rates[0]
    collective = collective_rate_subject(ctx, rate)
    if ctx.query.get("subject_number") == "singular" and collective:
        return Answer("decline", None, "an individual ask cannot use a collective rate")
    # a per-individual rate ("a bird eats 7 berries a day") entangles a
    # population the simple division below does not attempt — decline
    # rather than risk a wrong, mirroring the forward branch's own
    # per-individual detection (holders of rate.entity as a measure).
    holders = {q.entity for q in ctx.store.by_kind(Quantity) if q.measure == rate.entity}
    if holders:
        return Answer(
            "decline", None,
            f"the rate is per-{rate.entity} — the inverse span ask does "
            "not attempt a population division",
        )
    if ctx.query.get("subject_number") == "plural" and not collective:
        return Answer("decline", None, "the plural rate subject needs a resolved population")
    if "item_value" in ctx.query:
        item_value = float(ctx.query["item_value"])
    else:
        # mining candidate duration-rate-item-asks (TOTALITY ITEM): the
        # ask named no numeral at all ("all of the windows") — the
        # asked count instead resolves from the entity's own UNIQUELY
        # stated Quantity of this measure, elsewhere in the text
        # (the increment-10/16 whole-total-decline discipline: zero or
        # ambiguous totals both decline, never a partial/guessed sum).
        # `q.owner == entity` (not just `q.entity == entity`): "David's
        # house has 64 windows" states the total on the POSSESSED noun
        # ('house'), owner-tagged 'david' (condense.py merge-possessive,
        # Quantity.owner — the SAME declared field the single-entity
        # consumer's own `entity_owner` fallback already reads), so a
        # totality stated through what the asked entity OWNS resolves
        # exactly as one stated directly on the entity would.
        totals = [
            q for q in ctx.store.by_kind(Quantity)
            if q.measure == measure and (q.entity == entity or q.owner == entity)
        ]
        if len(totals) != 1:
            return Answer(
                "decline", None,
                f"{len(totals)} {measure!r} quantities known for "
                f"{entity!r} — the totality item needs exactly one",
            )
        item_value = totals[0].value
    span = apply_rate(rate, item_value, ctx.log, source="rate-span-inverse", inverse=True)
    span_unit = rate.per
    if "span_unit" in ctx.query:
        asked_unit = ctx.reg.plural_to_singular.get(ctx.query["span_unit"], ctx.query["span_unit"])
        if asked_unit != rate.per:
            # mining candidate duration-rate-item-asks (ASKED-UNIT
            # CONVERSION): the asked time unit differs from the
            # committing rate's own per-unit — apply the SAME static
            # `reg.conversions` table the forward rate-span consumer
            # already applies above, in the REVERSE direction (the
            # computed span is stated in the rate's per-unit; convert
            # it INTO the asked unit). An absent/ambiguous conversion
            # still declines exactly as before this widening.
            if (rate.per, asked_unit) not in ctx.reg.conversions:
                return Answer(
                    "decline", None,
                    f"no conversion from the rate's {rate.per!r} to "
                    f"asked time unit {asked_unit!r} — cannot invert",
                )
            span = convert_duration(span, rate.per, asked_unit, ctx.reg, ctx.log,
                                    source="rate-span-inverse")
            span_unit = asked_unit
    return Answer(
        "number", span,
        f"{item_value} {measure} ÷ {rate.value}/{rate.per} for {entity!r}"
        + (f" -> {span_unit}" if span_unit != rate.per else ""),
    )
