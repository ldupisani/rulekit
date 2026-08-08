"""Finite-domain witness selection over temporally anchored location fluents."""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("location-witnesses")
def location_witnesses(ctx: ConsumerContext):
    from ..answer import Answer, AnswerProof, ProofStep, SemanticNode
    from ..model import (
        EventTime,
        LocationConstraint,
        LocationEvent,
        LocationTransitionAbsence,
        VerbalRelation,
    )
    from ..patterns import SKIPPABLE_SENSES

    unread = [
        unit.surface
        for unit in ctx.question.units
        if unit.sense() not in SKIPPABLE_SENSES
        and unit.uid not in ctx.match.consumed
    ]
    if unread:
        return Answer(
            "decline",
            None,
            f"question states {unread!r} outside the location witness query",
        )

    candidates = ctx.query.get("candidates")
    if (
        not isinstance(candidates, list)
        or len(candidates) < 2
        or len(candidates) != len(set(candidates))
        or not all(isinstance(candidate, str) and candidate for candidate in candidates)
    ):
        return Answer(
            "decline",
            None,
            "a 'which of them' query needs one exact group of distinct named candidates",
        )
    place = ctx.query.get("place")
    marker = ctx.query.get("when")
    if (
        not isinstance(place, str)
        or not isinstance(marker, str)
        or marker not in ctx.reg.temporal_offsets
        or not ctx.reg.word_in_category(marker, "day_deictic_marker")
    ):
        return Answer(
            "decline",
            None,
            "the location witness query needs one declared day and place",
        )

    query_offset = float(ctx.reg.temporal_offsets[marker])
    times = {fact.event: fact for fact in ctx.store.by_kind(EventTime)}
    relations = {
        fact.event: fact
        for fact in ctx.store.by_kind(VerbalRelation)
        if fact.event is not None
    }
    constraints = [
        fact
        for fact in ctx.store.by_kind(LocationConstraint)
        if fact.place == place
        and fact.transition == "terminates"
        and fact.modality == "impossible"
    ]
    absences = [
        fact
        for fact in ctx.store.by_kind(LocationTransitionAbsence)
        if fact.place == place
        and fact.transition == "terminates"
        and fact.scope == "narrative-through-reference"
        and fact.subject_class == "person"
    ]
    if absences:
        conflicting_departures = []
        for event in ctx.store.by_kind(LocationEvent):
            if event.place != place or event.effect != "terminates":
                continue
            event_time = times.get(event.event)
            if event_time is None or event_time.offset <= query_offset:
                conflicting_departures.append(event)
        if conflicting_departures:
            return Answer(
                "decline",
                None,
                f"observed departure conflicts with the stated no-departure "
                f"interval at {place!r}",
            )

    query_node = SemanticNode(
        "LocationWitnesses",
        (
            ("candidates", tuple(candidates)),
            ("place", place),
            ("time", marker),
        ),
    )
    rows: list[dict[str, str]] = []
    steps: list[ProofStep] = []
    for entity in candidates:
        direct_positive = []
        direct_negative = []
        earlier_initiations = []
        for event in ctx.store.by_kind(LocationEvent):
            if event.entity != entity or event.place != place:
                continue
            event_time = times.get(event.event)
            if event_time is None:
                continue
            if event_time.marker == marker:
                if event.effect in ("holds", "initiates"):
                    direct_positive.append((event, event_time))
                elif event.effect == "not-holds":
                    direct_negative.append((event, event_time))
            elif event.effect == "initiates" and event_time.offset < query_offset:
                earlier_initiations.append((event, event_time))

        if direct_positive and direct_negative:
            return Answer(
                "decline",
                None,
                f"conflicting direct location evidence for {entity!r} at "
                f"{place!r}/{marker!r}",
            )
        if direct_negative and earlier_initiations and absences:
            return Answer(
                "decline",
                None,
                f"conflicting direct location evidence for {entity!r} at "
                f"{place!r}/{marker!r}",
            )

        selected = None
        persistence_license = None
        if direct_negative:
            status = "contradicted"
            selected = direct_negative[0]
        elif direct_positive:
            status = "supported"
            selected = direct_positive[0]
        elif earlier_initiations and (constraints or absences):
            status = "supported"
            selected = earlier_initiations[0]
            persistence_license = (constraints or absences)[0]
        else:
            status = "unknown"

        rows.append({"entity": entity, "status": status})
        if selected is None:
            continue
        event, event_time = selected
        evidence = []
        relation = relations.get(event.event)
        if relation is not None:
            evidence.append(relation)
        evidence.extend((event, event_time))
        if persistence_license is not None:
            evidence.append(persistence_license)
        conclusion = SemanticNode(
            "LocationStatus",
            (
                ("entity", entity),
                ("place", place),
                ("time", marker),
                ("status", status),
            ),
        )
        if status == "contradicted":
            rule = "inference/location-not-at-event"
            detail = (
                f"{entity!r} has direct negative location evidence at {marker!r}"
            )
        elif persistence_license is None:
            rule = "inference/location-at-event"
            detail = f"{entity!r} has direct location evidence at {marker!r}"
        elif isinstance(persistence_license, LocationTransitionAbsence):
            rule = "inference/location-no-departure-persistence"
            detail = (
                f"the earlier arrival of {entity!r} persists because no one "
                f"departed {place!r} during the narrative interval"
            )
        else:
            rule = "inference/location-persistence"
            detail = (
                f"the earlier arrival of {entity!r} persists because terminating "
                f"the location state at {place!r} is impossible"
            )
        steps.append(ProofStep(rule, conclusion, tuple(evidence), detail))

    supported_names = [row["entity"] for row in rows if row["status"] == "supported"]
    contradicted_names = [
        row["entity"] for row in rows if row["status"] == "contradicted"
    ]
    unknown_names = [row["entity"] for row in rows if row["status"] == "unknown"]
    reason = f"supported at {place!r}/{marker!r}: {supported_names}"
    if contradicted_names:
        reason += f"; contradicted: {contradicted_names}"
    if unknown_names:
        reason += f"; unknown: {unknown_names}"
    return Answer(
        "witnesses",
        rows,
        reason,
        AnswerProof(query_node, tuple(steps)),
    )
