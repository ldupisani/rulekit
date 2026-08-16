"""Refrigerated interior locations in complete quantity questions.

All examples are synthetic.  ``fridge`` joins the existing declarative
interior-location family; the ordinary quantity fold, consumption events,
location ask, and named-holder ask retain their existing completeness rules.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_ask_scenario
from rulekit.kernel.engine import analyze, solve
from rulekit.kernel.model import Quantity
from rulekit.kernel.patterns import match_ask


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects" / "gsm8k"
CORE_LEXICON = (ROOT / "packs/core-english/lexicon/core.yaml").resolve()
CORE_CATEGORIES = (ROOT / "packs/core-english/categories/core.yaml").resolve()


@pytest.fixture(scope="module")
def project():
    return load_project(PROJECT)


@pytest.fixture(scope="module")
def registry(project):
    return project.registry


def _ask_id(question: str, registry) -> str | None:
    matched = match_ask(analyze(question, registry), registry)
    return None if matched is None else matched[0].id


def _quantities(result) -> set[tuple[str, str, float, str]]:
    return {
        (fact.entity, fact.measure, fact.value, fact.verb)
        for fact in result.store.by_kind(Quantity)
    }


def test_fridge_family_is_core_owned_bounded_and_not_quarantined(project) -> None:
    registry = project.registry

    assert registry.singular_to_plural["fridge"] == "fridges"
    assert registry.plural_to_singular["fridges"] == "fridge"
    assert registry.word_in_category("fridge", "quantity_interior_location")
    assert registry.word_in_category("fridge", "quantity_location")
    assert project.source_index.lexicon["fridge"].path.resolve() == CORE_LEXICON
    assert (
        project.source_index.category_members[
            ("quantity_interior_location", "fridge")
        ].path.resolve()
        == CORE_CATEGORIES
    )
    assert "fridge" not in project.packs[-1].lexicon
    assert {"fridge", "fridges"}.isdisjoint(registry.quarantine)


def test_strict_positive_fridge_location_ask_is_matched_and_generation_reachable(
    project,
) -> None:
    singular_question = "How many apples are in the fridge?"
    assert _ask_id(singular_question, project.registry) == "ask/how-many-in-place"

    candidate = generate_ask_scenario(
        project,
        ask_id="ask/how-many-in-place",
        seed=8162026,
        scenario_mode="ask_only",
        locked_bindings={
            "item": "apples",
            "verb": "are",
            "prep": "in",
            "place": "the fridge",
        },
    )

    assert candidate.question == singular_question
    assert candidate.target_ask == "ask/how-many-in-place"
    assert candidate.target_bindings["place"] == "fridge"


def test_existing_interior_location_is_an_equivalent_paraphrase(registry) -> None:
    fridge = solve(
        "Jora has 18 apples in the fridge. Jora ate 5 apples. "
        "Jora ate 4 apples. How many apples does Jora have?",
        registry,
    )
    pantry = solve(
        "Jora has 18 apples in the pantry. Jora ate 5 apples. "
        "Jora ate 4 apples. How many apples does Jora have?",
        registry,
    )

    assert (fridge.answer.kind, fridge.answer.value) == ("number", 9.0)
    assert (pantry.answer.kind, pantry.answer.value) == ("number", 9.0)
    assert _quantities(fridge) == _quantities(pantry)


def test_referential_noun_outside_interior_category_is_not_an_in_place_ask(
    registry,
) -> None:
    assert registry.word_in_category("bench", "quantity_location")
    assert not registry.word_in_category("bench", "quantity_interior_location")
    assert _ask_id("How many apples are in the bench?", registry) is None


def test_complete_named_holder_fold_uses_two_matching_decrements(registry) -> None:
    result = solve(
        "Jora has 18 apples in the fridge. Jora ate 5 apples. "
        "Jora ate 4 apples. How many apples does Jora have?",
        registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == 9.0
    assert result.answer.reason == "fold over 'jora'/'apple'"
    assert _quantities(result) == {
        ("jora", "apple", 18.0, "have"),
        ("jora", "apple", 5.0, "eat"),
        ("jora", "apple", 4.0, "eat"),
    }


def test_locative_phrase_does_not_rekey_person_quantity_to_fridge(registry) -> None:
    result = solve(
        "Jora has 18 apples in the fridge. "
        "How many apples are in the fridge?",
        registry,
    )

    assert _ask_id("How many apples are in the fridge?", registry) == (
        "ask/how-many-in-place"
    )
    assert _quantities(result) == {("jora", "apple", 18.0, "have")}
    assert result.answer.kind == "decline"
    assert not result.answer.committed


def test_named_holder_ask_does_not_borrow_the_fridge_locative_quantity(
    registry,
) -> None:
    result = solve(
        "Jora has 18 apples in the fridge. How many apples does Bira have?",
        registry,
    )

    assert _quantities(result) == {("jora", "apple", 18.0, "have")}
    assert result.answer.kind == "decline"
    assert not result.answer.committed
