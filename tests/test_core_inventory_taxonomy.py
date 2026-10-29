"""Vocabulary families classify counted nouns without inventing a closed world."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project


@pytest.fixture(scope="module")
def project():
    return load_project(Path("projects/curated"))


@pytest.mark.parametrize("word,plural,category", [
    ("daffodil", "daffodils", "flower"),
    ("lily", "lilies", "flower"),
    ("sunflower", "sunflowers", "flower"),
    ("duck", "ducks", "bird"),
    ("penguin", "penguins", "bird"),
    ("sparrow", "sparrows", "bird"),
    ("ant", "ants", "insect"),
    ("bee", "bees", "insect"),
    ("butterfly", "butterflies", "insect"),
    ("insect", "insects", "animal"),
])
def test_counted_vocabulary_has_core_owned_morphology_and_classification(project, word, plural, category):
    registry = project.registry
    assert registry.plural_to_singular[plural] == word
    assert registry.word_in_category(word, category)
    assert registry.word_in_category(plural, category)
    assert project.source_index.lexicon[word].path.parts[-3:] == (
        "core-english", "lexicon", "core.yaml",
    )


@pytest.mark.parametrize("word", ["grape", "plum", "mango", "mangoes", "mangos"])
def test_existing_fruit_vocabulary_gains_classification_only(project, word):
    assert project.registry.word_in_category(word, "fruit")
    assert project.registry.category_terms_disjoint("flower", word)


@pytest.mark.parametrize("word", ["boy", "girl", "child", "children", "person", "people", "persons"])
def test_people_are_known_outside_botanical_categories(project, word):
    registry = project.registry
    assert registry.word_in_category(word, "person")
    assert registry.category_terms_disjoint("flower", word)
    assert registry.category_terms_disjoint("fruit", word)
    assert registry.category_terms_disjoint(word, "flower")
    assert registry.category_terms_disjoint(word, "fruit")


def test_subfamilies_inherit_membership_and_only_declared_separation(project):
    registry = project.registry
    for family, word in [("bird", "sparrow"), ("insect", "butterfly")]:
        assert registry.category_term_contains("animal", family)
        assert registry.category_term_contains(family, word)
        assert registry.word_in_category(word, "animal")
        assert registry.category_terms_disjoint(word, "person")
    assert registry.category_terms_disjoint("bird", "insect")
    assert registry.category_terms_disjoint("sparrow", "butterfly")
    assert registry.category_term_contains("person", "child")
    assert not registry.category_terms_disjoint("animal", "person")
    assert not registry.category_terms_disjoint("bird", "cat")
    assert not registry.category_terms_disjoint("flower", "plant")


def test_classification_does_not_grant_unrelated_roles_or_admit_quarantined_words(project):
    registry = project.registry
    for word in ["daffodil", "lily", "sunflower"]:
        assert not registry.word_in_category(word, "edible_quantity_object")
        assert not registry.word_in_category(word, "quantity_holder")
    for word in ["technician", "penguin", "ant"]:
        assert not registry.word_in_category(word, "animate")
    assert not registry.word_in_category("mango", "edible_quantity_object")
    assert "fruit" not in registry.lexicon
    assert "fruits" not in registry.lexicon


def test_promoted_vocabulary_has_no_redundant_mined_owner():
    project = load_project(Path("projects/gsm8k"))
    core, *_, mined = project.packs
    words = {"ant", "ants", "duck", "insect", "insects", "lily", "lilies",
             "penguin", "sparrow", "sunflower"}
    assert not words & mined.lexicon.keys()
    assert {"ant", "duck", "insect", "lily", "penguin", "sparrow", "sunflower"} <= core.lexicon.keys()
