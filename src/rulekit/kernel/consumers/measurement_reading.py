"""Final reading of an instrument observing one ordered content stream."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
import math

from . import ConsumerContext, consumer


_ACTIVE_CONTAINER = "$active:measured-container$"


def _dimension_families(word: str | None, ctx: ConsumerContext) -> set[str]:
    """Return the declared dimension families for a noun or unit."""

    if not word:
        return set()
    singular = ctx.reg.plural_to_singular.get(word, word)
    families = {
        category
        for category in ctx.reg.word_categories.get(singular, ())
        if category in ctx.reg.dimension_categories
    }
    if singular in ctx.reg.dimension_categories:
        families.add(singular)
    return families


def _substance_conversion_factor(
    ctx: ConsumerContext,
    substance: str,
    source: str,
    target: str,
) -> float | None:
    """DELEGATED to the shared dimensional algebra
    (`dimensions.substance_conversion_factor`) — the substance-bridge
    contract (one bridge composition per row, at most one direct ordinary
    edge on either side, disagreement -> None) is owned in ONE place now.
    This module keeps the ctx-shaped wrapper its call site uses."""
    from ..dimensions import substance_conversion_factor

    return substance_conversion_factor(ctx.reg, substance, source, target)


@consumer("measurement-reading")
def measurement_reading(ctx: ConsumerContext):
    """Apply all changes to one container whose support is the instrument.

    The consumer derives a reading; it never stores the total as an intrinsic
    property of the instrument.  An elided update is attached only when
    exactly one prior ``set_total`` stream exists at that point in the story.
    """

    from ..answer import _ACCOUNTED_VALUE_KINDS, Answer
    from ..evaluate import evaluate
    from ..model import MeasuredContentChange, SpatialPlacement

    instrument = str(ctx.query.get("instrument", "")).strip()
    container = str(ctx.query.get("container", "")).strip()
    dimension = str(ctx.query.get("dimension", "")).strip()
    relation = str(ctx.query.get("relation", "")).strip()
    if not dimension or not (container or (instrument and relation)):
        return Answer(
            "decline",
            None,
            "a measurement reading needs a dimension and a container or instrument placement",
        )

    asked_families = _dimension_families(dimension, ctx)
    if not asked_families:
        return Answer(
            "decline",
            None,
            f"the asked dimension {dimension!r} names no declared measurement dimension",
        )

    changes = list(ctx.store.by_kind(MeasuredContentChange))
    captured_by_sentence: dict[int, Counter[float]] = {}
    for change in changes:
        captured_by_sentence.setdefault(
            change.provenance.sentence, Counter()
        )[float(change.value)] += 1
    for sentence, value in ctx.query.get("_additional_measured_values", ()):
        captured_by_sentence.setdefault(int(sentence), Counter())[float(value)] += 1
    for reading in ctx.premises:
        captured = captured_by_sentence.get(reading.sentence_index, Counter())
        for unit in reading.units:
            if unit.features.get("value_kind") not in _ACCOUNTED_VALUE_KINDS:
                continue
            value = float(unit.features["value"])
            if captured.get(value, 0) <= 0:
                return Answer(
                    "decline",
                    None,
                    f"stated value {unit.surface!r} is outside the measured-content stream",
                )
            captured[value] -= 1
    anchors = [change for change in changes if change.operation == "set_total"]
    placements = list(ctx.store.by_kind(SpatialPlacement))

    candidates: list[tuple[SpatialPlacement, MeasuredContentChange, set[str]]] = []
    for anchor in anchors:
        anchor_families = (
            _dimension_families(anchor.dimension, ctx)
            & _dimension_families(anchor.measure, ctx)
            & asked_families
        )
        if not anchor_families or anchor.occurrence is None:
            continue
        for placement in placements:
            if (
                placement.entity == anchor.container
                and (not container or placement.entity == container)
                and (not instrument or placement.reference == instrument)
                and (not relation or placement.relation == relation)
                and placement.occurrence is not None
                and placement.occurrence <= anchor.occurrence
            ):
                candidates.append((placement, anchor, anchor_families))

    if len(candidates) != 1:
        return Answer(
            "decline",
            None,
            "the reading needs one matching placement and compatible total anchor; "
            f"found {len(candidates)}",
        )

    placement, anchor, families = candidates[0]
    assert anchor.measure is not None  # proved by the family intersection

    # Resolve every implicit update at its own narration coordinate.  A later
    # stream cannot make an earlier reference ambiguous, while two streams
    # already in play must never be guessed between.
    assigned: dict[MeasuredContentChange, str] = {}
    for change in changes:
        if change.container != _ACTIVE_CONTAINER:
            assigned[change] = change.container
            continue
        if change.occurrence is None:
            return Answer("decline", None, "a measured update has no narration order")
        prior = [
            candidate
            for candidate in anchors
            if candidate.occurrence is not None
            and candidate.occurrence < change.occurrence
        ]
        prior_containers = {candidate.container for candidate in prior}
        if len(prior) != 1 or len(prior_containers) != 1:
            return Answer(
                "decline",
                None,
                "an elided measured-content update does not have one unique prior stream",
            )
        assigned[change] = next(iter(prior_containers))

    stream = [
        change
        for change in changes
        if assigned.get(change) == anchor.container
        and change.occurrence is not None
        and change.occurrence >= anchor.occurrence
    ]
    if len(stream) != len(changes):
        return Answer(
            "decline",
            None,
            "the document contains measured changes outside the selected stream",
        )

    later = [change for change in stream if change is not anchor]
    if any(change.occurrence <= anchor.occurrence for change in later):
        return Answer(
            "decline", None, "two aggregate measurement effects have no strict order"
        )

    if not math.isfinite(anchor.value) or anchor.value < 0:
        return Answer("decline", None, "the aggregate measurement anchor is invalid")
    total = evaluate(
        str(float(anchor.value)), {}, ctx.log, source="measurement-reading-anchor"
    )

    steps = [f"{total:g} {anchor.measure}"]
    for change in sorted(later, key=lambda item: item.occurrence or -1):
        if not math.isfinite(change.value) or change.value < 0:
            return Answer("decline", None, "a measured-content update is invalid")
        if change.operation == "multiply_total":
            if not (_dimension_families(change.dimension, ctx) & families):
                return Answer(
                    "decline",
                    None,
                    f"the scaled dimension {change.dimension!r} is incompatible with "
                    f"the anchored {anchor.dimension!r}",
                )
            if change.value <= 0:
                return Answer("decline", None, "a total multiplier must be positive")
            # This measurement stream scales the aggregate through additions.
            if change.value < 1:
                return Answer("decline", None, "a measured addition leaves no positive content amount")
            total = evaluate(
                f"{total} * {change.value}",
                {},
                ctx.log,
                source="measurement-reading-multiply",
            )
            steps.append(f"× {change.value:g}")
            continue
        if change.operation == "add_quantity":
            if not (_dimension_families(change.measure, ctx) & families):
                return Answer(
                    "decline",
                    None,
                    f"the added measure {change.measure!r} is incompatible with "
                    f"the anchored {anchor.measure!r}",
                )
            assert change.measure is not None
            factor = (
                1.0
                if change.measure == anchor.measure
                else ctx.reg.conversions.get((change.measure, anchor.measure))
            )
            if factor is None:
                return Answer(
                    "decline",
                    None,
                    f"no known conversion from {change.measure!r} to {anchor.measure!r}",
                )
            added = evaluate(
                f"{change.value} * {factor}",
                {},
                ctx.log,
                source="measurement-reading-convert-addition",
            )
            total = evaluate(
                f"{total} + {added}",
                {},
                ctx.log,
                source="measurement-reading-addition",
            )
            steps.append(f"+ {added:g} {anchor.measure}")
            continue
        return Answer(
            "decline", None, f"unsupported aggregate operation {change.operation!r}"
        )

    target_measure = str(ctx.query.get("target_measure", "")).strip()
    if target_measure:
        if not (_dimension_families(target_measure, ctx) & families):
            return Answer(
                "decline", None, "the requested unit has an incompatible dimension"
            )
        factor = (
            1.0 if target_measure == anchor.measure
            else ctx.reg.conversions.get((anchor.measure, target_measure))
        )
        if factor is None:
            return Answer(
                "decline", None,
                f"no known conversion from {anchor.measure!r} to {target_measure!r}",
            )
        total = evaluate(
            f"{total} * {factor}", {}, ctx.log,
            source="measurement-reading-requested-unit",
        )
        steps.append(f"= {total:g} {target_measure}")

    return Answer(
        "number",
        float(total),
        f"{anchor.container!r} {placement.relation!r} {placement.reference!r}: "
        + " ".join(steps),
    )


@consumer("measurement-content-amount")
def measurement_content_amount(ctx: ConsumerContext):
    """Recover one content's contribution to a measured container.

    A resulting-total anchor states the container-plus-content mass.  The
    anchor content needs a declared container tare. Later content is recovered
    from the change it caused in the validated aggregate stream: a multiplier
    contributes the before/after difference and a direct addition contributes
    its converted stated amount. Repeated additions of the requested content
    accumulate; unrelated later additions never alter its recovered amount.
    """

    from ..answer import Answer
    from ..evaluate import evaluate
    from ..model import MeasuredContentChange, Quantity, SpatialPlacement

    content = str(ctx.query.get("content", "")).strip()
    container = str(ctx.query.get("container", "")).strip()
    if not content or not container:
        return Answer(
            "decline", None, "a content amount needs one content and container"
        )

    changes = list(ctx.store.by_kind(MeasuredContentChange))
    anchors = [
        change
        for change in changes
        if change.operation == "set_total"
        and change.container == container
    ]
    if len(anchors) != 1:
        return Answer(
            "decline",
            None,
            "the requested container needs one resulting-total anchor",
        )
    anchor = anchors[0]

    placements = [
        placement
        for placement in ctx.store.by_kind(SpatialPlacement)
        if placement.entity == container
        and placement.occurrence is not None
        and anchor.occurrence is not None
        and placement.occurrence <= anchor.occurrence
    ]
    if len(placements) != 1:
        return Answer(
            "decline",
            None,
            "the content anchor needs one prior container/instrument placement",
        )
    placement = placements[0]

    anchor_families = _dimension_families(anchor.measure, ctx)
    tares = [
        quantity
        for quantity in ctx.store.by_kind(Quantity)
        if quantity.entity == container
        and ctx.reg.word_in_category(quantity.verb, "measurement_mass_verb")
        and (_dimension_families(quantity.measure, ctx) & anchor_families)
    ]
    if len(tares) > 1 or (content == anchor.content and len(tares) != 1):
        return Answer(
            "decline",
            None,
            "the requested content needs one compatible intrinsic container mass",
        )

    # Reuse the final-reading consumer to validate and account for every later
    # aggregate update. A tare, when stated, is an additional independent
    # value, so admit exactly that mention into the premise audit. Later
    # content remains answerable without a tare because its contribution is an
    # observed change in the aggregate rather than a share of the anchor.
    validated = measurement_reading(
        replace(
            ctx,
            query={
                "instrument": placement.reference,
                "dimension": anchor.dimension or "",
                "relation": placement.relation,
                "_additional_measured_values": tuple(
                    (tare.provenance.sentence, tare.value) for tare in tares
                ),
            },
        )
    )
    if not validated.committed:
        return validated

    assert anchor.measure is not None
    amount = 0.0
    derivations: list[str] = []
    found = False

    if content == anchor.content:
        tare = tares[0]  # required by the cardinality guard above
        factor = (
            1.0
            if tare.measure == anchor.measure
            else ctx.reg.conversions.get((tare.measure, anchor.measure))
        )
        if factor is None:
            return Answer(
                "decline",
                None,
                f"no known conversion from {tare.measure!r} to {anchor.measure!r}",
            )
        tare_value = evaluate(
            f"{tare.value} * {factor}",
            {},
            ctx.log,
            source="measurement-content-tare-conversion",
        )
        amount = evaluate(
            f"{anchor.value} - {tare_value}",
            {},
            ctx.log,
            source="measurement-content-tare-subtraction",
        )
        if not math.isfinite(amount) or amount <= 0:
            return Answer(
                "decline", None, "the container tare leaves no positive content amount"
            )
        derivations.append(
            f"{anchor.value:g} {anchor.measure} − {tare_value:g} {anchor.measure}"
        )
        found = True

    total = float(anchor.value)
    later = sorted(
        (
            change
            for change in changes
            if change is not anchor
            and change.occurrence is not None
            and anchor.occurrence is not None
            and change.occurrence > anchor.occurrence
        ),
        key=lambda change: change.occurrence or -1,
    )
    for change in later:
        before = total
        if change.operation == "multiply_total":
            total = evaluate(
                f"{before} * {change.value}",
                {},
                ctx.log,
                source="measurement-content-replay-multiply",
            )
            contribution = evaluate(
                f"{total} - {before}",
                {},
                ctx.log,
                source="measurement-content-multiplier-contribution",
            )
            derivation = (
                f"{total:g} {anchor.measure} − {before:g} {anchor.measure}"
            )
        elif change.operation == "add_quantity":
            assert change.measure is not None  # validated by measurement_reading
            factor = (
                1.0
                if change.measure == anchor.measure
                else ctx.reg.conversions[(change.measure, anchor.measure)]
            )
            contribution = evaluate(
                f"{change.value} * {factor}",
                {},
                ctx.log,
                source="measurement-content-direct-contribution",
            )
            total = evaluate(
                f"{before} + {contribution}",
                {},
                ctx.log,
                source="measurement-content-replay-addition",
            )
            derivation = f"+ {contribution:g} {anchor.measure}"
        else:
            # The validating consumer rejects this branch first. Keeping the
            # replay exhaustive makes that dependency explicit to type checkers.
            continue

        if change.content != content:
            continue
        if not math.isfinite(contribution) or contribution <= 0:
            return Answer(
                "decline", None, "a measured addition leaves no positive content amount"
            )
        amount = evaluate(
            f"{amount} + {contribution}",
            {},
            ctx.log,
            source="measurement-content-accumulation",
        )
        derivations.append(derivation)
        found = True

    if not found:
        return Answer(
            "decline", None, "the requested content has no recoverable measured addition"
        )

    target_measure = str(ctx.query.get("target_measure", "")).strip()
    conversion_note = ""
    if target_measure:
        factor = _substance_conversion_factor(
            ctx, content, anchor.measure, target_measure
        )
        if factor is None:
            return Answer(
                "decline",
                None,
                f"no known {content!r} conversion from {anchor.measure!r} "
                f"to {target_measure!r}",
            )
        source_amount = amount
        amount = evaluate(
            f"{amount} * {factor}",
            {},
            ctx.log,
            source="measurement-content-substance-conversion",
        )
        conversion_note = (
            f"; {source_amount:g} {anchor.measure} → "
            f"{amount:g} {target_measure}"
        )

    return Answer(
        "number",
        float(amount),
        f"{content!r} in {container!r}: "
        + " + ".join(derivations)
        + conversion_note,
    )
