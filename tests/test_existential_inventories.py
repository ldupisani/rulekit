"""Coordinated counted inventories retain every member, location and scope."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from rulekit.data.project import load_project
from rulekit.data.schemas import MatchToken
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantity


@pytest.fixture(scope="module")
def registry():
    return load_project(Path("projects/curated")).registry


FLOWER_ASK = "What percent of the flowers are not roses?"


@pytest.mark.parametrize("premise,expected", [
    ("There are 12 roses in a garden, 18 tulips, and 30 daisies", 80),
    ("There are 12 roses in a garden, 18 tulips and 30 daisies", 80),
    ("There are 12 roses in a garden and 18 tulips and 30 daisies", 80),
    ("There are 12 roses, 18 tulips, and 30 daisies in a garden", 80),
    ("There are 12 roses, 18 tulips and 30 daisies at a park", 80),
    ("There are 12 roses, 18 tulips, and 30 daisies", 80),
    ("There are 12 roses and 18 tulips and 30 daisies", 80),
    ("There are 12 roses in a garden and 18 tulips", 60),
    ("There are 12 roses and 18 tulips in a garden", 60),
    ("There are 12 roses and 18 tulips", 60),
])
@pytest.mark.parametrize("frame", ["asserted", "detached", "leading", "trailing"])
def test_inventory_locations_lists_and_question_local_scope(registry, premise, expected, frame):
    if frame == "asserted":
        text = premise + ". " + FLOWER_ASK
    elif frame == "detached":
        text = "If " + premise.lower() + ". " + FLOWER_ASK
    elif frame == "leading":
        text = "If " + premise.lower() + ", " + FLOWER_ASK.lower()
    else:
        text = FLOWER_ASK[:-1] + ", if " + premise.lower() + "?"
    result = solve(text, registry)
    assert result.value == pytest.approx(expected), result.answer
    assert result.deficiencies() == []
    rows = result.store.by_kind(Quantity)
    assert {row.provenance.assumption for row in rows} == {frame != "asserted"}
    assert sum(row.value for row in rows) == (60 if expected == 80 else 30)


@pytest.mark.parametrize("location", ["", " in a garden"])
def test_inventory_is_not_limited_to_three_members_or_flowers(registry, location):
    text = (f"There are 2 cats, 3 dogs, 5 birds, and 10 hamsters{location}. "
            "What percentage of animals are not cats?")
    result = solve(text, registry)
    assert result.value == 90, result.answer
    assert result.deficiencies() == []
    assert len(result.store.by_kind(Quantity)) == 4


def test_shared_location_preserves_all_counts_for_existing_comparison(registry):
    result = solve("There are 12 roses in a garden, 18 tulips, and 30 daisies. "
                   "How many more tulips than roses does the garden have?", registry)
    assert result.value == 6, result.answer
    assert {(row.entity, row.measure, row.value) for row in result.store.by_kind(Quantity)} == {
        ("garden", "rose", 12), ("garden", "tulip", 18), ("garden", "daisy", 30),
    }


def test_counted_list_members_preserve_qualifiers_and_shared_holder(registry):
    result = solve("There are 2 red cats, 3 dogs, and 5 birds in a garden. "
                   "What percentage of animals are not cats?", registry)
    assert not result.answer.committed
    rows = result.store.by_kind(Quantity)
    cats = next(row for row in rows if row.measure == "cat")
    assert cats.value == 2
    assert cats.measure_qualifier == "red"
    assert cats.entity_ref.head == "garden"
    assert all(row.entity_ref == cats.entity_ref for row in rows)
    assert len(rows) == 3


@pytest.mark.parametrize("premise", [
    "There are 12 roses in a garden, 18 tulips, or 30 daisies",
    "There are 12 roses in a garden, 18 tulips, and 30 rocks",
    "There are 12 roses in a garden, 18 tulips in a park, and 30 daisies",
    "There are 12 red roses in a garden, 18 tulips, and 30 daisies",
    "There are 12 roses in a garden, 18 roses, and 30 daisies",
    "There are 12.5 roses in a garden, 18 tulips, and 30 daisies",
    "There are 12 roses in a garden, 18 tulips, and daisies",
    "There are 12 roses in a garden, 18 tulips, and 30 daisies and",
    "There are 12 roses in a garden, 18 tulips, 30 daisies",
    "There is 12 roses in a garden, 18 tulips, and 30 daisies",
    "There are 12 roses in a garden, 18 tulips, and 30 daisies each",
    "There are 12 roses in a garden, 18 tulips,, and 30 daisies",
    "There are 12 roses in each garden, 18 tulips, and 30 daisies",
    "There are 12 roses in a garden, 18 tulips, and 30 daisies for Fia",
    "There are 12 roses, 18 tulips, and 30 daisies in 2 gardens",
    "There are 12 roses, 18 tulips, and 30 daisies in 3 hours",
    "There are 12 roses in a garden, 18 tulips, and 30 daisies in total",
    "There are 12 roses in a garden, 18 tulips, and 30 pounds of daisies",
    "There are 12 roses in a garden, 18 tulips, and 30 daisies. Fia bought 7 roses",
    "If there are 12 roses in a garden, 18 tulips, and 30 daisies. There are 7 tulips",
])
def test_inventory_does_not_discard_conditions_or_infer_unstated_scope(registry, premise):
    assert not solve(premise + ". " + FLOWER_ASK, registry).answer.committed


def test_question_local_inventory_does_not_persist(registry):
    assumed = solve("If there are 12 roses, 18 tulips, and 30 daisies. " + FLOWER_ASK, registry)
    assert assumed.value == 80
    assert not solve(FLOWER_ASK, registry).answer.committed


def test_counted_enumeration_requires_a_gated_span():
    with pytest.raises(ValidationError, match="enumeration_counted requires enumeration_cat"):
        MatchToken(slot="items", span=True, enumeration_counted=True)
    with pytest.raises(ValidationError, match="enumeration_cat requires a span"):
        MatchToken(slot="items", type="noun", enumeration_cat="noun", enumeration_counted=True)


@pytest.mark.parametrize("premise,expected", [
    ("With 12 roses, 18 tulips, and 30 daisies in a garden", 80),
    ("With 12 roses, 18 tulips and 30 daisies in the garden", 80),
    ("With 12 roses and 18 tulips and 30 daisies at a park", 80),
    ("With 12 roses, 18 tulips, and 30 daisies", 80),
    ("With 12 roses and 18 tulips in a garden", 60),
    ("With 12 roses and 18 tulips", 60),
    ("With twelve roses, eighteen tulips, and thirty daisies in a garden", 80),
])
@pytest.mark.parametrize("negated", [True, False])
def test_with_introduces_a_complete_inventory(registry, premise, expected, negated):
    ask = FLOWER_ASK if negated else FLOWER_ASK.replace("not ", "")
    result = solve(premise + ". " + ask, registry)
    assert result.value == pytest.approx(expected if negated else 100 - expected), result.answer
    assert result.deficiencies() == []


@pytest.mark.parametrize("location", ["", " in a garden"])
def test_with_inventory_reuses_animal_categories_and_arbitrary_list_lengths(registry, location):
    result = solve(f"With 2 cats, 3 dogs, 5 birds, and 10 hamsters{location}. "
                   "What percent of the animals are not cats?", registry)
    assert result.value == 90, result.answer
    assert result.deficiencies() == []
    assert len(result.store.by_kind(Quantity)) == 4


def test_with_inventory_reuses_existing_located_comparisons(registry):
    result = solve("With 12 roses, 18 tulips, and 30 daisies in a garden. "
                   "How many more tulips than roses does the garden have?", registry)
    assert result.value == 6, result.answer
    assert result.deficiencies() == []


@pytest.mark.parametrize("premise", [
    "Without 12 roses, 18 tulips, and 30 daisies in a garden",
    "Fia works with 12 roses, 18 tulips, and 30 daisies in a garden",
    "Fia paints with 12 roses, 18 tulips, and 30 daisies in a garden",
    "With 12 roses, 18 tulips, or 30 daisies in a garden",
    "With 12 roses, 18 tulips, 30 daisies in a garden",
    "With 12 roses, 18 tulips, and daisies in a garden",
    "With 12 red roses, 18 tulips, and 30 daisies in a garden",
    "With 12 roses, 18 roses, and 30 daisies in a garden",
    "With 12 roses, 18 tulips, and 30 rocks in a garden",
    "With 12 roses in a garden, 18 tulips, and 30 daisies in a park",
    "With 12 roses, 18 tulips, and 30 daisies in 2 gardens",
    "With 12 roses, 18 tulips, and 30 daisies in each garden",
    "With 12 roses, 18 tulips, and 30 daisies in 3 hours",
    "With 12 roses, 18 tulips, and 30 daisies in a garden each",
    "With 12 roses, 18 tulips, and 30 daisies in a garden. Fia planted 7 roses",
])
def test_with_inventory_does_not_ignore_scope_or_nonholding_uses(registry, premise):
    assert not solve(premise + ". " + FLOWER_ASK, registry).answer.committed
