"""Purpose-scoped savings goals with explicitly committed contributions.

These are invented structural neighbours, not benchmark prose.  They keep the
goal, current progress, and promised transfers as distinct fact kinds until a
purpose-qualified deficit ask deliberately combines them.
"""

from pathlib import Path

from rulekit.data.project import load_project
from rulekit.data.schemas import WherePredicate
from rulekit.generation import generate_candidate, list_rule_availability
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Contribution, Goal, Quantity


ROOT = Path(__file__).resolve().parents[1]
GSM8K = ROOT / "projects" / "gsm8k"
CURATED = ROOT / "projects" / "curated"

TEXT = (
    "Dena is saving money for new shoes which cost $600. "
    "Dena has half the money she needs. "
    "Her friend decided to give her $40, and her brother three times as "
    "much as her friend. "
    "How much more money does Dena need to buy the shoes?"
)


def _matched_rules(text: str, registry) -> set[str]:
    result = solve(text, registry)
    assert result.document is not None
    return {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


def test_same_surface_is_distinct_from_referent_lemma_agreement() -> None:
    predicate = WherePredicate(same_surface=["owner", "recipient"])

    assert predicate.same_surface == ["owner", "recipient"]
    assert predicate.same_lemma is None


def test_savings_goal_progress_and_contributions_answer_the_deficit() -> None:
    registry = load_project(GSM8K).registry
    result = solve(TEXT, registry)

    assert result.answer.kind == "number"
    assert result.answer.value == 140
    goals = list(result.store.by_kind(Goal))
    assert [
        (goal.entity, goal.measure, goal.value, goal.verb, goal.target)
        for goal in goals
    ] == [("dena", "dollar", 600, "save", "shoe")]
    holdings = list(result.store.by_kind(Quantity))
    assert [(q.entity, q.measure, q.value, q.verb) for q in holdings] == [
        ("dena", "dollar", 300, "have")
    ]
    assert not any(q.entity.startswith("$goal:") for q in holdings)
    assert {
        (fact.beneficiary, fact.contributor, fact.measure, fact.value)
        for fact in result.store.by_kind(Contribution)
    } == {
        ("dena", "friend", "dollar", 40),
        ("dena", "brother", "dollar", 120),
    }


def test_singular_goal_optional_of_and_purpose_reference_answer_in_curated() -> None:
    registry = load_project(CURATED).registry
    text = (
        "Aven is raising money for a new wallet which costs $300. "
        "Aven has one third of the money she needs. "
        "Her grandparents decided to give her $20 for that purpose, and her "
        "parents twice as much as her grandparents. "
        "How much more money does Aven need to buy the wallet?"
    )
    result = solve(text, registry)

    assert result.answer.kind == "number"
    assert result.answer.value == 140
    assert [
        (goal.entity, goal.measure, goal.value, goal.verb, goal.target)
        for goal in result.store.by_kind(Goal)
    ] == [("aven", "dollar", 300, "raise", "wallet")]
    assert [
        (quantity.entity, quantity.measure, quantity.value, quantity.verb)
        for quantity in result.store.by_kind(Quantity)
    ] == [("aven", "dollar", 100, "have")]
    assert {
        (fact.beneficiary, fact.contributor, fact.measure, fact.value)
        for fact in result.store.by_kind(Contribution)
    } == {
        ("aven", "grandparent", "dollar", 20),
        ("aven", "parent", "dollar", 40),
    }
    assert not result.deficiencies()


def test_contribution_purpose_reference_rejects_an_unlicensed_object() -> None:
    registry = load_project(CURATED).registry
    text = (
        "Her grandparents decided to give her $20 for that garden, and her "
        "parents twice as much as her grandparents."
    )
    result = solve(text, registry)

    assert "arithmetic/committed-transfer-conjoined-relative" not in (
        _matched_rules(text, registry)
    )
    assert list(result.store.by_kind(Contribution)) == []


def test_contribution_coordination_requires_repeated_pronoun_surface() -> None:
    registry = load_project(GSM8K).registry
    text = (
        "Her friend decided to give her $40, and his brother three times "
        "as much as her friend."
    )
    result = solve(text, registry)

    assert "arithmetic/committed-transfer-conjoined-relative" not in (
        _matched_rules(text, registry)
    )
    assert list(result.store.by_kind(Contribution)) == []


def test_purpose_qualified_deficit_does_not_borrow_another_target() -> None:
    registry = load_project(GSM8K).registry
    text = TEXT.replace("buy the shoes?", "buy the businesses?")
    result = solve(text, registry)

    assert result.answer.kind == "decline"
    assert "0 goal facts" in result.answer.reason


def test_singular_goal_target_strictly_generates_and_round_trips() -> None:
    project = load_project(CURATED)
    candidate = generate_candidate(
        project,
        rule_id="arithmetic/savings-goal-priced-target",
        seed=7412,
        locked_bindings={
            "who": "Aven",
            "aux": "is",
            "save": "raising",
            "measure": "money",
            "target": "wallet",
            "cost": "costs",
            "amount": "$90",
        },
    )

    assert candidate.target_status in {"matched", "shadowed"}
    assert candidate.target_bindings["target"] == "wallet"
    assert "arithmetic/savings-goal-priced-target" in _matched_rules(
        candidate.sentence, project.registry
    )


def test_new_premise_rules_are_available_and_round_trip() -> None:
    project = load_project(GSM8K)
    rule_ids = {
        "arithmetic/savings-goal-priced-target",
        "arithmetic/goal-progress-fraction-needed",
        "arithmetic/committed-transfer-conjoined-relative",
    }
    availability = {
        item.id: item for item in list_rule_availability(project)
        if item.id in rule_ids
    }

    assert set(availability) == rule_ids
    assert all(item.supported for item in availability.values())
    for seed, rule_id in enumerate(sorted(rule_ids), start=170):
        candidate = generate_candidate(project, rule_id=rule_id, seed=seed)
        assert candidate.target_rule == rule_id
        assert candidate.target_status in {"matched", "shadowed"}
        assert rule_id in _matched_rules(candidate.sentence, project.registry)
