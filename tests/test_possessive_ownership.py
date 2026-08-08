"""Owner-qualified common nouns in quantities, relations, and asks."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.project import load_project
from rulekit.data.registry import compile_registry
from rulekit.generation import generate_candidate, list_rule_availability
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantity, Relation


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def full_registry():
    return compile_registry(
        load_packs(
            [
                ROOT / "packs/core-english",
                ROOT / "packs/arithmetic",
                ROOT / "packs/difg-mined",
            ]
        )
    )


@pytest.mark.parametrize("determiner", ["her", "his", "their"])
def test_possessive_determiner_age_standard_emits_owned_relation(
    determiner: str, full_registry
) -> None:
    result = solve(
        f"The teacher is 6 years older than {determiner} child.",
        full_registry,
    )

    relations = result.store.by_kind(Relation)
    assert len(relations) == 1
    assert relations[0].provenance.source == (
        "arithmetic/anchored-relation-postfix-age-possessive-standard"
    )
    assert relations[0].standard == "child"
    assert relations[0].standard_owner == "teacher"


def test_possessive_determiner_owner_reaches_folded_quantity(
    full_registry,
) -> None:
    result = solve("Her child is 10 years old.", full_registry)

    ages = [
        fact
        for fact in result.store.by_kind(Quantity)
        if fact.entity == "child" and fact.measure == "year"
    ]
    assert len(ages) == 1
    assert ages[0].value == 10
    assert ages[0].owner == "her"


@pytest.mark.parametrize("other_age", [10, 12])
def test_owned_age_relation_uses_exact_possessor(
    other_age: int, full_registry
) -> None:
    result = solve(
        "Mary's child is 10 years old. "
        f"John's child is {other_age} years old. "
        "Cato is 6 years older than Mary's child. How old is Cato?",
        full_registry,
    )

    assert result.answer.value == 16
    ages = {
        (fact.entity, fact.owner): fact.value
        for fact in result.store.by_kind(Quantity)
        if fact.measure == "year" and fact.owner
    }
    assert ages[("child[mary]", "mary")] == 10
    assert ages[("child[john]", "john")] == other_age


def test_owned_relation_never_borrows_another_possessors_quantity(
    full_registry,
) -> None:
    result = solve(
        "Mary's child is 10 years old. John's child is 12 years old. "
        "Cato is 6 years older than Pat's child. How old is Cato?",
        full_registry,
    )

    assert not result.answer.committed


def test_clause_local_possessive_owner_joins_explicit_possession(
    full_registry,
) -> None:
    result = solve(
        "Cato's child is 10 years old. "
        "Cato is 6 years older than his child. How old is Cato?",
        full_registry,
    )

    assert result.answer.value == 16
    relation = result.store.by_kind(Relation)[0]
    assert relation.standard_owner == "cato"


def test_unique_discourse_antecedent_resolves_the_owner(full_registry) -> None:
    result = solve(
        "Mary has 1 apple. Her child is 10 years old. "
        "How old is Mary's child?",
        full_registry,
    )

    assert result.answer.value == 10
    age = next(
        fact
        for fact in result.store.by_kind(Quantity)
        if fact.measure == "year"
    )
    assert age.owner == "mary"


@pytest.mark.parametrize(
    ("premise", "question"),
    [
        ("Mary's child is 10 years old.", "How old is Mary's child?"),
        ("Her child is 10 years old.", "How old is her child?"),
    ],
)
def test_possessed_age_ask_queries_exact_owner(
    premise: str, question: str, full_registry
) -> None:
    result = solve(f"{premise} {question}", full_registry)

    assert result.answer.value == 10


def test_possessive_age_rule_is_strictly_generatable() -> None:
    project = load_project(ROOT / "projects/curated")
    rule_id = (
        "arithmetic/anchored-relation-postfix-age-possessive-standard"
    )
    availability = {
        item.id: item for item in list_rule_availability(project)
    }
    candidate = generate_candidate(project, rule_id=rule_id, seed=0)

    assert availability[rule_id].supported
    assert candidate.target_status == "matched"
    assert next(
        row.binding for row in candidate.premises if row.slot == "std_det"
    )
