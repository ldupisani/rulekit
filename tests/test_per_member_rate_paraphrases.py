"""Invented paraphrases of explicit per-member dependency calculations."""

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate, generate_ask_scenario
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantity


@pytest.fixture(scope="module", params=["curated", "gsm8k"])
def project(request):
    return load_project("projects/" + request.param)


CLAUSES = ["Each bird eats 7 apricots per day", "each snake eats 2 birds per day",
           "each jaguar eats 4 snakes per day"]
RATES = ". ".join(CLAUSES) + ". "
POPULATION = "There are 3 jaguars in a garden. "
ASK = "How many apricots are eaten each day?"


@pytest.mark.parametrize("question,value", [
    ("How many apricots do the birds eat in one day?", 168),
    ("How many apricots do the birds eat in 2 days?", 336),
    ("How many birds do the snakes eat in one day?", 24),
    ("How many apricots does a bird eat in one day?", 7),
    ("How many snakes do the jaguars eat in one day?", 12),
    ("How many apricots are eaten in 2 days?", 336),
    ("How many apricots are eaten in one week?", 1176),
    ("How many apricots are eaten a day?", 168),
    ("How many apricots are eaten daily?", 168),
    ("How many apricots are eaten in a day?", 168),
    ("How many apricots are eaten in total each day?", 168),
    ("How many apricots are eaten each day altogether?", 168),
    ("What is the total number of apricots eaten each day?", 168),
    ("How many apricots do the birds eat each day?", 168),
    ("How many apricots does a bird eat each day?", 7),
    ("How many apricots do all the birds eat each day?", 168),
    ("How many apricots do the birds eat daily?", 168),
    ("How many apricots do the birds eat in a day?", 168),
    ("How many apricots are eaten in the garden each day?", 168),
    ("How many apricots are eaten each day in the garden?", 168),
    ("How many apricots will be eaten each day?", 168),
    ("Each day, how many apricots are eaten?", 168),
    ("How many snakes are eaten each day?", 12),
    ("How many birds are eaten each day?", 24),
])
def test_scoped_asks_and_duration(project, question, value):
    result = solve(RATES + POPULATION + question, project.registry)
    assert result.value == value, result.answer
    assert len(result.store.by_kind(Quantity)) == 1
    assert result.answer.proof


@pytest.mark.parametrize("rates", [
    RATES.replace("per day", "a day"),
    RATES.replace("per day", "daily"),
    "; ".join(CLAUSES) + ". ",
    " and ".join(CLAUSES) + ". ",
    ", ".join(CLAUSES[:2]) + " and " + CLAUSES[2] + ". ",
    CLAUSES[0].replace("per day", "") + " and " + CLAUSES[1] + ". " + CLAUSES[2] + ". ",
    ", ".join(c.replace(" per day", "") for c in CLAUSES[:2]) + " and " + CLAUSES[2] + ". ",
    "Every day, " + ", ".join(c.replace(" per day", "") for c in CLAUSES[:2]) + " and " + CLAUSES[2].replace(" per day", "") + ". ",
    "Every day, each bird eats 7 apricots. " + ". ".join(CLAUSES[1:]) + ". ",
    "Every day, each bird eats 7 apricots and each snake eats 2 birds. " + CLAUSES[2] + ". ",
    " and ".join(c.replace("per day", "daily") for c in CLAUSES) + ". ",
    RATES.replace("Each bird", "A bird").replace("each snake", "A snake").replace("each jaguar", "A jaguar"),
    RATES.replace("snake eats", "snake consumes"),
    "Birds each eat 7 apricots per day. Snakes each eat 2 birds per day. Jaguars each eat 4 snakes per day. ",
    "Seven apricots are eaten by each bird per day. Two birds are eaten by each snake per day. Four snakes are eaten by each jaguar per day. ",
])
def test_rate_phrasings(project, rates):
    result = solve(rates + POPULATION + ASK, project.registry)
    assert result.value == 168, (result.answer, rates)


@pytest.mark.parametrize("population", [
    "The garden contains 3 jaguars. ",
    "A garden has 3 jaguars. ",
    "Three jaguars live in a garden. ",
    "In a garden, there are 3 jaguars. ",
])
def test_population_phrasings(project, population):
    result = solve(RATES + population + ASK, project.registry)
    assert result.value == 168, result.answer


@pytest.mark.parametrize("question", [
    "How many apricots do the snakes eat in one day?",
    "How many apricots do the large birds eat in one day?",
    "How many apricots do Dena's birds eat in one day?",
    "How many large apricots do the birds eat in one day?",
    "How many apricots are eaten in 1.5 days?",
    "How many apricots are eaten in one hour?",
    "How many apricots are eaten in the forest each day?",
    "How many apricots are eaten near the garden each day?",
    "How many apricots are eaten outside the garden each day?",
    "How many apricots do all a bird eat each day?",
    "How many apricots are eaten in the garden each day in the forest?",
    "How many apricots are eaten each day yesterday?",
    "How many apricots are eaten each day except today?",
    "How many apricots are eaten in combined each day?",
    "How many apricots are eaten in all?",
])
def test_restrictions_are_not_erased(project, question):
    result = solve(RATES + POPULATION + question, project.registry)
    assert not result.answer.committed, result.answer


@pytest.mark.parametrize("replacement", ["Birds eat", "The birds eat", "Some birds eat"])
def test_bare_plural_rates_do_not_invent_per_member_distributivity(project, replacement):
    result = solve(RATES.replace("Each bird eats", replacement) + POPULATION + ASK,
                   project.registry)
    assert not result.answer.committed, result.answer


def test_plural_without_population_cannot_default_to_one(project):
    result = solve(CLAUSES[0] + ". How many apricots do the birds eat in one day?",
                   project.registry)
    assert not result.answer.committed, result.answer
    single = solve(CLAUSES[0] + ". How many apricots does a bird eat in one day?",
                   project.registry)
    assert single.value == 7, single.answer


def test_partial_chain_proof_accounts_for_unused_downstream_rates(project):
    result = solve(RATES + POPULATION + "How many snakes are eaten each day?", project.registry)
    assert result.value == 12
    omitted = [step for step in result.answer.proof.steps if step.rule == "outside-requested-subgraph"]
    assert len(omitted) == 1
    assert len(omitted[0].evidence) == 2


def test_duration_scales_complete_chain_once(project):
    result = solve(RATES + POPULATION + "How many apricots are eaten in 2 days?", project.registry)
    assert result.value == 336
    assert sum(s.rule == "scale-complete-period-once" for s in result.answer.proof.steps) == 1


def test_ordinary_non_distributive_rate_plural_also_needs_population(project):
    text = "A bird eats 7 apricots per day. How many apricots do the birds eat in 2 days?"
    assert not solve(text, project.registry).answer.committed


def test_nearby_population_cannot_answer_an_inside_ask(project):
    result = solve(RATES + POPULATION.replace("in a garden", "near a garden")
                   + "How many apricots are eaten in the garden each day?", project.registry)
    assert not result.answer.committed, result.answer


@pytest.mark.parametrize("subject", ["Dena's birds", "her birds"])
def test_owned_plural_uses_only_the_matching_explicit_population(project, subject):
    text = ("A bird eats 7 apricots per day. Dena has 5 birds. "
            f"How many apricots do {subject} eat in 4 days?")
    result = solve(text, project.registry)
    assert result.value == 140, result.answer
    other = solve(text.replace(subject + " eat", "Cato's birds eat"), project.registry)
    assert not other.answer.committed, other.answer


def test_owned_plural_does_not_sum_another_holders_population(project):
    text = ("A bird eats 7 apricots per day. Dena has 5 birds. Cato has 3 birds. "
            "How many apricots do Dena's birds eat in 4 days?")
    assert solve(text, project.registry).value == 140


def test_ask_generation_requires_the_declared_role_frame(project):
    from rulekit.generation.ask_generation import _ask_filler_satisfies_known_where
    from rulekit.generation.sample import _Filler

    ask = next(a for a in project.registry.asks if a.id == "ask/how-many-active-per-period")
    assert not _ask_filler_satisfies_known_where(
        project, ask, "verb", _Filler("zorp", "zorp", kind="verb"), {},
    )


@pytest.mark.parametrize("rule", [
    "fronted-located-class-population", "location-contains-population",
    "resident-class-population", "indefinite-member-period-rate",
    "postposed-member-period-rate", "passive-per-member-period-rate",
    "per-member-daily-rates", "two-per-member-daily-rates", "three-per-member-daily-rates",
    "two-per-member-shared-period-rates", "three-per-member-shared-period-rates",
    "per-member-fronted-period-rates", "two-per-member-fronted-period-rates",
    "three-per-member-fronted-period-rates",
])
def test_paraphrase_premises_generate(project, rule):
    candidate = generate_candidate(project, rule_id="arithmetic/" + rule, seed=17)
    assert candidate.target_status == "matched", candidate.sentence


@pytest.mark.parametrize("ask", [
    "how-many-passive-period-span", "how-many-passive-daily",
    "how-many-passive-one-period-span", "how-many-active-per-period",
    "how-many-active-daily", "how-many-active-one-period-span",
    "how-many-future-passive-per-period", "how-many-fronted-per-period",
    "total-number-passive-per-period",
])
def test_paraphrase_asks_generate(project, ask):
    candidate = generate_ask_scenario(project, ask_id="ask/" + ask, seed=17,
                                      scenario_mode="ask_only")
    assert candidate.target_ask == "ask/" + ask
    assert candidate.query["consumer"] == "per-member-rate-chain"
