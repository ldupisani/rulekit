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
    dimension = str(ctx.query.get("dimension", "")).strip()
    relation = str(ctx.query.get("relation", "")).strip()
    if not instrument or not dimension or not relation:
        return Answer(
            "decline",
            None,
            "a measurement reading needs an instrument, dimension, and spatial relation",
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
                and placement.reference == instrument
                and placement.relation == relation
                and placement.occurrence is not None
                and placement.occurrence <= anchor.occurrence
            ):
                candidates.append((placement, anchor, anchor_families))

    if len(candidates) != 1:
        return Answer(
            "decline",
            None,
            f"the reading needs one {relation!r} placement and compatible total anchor; "
            f"found {len(candidates)}",
        )

    _placement, anchor, families = candidates[0]
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

    return Answer(
        "number",
        float(total),
        f"{anchor.container!r} on {instrument!r}: " + " ".join(steps),
    )


@consumer("measurement-content-amount")
def measurement_content_amount(ctx: ConsumerContext):
    """Recover an anchor content amount by subtracting the container tare.

    A resulting-total anchor states the container-plus-content mass.  The
    named content can be isolated only when that content established the
    anchor, the same container has one declared intrinsic mass, and the whole
    later measurement stream remains valid.  Later additions are replayed for
    accounting but never subtracted from the earlier content amount.
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

    anchors = [
        change
        for change in ctx.store.by_kind(MeasuredContentChange)
        if change.operation == "set_total"
        and change.container == container
        and change.content == content
    ]
    if len(anchors) != 1:
        return Answer(
            "decline",
            None,
            "the requested content needs one resulting-total anchor in its container",
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
    if len(tares) != 1:
        return Answer(
            "decline",
            None,
            "the requested content needs one compatible intrinsic container mass",
        )
    tare = tares[0]

    # Reuse the final-reading consumer to validate and account for every later
    # aggregate update. The tare is an additional, independently stated value,
    # so admit exactly that one mention into its premise audit.
    validated = measurement_reading(
        replace(
            ctx,
            query={
                "instrument": placement.reference,
                "dimension": anchor.dimension or "",
                "relation": placement.relation,
                "_additional_measured_values": (
                    (tare.provenance.sentence, tare.value),
                ),
            },
        )
    )
    if not validated.committed:
        return validated

    assert anchor.measure is not None
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

    return Answer(
        "number",
        float(amount),
        f"{content!r} in {container!r}: {anchor.value:g} {anchor.measure} "
        f"− {tare_value:g} {anchor.measure}",
    )
