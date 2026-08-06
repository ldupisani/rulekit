"""Synthetic coverage for explicit animal-superclass total questions."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.data.schemas import CategoryDef
from rulekit.kernel.answer import match_ask
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantity


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/gsm8k")).registry


def test_prenominal_total_pronoun_uses_combined_ask(reg):
    result = solve(
        "Priya has 4 daughters. Priya has 3 sons. "
        "How many total children did they have?",
        reg,
        tracing=False,
    )

    assert result.question is not None
    matched = match_ask(result.question, reg)
    assert matched is not None
    assert matched[0].id == "ask/how-many-combined-prenominal-marker"
    assert result.answer.value == 7


def test_pronoun_superclass_question_without_total_marker_stays_unclaimed(reg):
    result = solve(
        "Priya has 4 daughters. Priya has 3 sons. "
        "How many children did they have?",
        reg,
        tracing=False,
    )

    assert result.answer.kind == "decline"
    assert result.answer.reason == "no ask shape recognizes this question"


def test_two_animal_subtypes_roll_up_to_animals(reg):
    result = solve(
        "A zoo has 6 penguins and three times as many polar bears. "
        "How many total animals did they have?",
        reg,
        tracing=False,
    )

    quantities = {
        (fact.entity, fact.measure): fact.value
        for fact in result.store.by_kind(Quantity)
    }
    assert quantities[("zoo", "penguin")] == 6
    assert quantities[("zoo", "bear")] == 18
    assert result.answer.value == 24


def test_one_animal_subtype_is_not_a_complete_total(reg):
    result = solve(
        "A zoo has 6 penguins. How many total animals did they have?",
        reg,
        tracing=False,
    )

    assert result.answer.kind == "decline"


def test_open_animal_class_does_not_compose_separate_premises(reg):
    result = solve(
        "A zoo has 6 penguins. The zoo has 8 bears. "
        "How many total animals did they have?",
        reg,
        tracing=False,
    )

    assert result.answer.kind == "decline"


def test_unrelated_holding_prevents_partial_animal_total(reg):
    result = solve(
        "A zoo has 6 penguins. The zoo has 8 bears. The zoo has 10 tickets. "
        "How many total animals did they have?",
        reg,
        tracing=False,
    )

    assert result.answer.kind == "decline"


def test_animal_superclass_vocabulary_is_explicit(reg):
    assert "animal" in reg.coordinated_superordinate_categories
    assert "animal" not in reg.superordinate_categories
    assert reg.word_in_category("penguin", "animal")
    assert reg.word_in_category("bear", "animal")
    assert reg.word_in_category("zoo", "quantity_holder")


def test_superordinate_contracts_are_mutually_exclusive():
    with pytest.raises(ValueError, match="both closed and coordinated-only"):
        CategoryDef(
            parent="noun",
            superordinate=True,
            coordinated_superordinate=True,
        )
