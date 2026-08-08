"""Relative temporal markers preserve event coordinates and strict order."""

from pathlib import Path

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Before, EventTime, VerbalRelation
from rulekit.server.api import _field_json


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
GSM8K = ROOT / "projects" / "gsm8k"

TEXT = (
    "Tom traveled toward the garden yesterday. "
    "Sally will travel toward the garden tomorrow. "
    "Bob traveled toward the garden today."
)
ARRIVAL_TEXT = (
    "Tom arrived at the garden yesterday. "
    "Sally will arrive at the garden tomorrow. "
    "Bob arrived at the garden today."
)


def test_relative_day_markers_and_offsets_are_core_owned() -> None:
    project = load_project(CURATED)
    registry = project.registry
    source = (ROOT / "packs/core-english/categories/core.yaml").resolve()

    assert registry.temporal_offsets == {
        "now": 0,
        "today": 0,
        "tomorrow": 1,
        "yesterday": -1,
    }
    for marker in registry.temporal_offsets:
        assert registry.word_in_category(marker, "deictic_temporal_marker")
        assert registry.lexicon[marker].senses == ["time"]
        assert project.source_index.temporal_offsets[marker].path.resolve() == source
    assert {
        marker
        for marker in registry.temporal_offsets
        if registry.word_in_category(marker, "temporal_marker")
    } == {"now", "today"}


def test_relative_markers_anchor_events_and_derive_complete_strict_order() -> None:
    result = solve(TEXT, load_project(CURATED).registry)
    events = list(result.store.by_kind(EventTime))
    by_marker = {event.marker: event for event in events}

    assert result.document is not None
    assert not [
        gap
        for gap in result.document.gaps
        if gap.kind == "unknown-word"
    ]
    assert set(by_marker) == {"yesterday", "today", "tomorrow"}
    assert {
        marker: (event.entity, event.verb, event.obj, event.offset)
        for marker, event in by_marker.items()
    } == {
        "yesterday": ("tom", "travel", "garden", -1.0),
        "today": ("bob", "travel", "garden", 0.0),
        "tomorrow": ("sally", "travel", "garden", 1.0),
    }

    before = {
        (fact.earlier, fact.later)
        for fact in result.store.by_kind(Before)
    }
    assert before == {
        (by_marker["yesterday"].event, by_marker["today"].event),
        (by_marker["yesterday"].event, by_marker["tomorrow"].event),
        (by_marker["today"].event, by_marker["tomorrow"].event),
    }

    goals = {
        (fact.entity, fact.obj, fact.role)
        for fact in result.store.by_kind(VerbalRelation)
    }
    assert goals == {
        ("tom", "garden", "spatial-goal"),
        ("sally", "garden", "spatial-goal"),
        ("bob", "garden", "spatial-goal"),
    }


def test_deictic_field_exposes_ordered_events_without_ordering_opaque_labels() -> None:
    field = _field_json(solve(TEXT, load_project(CURATED).registry))
    time = field["time"]

    assert time["ordered"] is True
    assert [event["marker"] for event in time["events"]] == [
        "yesterday",
        "today",
        "tomorrow",
    ]
    assert [event["offset"] for event in time["events"]] == [-1.0, 0.0, 1.0]
    assert len(time["before"]) == 3
    assert time["labels"] == []


def test_arrival_events_preserve_destination_and_the_same_temporal_order() -> None:
    result = solve(ARRIVAL_TEXT, load_project(CURATED).registry)
    events = list(result.store.by_kind(EventTime))
    by_marker = {event.marker: event for event in events}

    assert result.document is not None
    assert result.document.gaps == []
    assert {
        (event.entity, event.verb, event.obj, event.marker, event.offset)
        for event in events
    } == {
        ("tom", "arrive", "garden", "yesterday", -1.0),
        ("bob", "arrive", "garden", "today", 0.0),
        ("sally", "arrive", "garden", "tomorrow", 1.0),
    }
    assert {
        (relation.entity, relation.verb, relation.prep, relation.obj, relation.role)
        for relation in result.store.by_kind(VerbalRelation)
    } == {
        ("tom", "arrive", "at", "garden", "spatial-goal"),
        ("bob", "arrive", "at", "garden", "spatial-goal"),
        ("sally", "arrive", "at", "garden", "spatial-goal"),
    }
    assert {
        (fact.earlier, fact.later)
        for fact in result.store.by_kind(Before)
    } == {
        (by_marker["yesterday"].event, by_marker["today"].event),
        (by_marker["yesterday"].event, by_marker["tomorrow"].event),
        (by_marker["today"].event, by_marker["tomorrow"].event),
    }


def test_time_sense_without_a_declared_offset_does_not_gain_an_order() -> None:
    result = solve(
        "Tom traveled toward the garden tonight.",
        load_project(GSM8K).registry,
    )

    assert result.store.by_kind(EventTime) == []
    assert result.store.by_kind(Before) == []


def test_competing_markers_or_predicates_do_not_guess_scope() -> None:
    registry = load_project(CURATED).registry

    competing_markers = solve(
        "Tom traveled toward the garden yesterday today.", registry
    )
    coordinated_predicates = solve(
        "Tom traveled and walked toward the garden yesterday.", registry
    )

    assert competing_markers.store.by_kind(EventTime) == []
    assert coordinated_predicates.store.by_kind(EventTime) == []
