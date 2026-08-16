"""Vocabulary-independent goal constructions and their inference boundary."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Goal, Quantity, Relation


PROJECT = Path(__file__).resolve().parents[1] / "projects" / "curated"


@pytest.fixture(scope="module")
def project():
    return load_project(PROJECT)


@pytest.mark.parametrize(
    ("premise_predicate", "ask_predicate"),
    [("needs", "need"), ("requires", "require")],
)
def test_direct_quantity_predicates_share_one_goal_contract(
    project, premise_predicate: str, ask_predicate: str
) -> None:
    result = solve(
        f"Dena {premise_predicate} 30 books. Dena has 12 books. "
        f"How many more books does Dena {ask_predicate}?",
        project.registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == 18
    assert [(goal.entity, goal.measure, goal.value) for goal in result.store.by_kind(Goal)] == [
        ("dena", "book", 30)
    ]


@pytest.mark.parametrize("predicate", ["wants", "hopes", "intends"])
def test_infinitival_predicates_normalize_to_the_same_goal(
    project, predicate: str
) -> None:
    result = solve(
        f"Dena {predicate} to buy 30 books. Dena has 12 books. "
        "How many more books does Dena require?",
        project.registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == 18
    goals = list(result.store.by_kind(Goal))
    assert [(goal.entity, goal.measure, goal.value) for goal in goals] == [
        ("dena", "book", 30)
    ]


def test_goal_predicate_never_changes_the_ordinary_holding(project) -> None:
    result = solve(
        "Dena hopes to buy 30 books. Dena has 12 books. "
        "How many books does Dena have?",
        project.registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == 12


@pytest.mark.parametrize("activity", ["saving", "raising"])
def test_priced_purpose_activities_share_one_targeted_goal(
    project, activity: str
) -> None:
    result = solve(
        f"Dena is {activity} money for new shoes which cost $600. "
        "Dena has $250. How much more money does Dena require to buy the shoes?",
        project.registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == 350
    goals = list(result.store.by_kind(Goal))
    assert [
        (goal.entity, goal.measure, goal.value, goal.target) for goal in goals
    ] == [("dena", "dollar", 600, "shoe")]


def test_comparative_goal_anchors_only_on_another_goal(project) -> None:
    result = solve(
        "Cato needs 30 pencils. Fia requires 5 fewer pencils than Cato. "
        "Fia has 10 pencils. How many more pencils does Fia require?",
        project.registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == 15
    assert {
        (goal.entity, goal.measure, goal.value)
        for goal in result.store.by_kind(Goal)
    } == {("cato", "pencil", 30), ("fia", "pencil", 25)}
    relation = next(iter(result.store.by_kind(Relation)))
    assert relation.verb == "require"
    assert not any(
        quantity.provenance.source == "synth/relation"
        and quantity.entity == "fia"
        for quantity in result.store.by_kind(Quantity)
    )


def test_comparative_goal_does_not_borrow_an_actual_holding(project) -> None:
    result = solve(
        "Cato has 30 pencils. Fia requires 5 fewer pencils than Cato. "
        "Fia has 10 pencils. How many more pencils does Fia require?",
        project.registry,
    )

    assert result.answer.kind == "decline"
    assert not result.store.by_kind(Goal)
    assert not any(
        quantity.provenance.source == "synth/relation"
        and quantity.entity == "fia"
        for quantity in result.store.by_kind(Quantity)
    )


@pytest.mark.parametrize(
    "text",
    [
        "Dena received 30 books. Dena has 12 books. "
        "How many more books does Dena require?",
        "Dena raised $100. Dena has $20. "
        "How much more money does Dena require to buy the shoes?",
    ],
)
def test_actual_events_do_not_invent_goals(project, text: str) -> None:
    result = solve(text, project.registry)

    assert result.answer.kind == "decline"
    assert not result.store.by_kind(Goal)


@pytest.mark.parametrize(
    ("rule_id", "bindings"),
    [
        (
            "arithmetic/goal-desire-quantity",
            {"who": "Dena", "want": "hopes", "verb": "buy", "item": "30 books"},
        ),
        (
            "arithmetic/goal-need-quantity",
            {"who": "Dena", "need": "requires", "item": "30 books"},
        ),
        (
            "arithmetic/goal-need-comparative-quantity",
            {
                "who": "Dena",
                "need": "requires",
                "n": "5",
                "dir": "fewer",
                "item": "books",
                "std": "Cato",
            },
        ),
        (
            "arithmetic/savings-goal-priced-target",
            {
                "who": "Dena",
                "aux": "is",
                "save": "raising",
                "measure": "money",
                "target": "shoes",
                "cost": "cost",
                "amount": "$90",
            },
        ),
    ],
)
def test_generic_goal_vocabulary_round_trips_through_generation(
    project, rule_id: str, bindings: dict[str, str]
) -> None:
    candidate = generate_candidate(
        project,
        rule_id=rule_id,
        seed=7411,
        locked_bindings=bindings,
    )

    assert candidate.target_status in {"matched", "shadowed"}
    assert any(fact["type"] in {"Goal", "Relation"} for fact in candidate.facts)
