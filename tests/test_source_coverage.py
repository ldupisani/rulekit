"""Source completeness is shared without merging consumer evidence policies."""

from types import SimpleNamespace
from dataclasses import replace

from rulekit.kernel.model import Unit, EventTime, Provenance
from rulekit.kernel.source_coverage import (
    uncovered_units, uncovered_document_units, covered_temporal_annotation,
)


def unit(uid, sense, **features):
    return Unit(uid, (), {"senses": [sense], **features})


def test_only_explicit_coverage_or_rule_consumption_covers_content():
    condition = unit(3, "negator")
    qualifier = unit(4, "adjective")
    reading = SimpleNamespace(units=[
        unit(0, "article"), unit(1, "noun"),
        unit(2, "verb", pattern_consumed=True), condition, qualifier,
        unit(5, "punct"),
    ])
    assert uncovered_units(reading, {1}) == (condition, qualifier)
    assert not uncovered_units(reading, {1, 3, 4})


def test_ask_unit_ids_cannot_cover_units_in_another_sentence():
    premise_unit = unit(0, "noun")
    premise = SimpleNamespace(sentence_index=0, units=[premise_unit])
    question = SimpleNamespace(sentence_index=1, units=[unit(0, "noun")])
    assert uncovered_document_units([premise], question, {0}) == ((0, premise_unit),)


def test_unknown_and_unresolved_senses_are_not_silently_ignored():
    unknown = Unit(0, (), {})
    reading = SimpleNamespace(units=[unknown])
    assert uncovered_units(reading) == (unknown,)


def test_a_fold_footprint_must_be_passed_explicitly():
    amount = unit(0, "noun", value=7, value_kind="count")
    condition = unit(1, "modal")
    reading = SimpleNamespace(units=[amount, condition])
    assert uncovered_units(reading) == (amount, condition)
    assert uncovered_units(reading, {amount.uid}) == (condition,)


def test_temporal_metadata_needs_the_consumed_predicate_entity_and_period():
    predicate = unit(3, "verb", lemma="produce", pattern_consumed=True)
    reading = SimpleNamespace(sentence_index=2, units=[predicate])
    event = EventTime(
        provenance=Provenance("fold", 2), event="s2:u3", entity="workshop",
        verb="produce", marker="today", offset=0,
    )
    args = ([reading], "workshop", {(2, "today")})
    assert covered_temporal_annotation(event, *args)
    for field, value in (
        ("entity", "factory"), ("marker", "yesterday"),
        ("verb", "destroy"), ("event", "s2:u4"),
        ("provenance", Provenance("fold", 1)),
    ):
        assert not covered_temporal_annotation(replace(event, **{field: value}), *args)
    predicate.features.pop("pattern_consumed")
    assert not covered_temporal_annotation(event, *args)
