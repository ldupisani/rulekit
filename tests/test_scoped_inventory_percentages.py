"""A scoped percentage excludes proven outsiders without discarding evidence."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantity


@pytest.fixture(scope="module")
def registry():
    return load_project(Path("projects/curated")).registry


ASK = "What percent of the flowers are not roses?"


@pytest.mark.parametrize("premise", [
    "There are 6 roses, 9 tulips, 15 daisies, and 8 apples",
    "There are 8 apples, 6 roses, 9 tulips, and 15 daisies",
    "There are 6 roses and 9 tulips and 15 daisies and 8 pears",
    "There are six roses, nine tulips, fifteen daisies, and eight bananas",
    "There are 6 roses in a garden, 9 tulips, 15 daisies, and 8 peaches",
    "There are 6 roses, 9 tulips, 15 daisies, and 8 apricots in a garden",
    "With 6 roses, 9 tulips, 15 daisies, and 8 apples in a garden",
    "With 6 roses, 9 tulips, 15 daisies, and 8 apples",
    "If there are 6 roses, 9 tulips, 15 daisies, and 8 apples",
    "There are 6 roses in a garden. There are 9 tulips. There are 15 daisies. There are 8 apples in a pantry",
    "Fia has 6 roses. Fia has 9 tulips. Fia has 15 daisies. Ben has 8 apples",
])
@pytest.mark.parametrize("complement", [True, False])
def test_percentage_and_complement_use_only_the_requested_category(registry, premise, complement):
    ask = ASK if complement else ASK.replace("not ", "")
    result = solve(premise + ". " + ask, registry)
    assert result.value == pytest.approx(80 if complement else 20), result.answer
    assert result.deficiencies() == []
    assert len(result.store.by_kind(Quantity)) == 4
    assert "declared category separation" in result.answer.reason


@pytest.mark.parametrize("extra", ["7 roses", "7 apples", "7 roses and 13 apples"])
def test_other_category_queries_reuse_the_same_projection(registry, extra):
    result = solve(f"There are 2 cats, 3 dogs, 5 birds, and {extra}. "
                   "What percent of the animals are not cats?", registry)
    assert result.value == 80, result.answer
    assert result.deficiencies() == []


def test_multiple_outside_counts_remain_read_and_available(registry):
    result = solve("There are 6 roses, 9 tulips, 15 daisies, 8 apples, and 11 pears. " + ASK, registry)
    assert result.value == 80, result.answer
    assert {row.measure: row.value for row in result.store.by_kind(Quantity)} == {
        "rose": 6, "tulip": 9, "daisy": 15, "apple": 8, "pear": 11,
    }
    total = next(entry for entry in result.log.entries if entry.source == "enumerated-category-total")
    assert total.result == 30


@pytest.mark.parametrize("premise", [
    "There are 6 roses, 9 tulips, 15 daisies, 8 apples, 4 children, and 11 pears",
    "There are 4 children, 8 apples, 6 roses, 9 tulips, 11 pears, and 15 daisies",
    "There are six roses, nine tulips, fifteen daisies, eight apples, four people, and eleven pears",
    "There are 6 roses in a garden, 9 tulips, 15 daisies, 8 apples, 4 boys, and 11 pears",
    "If there are 6 roses, 9 tulips, 15 daisies, 8 apples, 4 girls, and 11 pears in a garden",
    "With 6 roses, 9 tulips, 15 daisies, 8 apples, 4 workers, and 11 pears in a garden",
])
def test_mixed_inventories_account_for_every_count_without_diluting_the_category(registry, premise):
    result = solve(premise + ". " + ASK, registry)
    assert result.value == 80, result.answer
    assert result.deficiencies() == []
    assert len(result.store.by_kind(Quantity)) == 6
    assert "declared category separation" in result.answer.reason


@pytest.mark.parametrize("flowers", ["9 lilies, 15 sunflowers", "9 daffodils, 15 tulips"])
@pytest.mark.parametrize("outside", [
    "8 grapes", "8 plums", "8 mangoes", "8 mangos", "8 boys", "8 girls",
    "8 children", "8 people", "8 persons", "8 students", "8 sons",
    "8 penguins", "8 bees",
])
def test_expanded_flower_and_outside_vocabulary_reuses_the_same_inventory(registry, flowers, outside):
    result = solve(f"There are 6 roses, {flowers}, and {outside}. " + ASK, registry)
    assert result.value == 80, result.answer
    assert result.deficiencies() == []


@pytest.mark.parametrize("items,collection,subtype", [
    ("6 penguins, 9 sparrows, 15 ducks, 8 ants, and 4 children", "birds", "penguins"),
    ("6 ants, 9 bees, 15 butterflies, 8 ducks, and 4 teachers", "insects", "ants"),
    ("6 beetles, 9 bees, 15 ants, 8 penguins, and 4 girls", "insects", "beetles"),
    ("6 penguins, 9 ants, 15 cats, 8 roses, and 4 plums", "animals", "penguins"),
    ("6 lilies, 9 sunflowers, 15 daffodils, 8 bees, and 4 mangoes", "flowers", "lilies"),
    ("30 birds, 6 sparrows, 8 children, and 11 roses", "birds", "sparrows"),
    ("30 insects, 6 butterflies, 8 ducks, and 11 girls", "insects", "butterflies"),
    ("6 insects, 9 ducks, 15 cats, 8 plums, and 4 roses", "animals", "insects"),
    ("30 people, 6 children, 8 roses, and 11 mangoes", "people", "children"),
    ("30 persons, 6 boys, 8 lilies, and 11 grapes", "persons", "boys"),
])
@pytest.mark.parametrize("negated", [True, False])
def test_other_known_categories_support_subtypes_plurals_and_complements(
    registry, items, collection, subtype, negated,
):
    ask = f"What percent of the {collection} are {'not ' if negated else ''}{subtype}?"
    result = solve(f"There are {items}. " + ask, registry)
    assert result.value == (80 if negated else 20), result.answer
    assert result.deficiencies() == []


@pytest.mark.parametrize("premise,ask", [
    ("6 roses, 9 lilies, and 8 plants", ASK),
    ("6 roses, 9 lilies, and 8 rocks", ASK),
    ("6 roses, 9 lilies, 8 birds, and 2 sparrows", ASK),
    ("6 roses, 9 lilies, 8 people, and 2 children", ASK),
    ("6 penguins, 9 sparrows, and 8 animals", "What percent of the birds are not penguins?"),
    ("6 penguins, 9 sparrows, and 8 cats", "What percent of the birds are not penguins?"),
    ("6 penguins, 9 ants, and 8 children", "What percent of the animals are not penguins?"),
    ("6 insects, 9 bees, and 8 roses", "What percent of the animals are not insects?"),
    ("6 children, 9 workers, and 8 animals", "What percent of the people are not children?"),
    ("6 lilies, 9 sunflowers, and 8 zinnias", "What percent of the flowers are not lilies?"),
])
def test_category_expansion_preserves_unknown_and_overlapping_boundaries(registry, premise, ask):
    assert not solve(f"There are {premise}. " + ask, registry).answer.committed


@pytest.mark.parametrize("outside", [6, 30])
def test_equal_values_do_not_confuse_category_membership(registry, outside):
    result = solve(f"There are 6 roses, 9 tulips, 15 daisies, and {outside} apples. " + ASK, registry)
    assert result.value == 80, result.answer
    assert result.deficiencies() == []


@pytest.mark.parametrize("outside", [8, 80])
def test_explicit_category_total_excludes_foreign_counts(registry, outside):
    result = solve(f"There are 30 flowers, 6 roses, and {outside} apples. " + ASK, registry)
    assert result.value == 80, result.answer
    assert result.deficiencies() == []


@pytest.mark.parametrize("premise", [
    "There are 6 roses and 8 apples",
    "There are 8 apples and 11 pears",
    "There are 6 roses, 9 tulips, and 8 rocks",
    "There are 6 roses, 9 tulips, and 8 plants",
    "There are 6 roses, 9 tulips, and 8 foods",
    "There are 6 red roses, 9 tulips, and 8 apples",
    "There are 6 roses, 9 tulips, and 8 red apples",
    "There are 6 roses, 9 tulips, 8 apples, and 11 apples",
    "There are 6 roses in a garden. There are 9 tulips in a park. There are 8 apples",
    "There are 6 roses, 9 tulips, and 8.5 apples",
    "There are 6 roses, 9 tulips, and -8 apples",
    "There are 0 roses, 0 tulips, and 8 apples",
    "There are 6 roses, 9 tulips, and 8 apples each",
    "There are 6 roses, 9 tulips, and 8 apples. Fia bought 2 apples",
    "There are 6 roses, 9 tulips, and 8 apples. Fia lost 2 apples",
    "There are 10 flowers, 6 roses, 9 tulips, and 8 apples",
    "There are 6 roses, 9 tulips, and 8 apples in total",
    "There are 6 roses, 9 tulips, or 8 apples",
])
def test_filtering_does_not_hide_ambiguity_or_unaccounted_conditions(registry, premise):
    assert not solve(premise + ". " + ASK, registry).answer.committed
