"""Final reading of an instrument observing one ordered content stream."""

from __future__ import annotations

from collections import Counter
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
