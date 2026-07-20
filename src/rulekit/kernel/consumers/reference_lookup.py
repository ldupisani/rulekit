"""`reference-lookup` — a curated real-world fact from the frozen registry.

The difg reference-seed capability, re-homed on rulekit's ask->consumer
dispatch: the ask shapes (packs/reference/rules/lookup.yaml) bind the
attribute WORD, the entity NAME and optionally a stated year; this consumer
takes them to `reg.reference`, a mapping compiled from `rulekit/reference@1`
pack tables. No entity, attribute or value is named here (constitution rule
1) — every miss is a decline, never an approximation:

- unknown entity            -> no key, decline
- attribute without data    -> no key, decline (the category gate already
                               blocks attributes no table declares)
- by-year attribute, no year-> no year-less key EXISTS for a time series
                               (registry compile stores one key per year), so
                               the lookup declines rather than silently
                               choosing a year for "the population of France"
- year outside the series   -> no key, decline — no difg-style trend
                               projection; an estimate is not a fact
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("reference-lookup")
def reference_lookup(ctx: ConsumerContext):
    from ..answer import Answer

    attribute = ctx.query.get("attribute", "")
    entity = str(ctx.query.get("entity", "")).strip().lower()
    if not attribute or not entity:
        return Answer("decline", None, "a reference lookup needs an attribute and an entity")
    year: int | None = None
    raw_year = ctx.query.get("year")
    if raw_year is not None:
        try:
            year = int(float(raw_year))
        except (TypeError, ValueError):
            return Answer("decline", None, f"cannot read {raw_year!r} as a year")
    value = ctx.reg.reference.get((entity, attribute, year))
    if value is None:
        when = f" in {year}" if year is not None else ""
        return Answer(
            "decline", None,
            f"no reference fact for the {attribute!r} of {entity!r}{when}",
        )
    when = f" in {year}" if year is not None else ""
    return Answer(
        "number", float(value),
        f"reference: {attribute} of {entity}{when} = {value:g}",
    )
