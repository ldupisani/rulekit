"""Invented per-member chains, source completeness and interpretation boundaries."""

from itertools import permutations

import pytest
from pydantic import ValidationError

from rulekit.data.project import load_project
from rulekit.data.schemas import FactEmit
from rulekit.generation import generate_ask_scenario, generate_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantity, Rate


@pytest.fixture(scope="module", params=["curated", "gsm8k"])
def project(request):
    return load_project("projects/" + request.param)


CLAUSES = [
    "Each bird eats 7 apricots per week",
    "each snake eats 2 birds per week",
    "each jaguar eats 4 snakes per week",
]
QUESTION = "If there are 3 jaguars in a garden, how many apricots are eaten every week?"


def story():
    return CLAUSES[0] + ", " + CLAUSES[1] + ", and " + CLAUSES[2] + ". " + QUESTION


def test_three_coordinated_rates_and_conditional_population(project):
    result = solve(story(), project.registry)
    assert result.value == 168, result.answer
    assert not result.deficiencies()
    assert len(result.assumptions) == 1
    assert len(result.store.by_kind(Rate)) == 3
    assert all(r.provenance.distributive for r in result.store.by_kind(Rate))
    assert [(q.measure, q.value) for q in result.store.by_kind(Quantity)] == [("jaguar", 3)]
    assert "not inferred total populations" in result.answer.reason
    assert [a.id for a in result.answer.assumptions] == ["closed-quota-chain"]
    assert [dict(s.conclusion.fields)["value"] for s in result.answer.proof.steps] == [3, 12, 24, 168]
    assert len(result.answer.proof.steps[-1].evidence) == 4


@pytest.mark.parametrize("clauses", list(permutations(CLAUSES)))
def test_separate_sentences_and_any_rate_order(project, clauses):
    result = solve(". ".join(clauses) + ". " + QUESTION, project.registry)
    assert result.value == 168, result.answer


@pytest.mark.parametrize("marker", ["each", "every", "per"])
def test_period_markers_and_non_daily_period(project, marker):
    result = solve(story().replace("per week", marker + " week")
                   .replace("every week?", marker + " week?"), project.registry)
    assert result.value == 168, result.answer


def test_general_consumption_verb_reuses_category_roles(project):
    result = solve(story().replace("eats", "consumes").replace("eaten", "consumed"), project.registry)
    assert result.value == 168, result.answer


def test_two_link_and_single_link_chains(project):
    two = (CLAUSES[0] + " and " + CLAUSES[1] + ". "
           "There are 5 snakes in a forest. How many apricots are eaten each week?")
    assert solve(two, project.registry).value == 70
    one = (CLAUSES[0] + ". There are 5 birds in a forest. "
           "How many apricots are eaten each week?")
    assert solve(one, project.registry).value == 35


def test_zero_population(project):
    result = solve(story().replace("3 jaguars", "0 jaguars"), project.registry)
    assert result.value == 0, result.answer


def test_the_same_contract_supports_non_consumption_events(project):
    result = solve(
        "Each student drops 3 cards per day. There are 5 students in a university. "
        "How many cards are dropped every day?", project.registry,
    )
    assert result.value == 15, result.answer


def test_longer_chain_has_no_fixed_three_link_limit(project):
    result = solve(
        "Each jaguar eats 2 snakes per week. Each snake eats 3 birds per week. "
        "Each bird eats 4 beetles per week. Each beetle eats 5 apricots per week. "
        "There are 6 jaguars in a forest. How many apricots are eaten every week?",
        project.registry,
    )
    assert result.value == 720, result.answer
    assert len(result.answer.proof.steps) == 5


@pytest.mark.parametrize("old,new", [
    ("2 birds", "2.5 birds"),
    ("3 jaguars", "-3 jaguars"),
    ("3 jaguars", "3.5 jaguars"),
    ("7 apricots", "-7 apricots"),
    ("4 snakes per week", "4 snakes per day"),
    ("every week?", "every day?"),
    ("every week?", "every week yesterday?"),
    ("each snake eats", "each snake does not eat"),
    ("Each bird eats", "Each bird might eat"),
    ("Each bird eats", "The bird eats"),
    ("each snake eats", "each snake buys"),
    ("each snake", "each rabbit"),
    ("7 apricots", "7 pencils"),
    ("eaten every", "eaten by Dena every"),
    ("there are 3 jaguars", "there are 3 large jaguars"),
    ("there are 3 jaguars", "there were 3 jaguars yesterday"),
])
def test_incomplete_conflicting_or_qualified_chains_decline(project, old, new):
    result = solve(story().replace(old, new), project.registry)
    assert not result.answer.committed, result.answer


@pytest.mark.parametrize("extra", [
    "Each bird eats 7 apricots per week.",
    "Each bird eats 8 apricots per week.",
    "Each bird eats 3 cookies per week.",
    "There are 4 jaguars in a forest.",
    "There are 3 jaguars in a forest.",
    "There are 12 snakes in a garden.",
    "Cato has 7 apricots.",
    "Each rabbit eats 7 apricots per week.",
])
def test_no_source_statement_can_be_silently_ignored(project, extra):
    result = solve(story().replace("If there", extra + " If there"), project.registry)
    assert not result.answer.committed, result.answer


def test_cycle_declines(project):
    result = solve(
        "Each bird eats 2 fish per week. Each fish eats 3 birds per week. "
        "There are 4 birds in a forest. How many apricots are eaten every week?",
        project.registry,
    )
    assert not result.answer.committed, result.answer
    assert "cyclic" in result.answer.reason


def test_one_owned_location_keeps_its_identity_in_the_proof(project):
    result = solve(story().replace("in a garden", "in Dena's garden"), project.registry)
    assert result.value == 168, result.answer
    population = result.answer.proof.steps[0].evidence[0]
    assert population.entity_ref.owner.head == "dena"


def test_chain_cannot_assert_intermediate_population(project):
    text = story().replace("how many apricots are eaten every week?", "how many birds are in the garden?")
    assert not solve(text, project.registry).answer.committed


@pytest.mark.parametrize("rule", [
    "arithmetic/per-member-period-rate",
    "arithmetic/two-per-member-period-rates",
    "arithmetic/three-per-member-period-rates",
    "arithmetic/located-class-population",
])
def test_new_premise_shapes_generate_and_round_trip(project, rule):
    candidate = generate_candidate(project, rule_id=rule, seed=17)
    assert candidate.target_status == "matched", candidate.sentence


def test_distributive_provenance_is_a_declared_rate_contract():
    assert FactEmit(fact="rate", distributive=True).distributive
    with pytest.raises(ValidationError):
        FactEmit(fact="relation", distributive=True)


def test_passive_period_ask_generates_from_its_declared_contract(project):
    candidate = generate_ask_scenario(
        project, ask_id="ask/how-many-passive-per-period", seed=17,
        scenario_mode="ask_only",
    )
    assert candidate.target_ask == "ask/how-many-passive-per-period"
    assert candidate.query["consumer"] == "per-member-rate-chain"
    assert candidate.query["period"]
