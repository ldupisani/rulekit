"""Invented paraphrases and scope boundaries for item-class comparisons."""

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import CollectionAttribute


@pytest.fixture(scope="module")
def project():
    return load_project("projects/curated")


BASE = ("Cato bought 14 flower cards. He bought 6 more truck cards than flower cards, "
        "and 8 fewer rose cards than truck cards. ")
ASK = "How many cards did Cato buy in all?"


@pytest.mark.parametrize("question", [
    "What is the total number of cards Cato bought?",
    "What is the total number of cards that Cato bought?",
    "How many cards did he buy in all?",
    "How many cards did he buy altogether?",
    "How many cards did he buy in total?",
    "How many cards did he buy combined?",
])
def test_single_holder_total_paraphrases(project, question):
    assert solve(BASE + question, project.registry).value == 46


@pytest.mark.parametrize("tail", ["Cato bought", "that Cato bought"])
def test_named_total_never_enumerates_other_holders(project, tail):
    result = solve(BASE + "Dena bought 100 cards. What is the total number of cards "
                   + tail + "?", project.registry)
    assert result.value == 46, result.answer


@pytest.mark.parametrize("question", [
    "What is the total number of cards Cato sold?",
    "What is the total number of cards Dena bought?",
    "What is the total number of cards that Cato bought tomorrow?",
])
def test_total_keeps_predicate_holder_and_temporal_constraints(project, question):
    assert not solve(BASE + question, project.registry).answer.committed


@pytest.mark.parametrize("qualifier,expected", [("flower", 14), ("truck", 20), ("rose", 12)])
def test_scene_setting_does_not_block_known_subtype(project, qualifier, expected):
    result = solve("Cato bought cards at the post office. " + BASE
                   + f"How many {qualifier} cards did Cato buy?", project.registry)
    assert result.value == expected, result.answer


@pytest.mark.parametrize("extra", [
    "Cato bought some cards at the post office. ",
    "Cato bought cards. ",
    "Cato bought 3 cards at the post office. ",
])
def test_unknown_additional_events_still_block_subtype(project, extra):
    assert not solve(BASE + extra + "How many truck cards did Cato buy?",
                     project.registry).answer.committed


@pytest.mark.parametrize("comparison", [
    "He bought 6 more truck cards than he bought flower cards. He bought 8 fewer rose cards than he bought truck cards. ",
    "He bought 6 more truck cards than he bought flower cards, and 8 fewer rose cards than he bought truck cards. ",
])
def test_expanded_comparison_clauses(project, comparison):
    result = solve("Cato bought 14 flower cards. " + comparison + ASK, project.registry)
    assert result.value == 46, result.answer


def test_initial_count_and_comparisons_in_one_sentence(project):
    result = solve("Cato bought 14 flower cards, 6 more truck cards than flower cards, "
                   "and 8 fewer rose cards than truck cards. " + ASK, project.registry)
    assert result.value == 46, result.answer


@pytest.mark.parametrize("replacement", ["Dena bought", "he sold"])
def test_expanded_clause_does_not_erase_changed_participant_or_verb(project, replacement):
    result = solve("Cato bought 14 flower cards. He bought 6 more truck cards than "
                   + replacement + " flower cards. " + ASK, project.registry)
    assert not result.answer.committed, result.answer


def test_elided_object_after_standard_verb_keeps_existing_holder_relation(project):
    result = solve("Cato has 18 cards. His brother has 4 fewer cards than he has. "
                   "How many cards do they have combined?", project.registry)
    assert result.value == 32, result.answer


@pytest.mark.parametrize("designs", ["flower and truck", "flower, truck, and rose",
                                    "flower, truck, rose, and tree"])
def test_coordinated_nominal_descriptions_preserve_every_member(project, designs):
    result = solve("The cards had " + designs + " designs.", project.registry)
    expected = set(designs.replace(",", "").split()) - {"and"}
    assert {f.qualifier for f in result.store.by_kind(CollectionAttribute)} == expected


def test_unknown_fourth_design_cannot_disappear(project):
    result = solve("The cards had flower, truck, rose, and tree designs. " + BASE + ASK,
                   project.registry)
    assert not result.answer.committed, result.answer


def test_longer_unsupported_description_list_cannot_disappear(project):
    result = solve("The cards had flower, truck, rose, tree, and snowflake designs. "
                   + BASE + ASK, project.registry)
    assert not result.answer.committed, result.answer


@pytest.mark.parametrize("extra", ["Cato bought cards. ", "Cato bought cards at the post office. "])
def test_later_unknown_event_is_not_an_introductory_summary(project, extra):
    result = solve("Cato bought cards at the post office. " + BASE + extra
                   + "How many truck cards did Cato buy?", project.registry)
    assert not result.answer.committed, result.answer


def test_counted_design_list_is_answerable(project):
    result = solve("The cards had flower, truck, and rose designs. " + BASE + ASK,
                   project.registry)
    assert result.value == 46, result.answer


@pytest.mark.parametrize("attribute", ["design", "pattern"])
def test_postnominal_description_uses_same_item_identity(project, attribute):
    text = (f"Cato bought 14 cards with a flower {attribute}. "
            f"He bought 6 more cards with a truck {attribute} than cards with a flower {attribute}, "
            f"and 8 fewer cards with a rose {attribute} than cards with a truck {attribute}. ")
    assert solve(text + ASK, project.registry).value == 46
    assert solve(text + f"How many cards with a truck {attribute} did Cato buy?",
                 project.registry).value == 20


def test_pre_and_post_nominal_forms_interoperate(project):
    result = solve(BASE.replace("14 flower cards", "14 cards with a flower design") + ASK,
                   project.registry)
    assert result.value == 46, result.answer


@pytest.mark.parametrize("rule", [
    "arithmetic/qualified-item-comparison-clause",
    "arithmetic/located-quantity-event-context",
    "arithmetic/anchored-qualified-item-comparison-pair",
    "arithmetic/collection-two-shared-attributes",
    "arithmetic/collection-three-shared-attributes",
    "arithmetic/collection-four-shared-attributes",
])
def test_new_premise_shapes_generate_and_round_trip(project, rule):
    assert generate_candidate(project, rule_id=rule, seed=17).target_status == "matched"
