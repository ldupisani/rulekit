"""Reviewed role mistakes and scope-safe location questions; invented neighbours."""

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.generation.ask_generation import generate_ask_scenario
from rulekit.generation.sample import retest_candidate
from rulekit.kernel.engine import analyze, solve
from rulekit.kernel.patterns import match_ask


@pytest.fixture(scope="module")
def project():
    return load_project("projects/curated")


@pytest.mark.parametrize("rule,text", [
    ("arithmetic/as-many", "The box put as many coats as the hunger."),
    ("arithmetic/times-as-many-possessive-kinship-standard",
     "The librarian wrote twice as many toys on friday as your teacher."),
    ("arithmetic/group-total-leading", "In total shopping read 18 pages."),
    ("arithmetic/group-total-leading-marker", "Together shopping read 18 pages."),
    ("arithmetic/group-total-leading", "In total the boxes read 18 pages."),
    ("arithmetic/group-total-leading-marker", "Together the boxes read 18 pages."),
    ("arithmetic/times-the-number-of", "Energy had twice the amount of seas as my student Aven."),
    ("arithmetic/container-capacity-checking-inquiry-frame",
     "The cost is checking to know how many balls should go in the cupboard."),
    ("arithmetic/container-capacity-assessment-frame", "The cost is studying the capacity of a jar."),
    ("arithmetic/container-capacity-progressive-inquiry-frame",
     "The cost is wondering how many balls she can fit in a jar."),
])
def test_invalid_roles_do_not_match(project, rule, text):
    result = solve(text, project.registry)
    assert rule not in {
        match.match.rule.id
        for matches in result.document.rule_results.values() for match in matches
    }


@pytest.mark.parametrize("text", [
    "The librarian wrote twice as many books as your teacher.",
    "The librarian wrote twice as many pages as your teacher.",
    "The librarian wrote twice as many letters as your teacher.",
    "The librarian made twice as many toys as your teacher.",
    "In total the librarian read 18 pages.",
    "Together they sold 18 coats.",
    "Total blue has 18 birds.",
    "The teacher is checking to know how many balls can go in the cupboard.",
    "The teacher is studying the capacity of a jar.",
    "The garden has twice the number of flowers as the university.",
])
def test_compatible_neighbours_keep_their_premises(project, text):
    result = solve(text, project.registry)
    assert any(result.document.rule_results.values()), text


@pytest.mark.parametrize("question", [
    "How many marbles are there into Mira's bowl?",
    "How many marbles are into Mira's bowl?",
    "How many marbles are into the bowl?",
])
def test_static_asks_do_not_bind_directional_prepositions(project, question):
    assert match_ask(analyze(question, project.registry), project.registry) is None


@pytest.mark.parametrize("premise", [
    "A small bowl has 7 marbles.",
    "A small bowl has 7 marbles. Mira has a large bowl.",
    "Cato's bowl has 7 marbles.",
    "Mira has 7 marbles.",
])
def test_possessed_location_needs_exact_instance_evidence(project, premise):
    result = solve(premise + " How many marbles are there in Mira's bowl?", project.registry)
    assert not result.answer.committed


@pytest.mark.parametrize("question", [
    "How many marbles are there in Mira's bowl?",
    "How many marbles are in Mira's bowl?",
])
def test_exact_possessed_location_still_answers(project, question):
    assert solve("Mira's bowl has 7 marbles. " + question, project.registry).value == 7


def test_owner_and_size_are_intersected_not_alternative_scopes(project):
    result = solve("Mira's small bowl has 7 marbles. "
                   "How many marbles are there in Mira's large bowl?", project.registry)
    assert not result.answer.committed


def test_colour_partition_keeps_its_specific_ask(project):
    reading = analyze("How many violet balls are in the bowl?", project.registry)
    assert match_ask(reading, project.registry)[0].id == "ask/how-many-attribute-partition-in-place"


def test_colour_subset_never_borrows_another_colour(project):
    result = solve("There is a total of 17 balls. There are 12 red balls. "
                   "How many green balls are in the bowl?", project.registry)
    assert result.value != 12


@pytest.mark.parametrize("question", [
    "How many green balls are there in Mira's bowl?",
    "How many green balls are in Mira's bowl?",
    "How many green balls does Mira have in her bowl?",
    "How many green balls were in the bowl yesterday?",
])
def test_qualified_location_never_drops_the_content_attribute(project, question):
    result = solve("Mira's bowl had 7 red balls yesterday. " + question, project.registry)
    assert not result.answer.committed


def test_explicit_subject_owned_location_retains_its_holder_path(project):
    result = solve("Mira has 7 fish. "
                   "How many fish does Mira have in her jar?", project.registry)
    assert result.value == 7


@pytest.mark.parametrize("question", [
    "How many marbles were there in Mira's bowl yesterday?",
    "How many marbles were in Mira's bowl yesterday?",
    "How many marbles are in the bowl today?",
])
def test_explicit_time_cannot_use_untimed_location_evidence(project, question):
    assert not solve("Mira's bowl has 7 marbles. " + question, project.registry).answer.committed


@pytest.mark.parametrize("marker,expected", [("yesterday", 7), ("today", None)])
def test_location_time_matches_existing_event_time_evidence(project, marker, expected):
    result = solve(
        "Mira's bowl had 7 marbles yesterday. "
        f"How many marbles were there in Mira's bowl {marker}?", project.registry,
    )
    assert result.value == expected


def test_valid_existential_has_no_false_subject_warning(project):
    candidate = retest_candidate(project, rule_id="arithmetic/existential-premise-bare-conjoined",
        sentence="There was 1 goodie and 40 marbles.", seed=0)
    assert candidate.target_status == "matched"
    assert not candidate.deficiencies


@pytest.mark.parametrize("rule,bindings", [
    ("arithmetic/times-as-many-possessive-kinship-standard", {"verb": "wrote"}),
    ("arithmetic/group-total-leading", {"verb": "read"}),
    ("arithmetic/container-capacity-checking-inquiry-frame", {}),
    ("arithmetic/container-capacity-assessment-frame", {}),
])
def test_strict_generation_round_trips_role_contracts(project, rule, bindings):
    candidate = generate_candidate(project, rule_id=rule, seed=91, locked_bindings=bindings)
    assert candidate.target_status == "matched"


def test_answerable_possessed_location_generates_actual_owner_evidence(project):
    candidate = generate_ask_scenario(project,
        ask_id="ask/how-many-there-in-possessed-place", scenario_mode="answerable",
        seed=91, locked_bindings={"place": "Dena's bowl", "item": "marbles", "verb": "are"})
    assert candidate.answer["committed"]
    assert "dena" in candidate.text.casefold()
    assert "small bowl" not in candidate.text.casefold()
