"""Complete matched constructions account for grammar, never missing evidence."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import retest_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import GroupTotal, Quantity, Relation
from rulekit.kernel.patterns import match_ask


@pytest.fixture(scope="module")
def project():
    return load_project(Path("projects/curated"))


@pytest.mark.parametrize("question", [
    "How old is Dena?", "How old are Dena?", "How many years old is Dena?",
])
def test_inverted_age_subject_is_complete_without_changing_temporal_scope(
    project, question
):
    result = solve(
        f"In 4 more years Dena would be 24 years old. {question}",
        project.registry,
    )

    assert result.answer.committed
    assert result.value == 20
    assert result.deficiencies() == []


def test_inverted_past_subject_does_not_invent_a_past_age(project):
    result = solve(
        "In 4 more years Dena would be 24 years old. How old was Dena?",
        project.registry,
    )

    assert not result.answer.committed
    assert result.deficiencies() == []


@pytest.mark.parametrize("holder", ["Fia", "the rabbit"])
def test_inverted_dated_age_has_a_subject_and_calendar_coordinate(project, holder):
    result = solve(
        f"{holder} was 12 years old in 2000. How old was {holder} in 2006?",
        project.registry,
    )

    assert result.answer.committed
    assert result.value == 18
    assert result.deficiencies() == []


@pytest.mark.parametrize("item", ["cookies", "books"])
def test_possessed_number_question_accounts_for_its_copula(project, item):
    result = solve(
        f"Fia had 6 {item}. What is the number of Fia's {item}?",
        project.registry,
    )

    assert result.answer.committed
    assert result.value == 6
    assert result.deficiencies() == []


@pytest.mark.parametrize("premises,item,expected", [
    ("Dena has $8. Fia has $4. Cato has $100.", "money", 12),
    ("Dena has 8 liters of water. Fia has 4 liters of water. Cato has 100 liters of water.", "water", None),
])
@pytest.mark.parametrize("marker", ["together", "in total"])
def test_named_mass_subject_keeps_the_exact_pair(project, premises, item, expected, marker):
    result = solve(
        f"{premises} How much {item} do Dena and Fia have {marker}?",
        project.registry,
    )

    # The substance-only question does not specify a unit. Grammar accounting
    # must not turn a volume into an unqualified water count.
    assert result.answer.committed == (expected is not None)
    assert result.value == expected
    assert result.deficiencies() == []


@pytest.mark.parametrize("item", ["books", "marbles"])
def test_named_list_and_totality_marker_do_not_include_other_holders(project, item):
    result = solve(
        f"Dena has 2 {item}. Fia has 3 {item}. Cato has 4 {item}. "
        f"Eron has 100 {item}. "
        f"How many {item} do Dena, Fia, and Cato have all together?",
        project.registry,
    )

    assert result.answer.committed
    assert result.value == 9
    assert result.deficiencies() == []


@pytest.mark.parametrize("cardinal,committed", [("2", True), ("two", True), ("3", False)])
def test_bare_cardinal_subject_is_not_an_invented_holder_set(project, cardinal, committed):
    result = solve(
        "Dena has 4 books. Fia has 6 books. "
        f"How many books do the {cardinal} have in total?",
        project.registry,
    )

    assert result.answer.committed == committed
    if committed:
        assert result.value == 10
    assert result.deficiencies() == []
    matched = match_ask(result.question, project.registry)
    assert matched[0].id == "ask/how-many-combined-cardinal-pronoun"
    assert float(matched[1]["holder_count"]) == (2 if cardinal == "two" else int(cardinal))


def test_complete_cardinal_question_without_holdings_still_declines(project):
    result = solve("How many books do the 4 have in total?", project.registry)

    assert result.deficiencies() == []
    assert not result.answer.committed


@pytest.mark.parametrize("cardinal,committed", [("2", True), ("two", True), ("3", False)])
def test_cardinal_mass_sibling_uses_the_same_quantity_accounting(project, cardinal, committed):
    result = solve(
        "Dena has $4. Fia has $6. "
        f"How much money do the {cardinal} have in total?", project.registry,
    )

    assert result.answer.committed == committed
    assert result.value == (10 if committed else None)
    assert result.deficiencies() == []


@pytest.mark.parametrize("marker", ["Total", "In total"])
@pytest.mark.parametrize("label,item,measure", [("red", "books", "book"), ("blue", "marbles", "marble")])
def test_group_label_subject_is_recorded_as_scope(project, marker, label, item, measure):
    result = solve(f"{marker} {label} lost 6 {item}.", project.registry)

    assert result.deficiencies() == []
    totals = result.store.by_kind(GroupTotal)
    assert [(f.scope, f.measure, f.value, f.verb) for f in totals] == [
        (label, measure, 6, "lose")
    ]
    assert not result.store.by_kind(Quantity)


@pytest.mark.parametrize("item,measure", [("pencils", "pencil"), ("topics", "topic")])
def test_separated_comparative_number_accounts_only_for_the_goal_relation(project, item, measure):
    candidate = retest_candidate(
        project, rule_id="arithmetic/goal-need-comparative-quantity",
        sentence=f"Dena needs 6 fewer {item} than Fia.", seed=0, origin="reading",
    )

    assert candidate.target_status == "matched"
    assert candidate.deficiencies == ()
    result = solve(candidate.sentence, project.registry)
    relations = result.store.by_kind(Relation)
    assert [(f.subject, f.standard, f.measure, f.offset, f.verb) for f in relations] == [
        ("dena", "fia", measure, -6, "need")
    ]
    assert not result.store.by_kind(Quantity)


@pytest.mark.parametrize("marker", ["start", "begin"])
@pytest.mark.parametrize("question", [
    "How many books did the teacher have to {marker} with?",
    "How many books were in the garden to {marker} with?",
])
def test_initial_state_idiom_is_grammatically_complete_without_an_anchor(project, marker, question):
    result = solve(question.format(marker=marker), project.registry)

    assert result.deficiencies() == []
    assert not result.answer.committed
    matched = match_ask(result.question, project.registry)
    assert matched[1]["start_state"] == "true"


@pytest.mark.parametrize("marker", ["start", "begin"])
def test_initial_state_marker_does_not_discharge_an_unrelated_preposition(project, marker):
    result = solve(
        f"How many books were in the garden to {marker} with at?", project.registry
    )

    assert "'at' (preposition) needs a object and none was found." in result.deficiencies()
    assert not result.answer.committed


@pytest.mark.parametrize("sentence", [
    "Two thirds of them are large.",
    "The sum of their ages was 28.",
    "What is the total amount of grapes they own?",
])
def test_unresolved_references_remain_real_context_requirements(project, sentence):
    result = solve(sentence, project.registry)

    assert len(result.deficiencies()) == 1
    assert "needs a refers" in result.deficiencies()[0]
    assert not result.answer.committed


@pytest.mark.parametrize("copula", ["are", "was"])
def test_possessed_number_question_does_not_expand_its_copula_frame(project, copula):
    result = solve(f"What {copula} the number of Fia's books?", project.registry)
    matched = match_ask(result.question, project.registry)

    assert not matched or matched[0].id != "ask/what-is-the-number-of-possessed"
