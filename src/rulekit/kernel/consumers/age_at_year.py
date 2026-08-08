"""``age-at-year`` — project stated ages between absolute calendar years.

The premise grammar owns the age interpretation and the measure vocabulary.
This consumer only applies the invariant encoded by ``AgeAtYear``: for the
same entity, age changes one-for-one with elapsed calendar years.  Multiple
source coordinates must project to one answer; disagreement is a decline.
An exact discourse group is projected all-or-nothing and returned as a
labelled series unless the ask explicitly requests a sum. Deictic targets
require a caller-supplied reference year; the kernel never consults the wall
clock.
"""

from __future__ import annotations

import math

from . import ConsumerContext, consumer


def _calendar_year(raw, ctx: ConsumerContext, *, source: str) -> float | None:
    from ..evaluate import EvaluationError, evaluate

    try:
        value = evaluate(str(raw), {}, ctx.log, source=source)
    except (EvaluationError, TypeError, ValueError):
        return None
    if not math.isfinite(value) or not float(value).is_integer():
        return None
    return float(value)


def _identity(query: dict, field: str) -> str | None:
    value = query.get(field)
    if value is None:
        return None
    rendered = str(value).strip()
    return rendered or None


def _project_entity(
    ctx: ConsumerContext,
    entity: str,
    measure: str,
    target_year: float,
    *,
    owner: str | None = None,
    qualifier: str | None = None,
    label: str | None = None,
    infer_identity: bool = False,
):
    """Project one exact dated-age identity or return a decline Answer."""

    from ..answer import Answer
    from ..evaluate import evaluate
    from ..model import AgeAtYear

    candidates = [
        fact
        for fact in ctx.store.by_kind(AgeAtYear)
        if fact.entity == entity and fact.measure == measure
    ]
    if infer_identity and candidates:
        identities = {
            (fact.owner, fact.qualifier, fact.label)
            for fact in candidates
        }
        if len(identities) != 1:
            return Answer(
                "decline", None,
                f"dated {measure} age identity is ambiguous for {entity!r}",
            )
        owner, qualifier, label = next(iter(identities))
    sources = [
        fact
        for fact in candidates
        if fact.owner == owner
        and fact.qualifier == qualifier
        and fact.label == label
    ]
    if not sources:
        return Answer(
            "decline", None,
            f"no dated {measure} age known for {entity!r}",
        )

    projections: list[tuple[AgeAtYear, float]] = []
    for fact in sources:
        source_year = _calendar_year(
            fact.year, ctx, source="age-at-year-source-year"
        )
        if source_year is None or not math.isfinite(fact.value) or fact.value < 0:
            return Answer(
                "decline", None,
                f"invalid dated age source for {entity!r}",
            )
        projected = evaluate(
            f"{fact.value} + ({target_year} - {source_year})",
            {},
            ctx.log,
            source="age-at-year-projection",
        )
        if projected < 0:
            return Answer(
                "decline", None,
                f"projecting {entity!r} to {target_year:g} gives a negative age",
            )
        projections.append((fact, projected))

    values = {value for _, value in projections}
    if len(values) != 1:
        coordinates = ", ".join(
            f"{fact.value:g} in {fact.year:g} -> {value:g}"
            for fact, value in projections
        )
        return Answer(
            "decline", None,
            f"dated age sources for {entity!r} disagree at {target_year:g}: "
            f"{coordinates}",
        )

    value = projections[0][1]
    sources_text = ", ".join(
        f"{fact.value:g} in {fact.year:g}" for fact, _ in projections
    )
    return value, sources_text


@consumer("age-at-year")
def age_at_year(ctx: ConsumerContext):
    from ..answer import Answer

    entity = str(ctx.query.get("entity", "")).strip()
    measure = str(ctx.query.get("measure", "")).strip()
    holders = ctx.query.get("holders")
    aggregate = ctx.query.get("aggregate")
    target_raw = ctx.query.get("target_year")
    target_marker = str(ctx.query.get("target_marker", "")).strip()
    if not measure or (holders is None and not entity):
        return Answer(
            "decline", None,
            "a dated age ask needs an entity, measure, and target year",
        )
    if target_raw is None and target_marker:
        if ctx.reference_year is None:
            return Answer(
                "decline", None,
                "a deictic dated age ask needs an explicit reference year",
            )
        offset = ctx.reg.temporal_offsets.get(target_marker)
        if offset != 0:
            return Answer(
                "decline", None,
                f"{target_marker!r} is not a current-year age marker",
            )
        target_raw = ctx.reference_year
    if target_raw is None:
        return Answer(
            "decline", None,
            "a dated age ask needs an entity, measure, and target year",
        )
    target_year = _calendar_year(
        target_raw, ctx, source="age-at-year-target-year"
    )
    if target_year is None:
        return Answer("decline", None, f"cannot read {target_raw!r} as a calendar year")

    if holders is not None:
        if (
            not isinstance(holders, list)
            or len(holders) < 2
            or not all(isinstance(holder, str) and holder for holder in holders)
            or len(set(holders)) != len(holders)
        ):
            return Answer(
                "decline", None,
                "a dated age group ask needs at least two distinct entities",
            )
        if aggregate not in (None, "sum"):
            return Answer(
                "decline", None,
                f"unsupported dated age aggregate {aggregate!r}",
            )
        values = []
        for holder in holders:
            projection = _project_entity(
                ctx,
                holder,
                measure,
                target_year,
                infer_identity=True,
            )
            if isinstance(projection, Answer):
                return projection
            value, _sources_text = projection
            values.append(
                {"entity": holder, "measure": measure, "value": value}
            )
        if aggregate == "sum":
            total = sum(row["value"] for row in values)
            return Answer(
                "number",
                total,
                f"combined dated {measure} age for {holders} at "
                f"{target_year:g}",
            )
        return Answer(
            "series",
            values,
            f"dated {measure} ages for {holders} projected to {target_year:g}",
        )

    projection = _project_entity(
        ctx,
        entity,
        measure,
        target_year,
        owner=_identity(ctx.query, "entity_owner"),
        qualifier=_identity(ctx.query, "entity_qualifier"),
        label=_identity(ctx.query, "entity_label"),
    )
    if isinstance(projection, Answer):
        return projection
    value, sources_text = projection
    return Answer(
        "number",
        value,
        f"{entity}'s dated {measure} age ({sources_text}) projected to "
        f"{target_year:g}",
    )
