"""Typed spatial preposition categories and exact PP preservation."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.document import run_document
from rulekit.kernel.engine import analyze
from rulekit.kernel.model import Predication, VerbalRelation


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"


def _document(sentence: str):
    project = load_project(CURATED)
    reading = analyze(sentence, project.registry, tracing=False)
    return run_document([reading], project.registry), project.registry


def _relations(sentence: str) -> list[VerbalRelation]:
    document, _ = _document(sentence)
    return list(document.store.by_kind(VerbalRelation))


def test_spatial_role_categories_are_narrow_and_composable() -> None:
    _, registry = _document("Tom walked through the garden.")

    assert registry.word_in_category("through", "spatial_path_preposition")
    assert registry.word_in_category("through", "spatial_preposition")
    assert registry.word_in_category("from", "spatial_source_preposition")
    assert registry.word_in_category("to", "spatial_goal_preposition")
    assert registry.word_in_category("inside", "spatial_location_preposition")
    assert registry.word_in_category("over", "spatial_location_preposition")
    assert registry.word_in_category("over", "spatial_path_preposition")
    assert not registry.word_in_category("during", "spatial_preposition")
    # These recognized prepositions need their own complement constraints
    # before they can safely acquire a spatial role.
    assert not registry.word_in_category("among", "spatial_preposition")
    assert not registry.word_in_category("between", "spatial_preposition")
    assert not registry.word_in_category("against", "spatial_preposition")
    assert registry.word_in_category("at", "arrival_goal_preposition")
    assert not registry.word_in_category("walked", "arrival_motion_verb")
    assert registry.word_in_category("arrived", "arrival_motion_verb")


def test_spatial_goal_role_has_general_and_arrival_specific_frames() -> None:
    _, registry = _document("Tom arrived at the garden.")

    assert registry.adposition_roles["spatial-goal"] == (
        (
            "spatial_goal_preposition",
            "spatial_reference_noun",
            "spatial_motion_verb",
            True,
        ),
        (
            "arrival_goal_preposition",
            "spatial_reference_noun",
            "arrival_motion_verb",
            True,
        ),
    )


@pytest.mark.parametrize(
    ("sentence", "verb", "marker", "obj", "role"),
    [
        ("Tom is inside the garden.", "be", "inside", "garden", "spatial-location"),
        ("Tom walked through the garden.", "walk", "through", "garden", "spatial-path"),
        ("Tom traveled from the garden.", "travel", "from", "garden", "spatial-source"),
        ("Tom traveled towards the garden.", "travel", "towards", "garden", "spatial-goal"),
        ("Tom traveled toward the garden.", "travel", "toward", "garden", "spatial-goal"),
        ("Tom traveled to Mary.", "travel", "to", "mary", "spatial-goal"),
        ("Tom walked next to the garden.", "walk", "next to", "garden", "spatial-location"),
        ("Tom walked out of the garden.", "walk", "out of", "garden", "spatial-source"),
        ("Tom arrived at the garden.", "arrive", "at", "garden", "spatial-goal"),
        ("Tom arrives at the garden.", "arrive", "at", "garden", "spatial-goal"),
    ],
)
def test_declared_spatial_pp_is_preserved_exactly(
    sentence: str, verb: str, marker: str, obj: str, role: str
) -> None:
    relation = _relations(sentence)[0]

    assert _relations(sentence) == [
        VerbalRelation(
            provenance=relation.provenance,
            entity="tom",
            verb=verb,
            prep=marker,
            obj=obj,
            role=role,
            event=relation.event,
        )
    ]


def test_indefinite_spatial_object_remains_indefinite() -> None:
    relation = _relations("Tom walked through a garden.")[0]

    assert relation.obj == "garden"
    assert relation.indef_obj is True


@pytest.mark.parametrize(
    "sentence",
    [
        "Tom walked through garden.",  # bare common object is not referential
        "Tom walked through the apple.",  # arbitrary noun is not a place
        "Tom is into the garden.",  # a goal requires a motion predicate
        "Tom painted through the garden.",  # a path requires a motion predicate
        "Tom stayed during the garden.",  # the marker has no spatial role
        "Tom is among the garden.",  # collective complement boundary is unbuilt
        "Tom arrived at the apple.",  # arbitrary nouns do not become destinations
    ],
)
def test_unlicensed_spatial_interpretations_emit_no_relation(sentence: str) -> None:
    assert _relations(sentence) == []


def test_arrival_at_frame_does_not_make_ordinary_motion_a_goal() -> None:
    relations = _relations("Tom walked at the garden.")

    assert [relation.role for relation in relations] == ["spatial-location"]


def test_spatial_relation_is_supplementary_and_does_not_claim_the_sentence() -> None:
    document, _ = _document("Tom walked through the garden.")

    assert list(document.store.by_kind(VerbalRelation))
    assert list(document.store.by_kind(Predication))
    assert document.consumed_uids[0] == set()


def test_arrival_vocabulary_and_morphology_are_core_owned() -> None:
    project = load_project(CURATED)
    source = (ROOT / "packs/core-english/lexicon/core.yaml").resolve()

    assert {
        project.source_index.lexicon[word].path.resolve()
        for word in ("arrive", "arrived", "arrives")
    } == {source}
    assert project.registry.verb_lemmas["arrived"] == "arrive"
    assert project.registry.verb_lemmas["arrives"] == "arrive"
    assert project.source_index.morphology[
        ("arrived", "verb.lemma")
    ].path.resolve() == source
