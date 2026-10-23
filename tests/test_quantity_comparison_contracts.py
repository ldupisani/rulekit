"""Quantity predicates share lexical boundaries in generation and reading."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import GenerationError, generate_candidate, retest_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Relation


@pytest.fixture(scope="module")
def project():
    return load_project(Path("projects/curated"))


@pytest.mark.parametrize("sentence", [
    "Dena evaporated 2 fewer purposes than Fia.",
    "Dena evaporated 2 fewer than Fia.",
    "Dena evaporated twice as many purposes as Fia.",
    "Dena evaporated half as many purposes as Fia.",
    "Dena evaporated twice as many as Fia.",
    "Dena evaporated half as many as Fia.",
    "Dena evaporated twice as many purposes.",
    "Dena evaporated half as many purposes.",
    "Dena evaporated 2 fewer than twice as many purposes as Fia.",
    "Dena evaporated 2 fewer than half as many purposes as Fia.",
    "Dena evaporated 20% more purposes than Fia.",
    "Dena evaporated 20% more water than Fia.",
    "Dena evaporated 20% more than Fia.",
    "Dena evaporated twice the number of purposes Fia evaporated.",
    "Dena evaporated half the number of purposes Fia evaporated.",
    "Dena evaporated 2 fewer purposes than twice the number of purposes Fia evaporated.",
    "Dena evaporated 2 fewer purposes than twice the number of purposes that Fia evaporated.",
    "Dena evaporated twice that amount.",
    "Dena evaporated twice that many.",
    "Dena evaporated 3 purposes and twice as many books.",
])
def test_unlicensed_physical_predicate_cannot_emit_quantity_comparisons(project, sentence):
    result = solve(sentence, project.registry)
    assert not result.store.by_kind(Relation)
    assert not result.answer.committed


@pytest.mark.parametrize("premise,anchor,question,expected", [
    ("Dena has 1 fewer book than twice the number of books Fia has.",
     "Fia has 5 books.", "How many books does Dena have?", 9),
    ("Dena has 2 fewer books than twice the number of books Fia has.",
     "Fia has 5 books.", "How many books does Dena have?", 8),
    ("Dena has 2 fewer than twice the number of books that Fia has.",
     "Fia has 5 books.", "How many books does Dena have?", 8),
    ("Dena has 2 fewer than twice the number of books as Fia.",
     "Fia has 5 books.", "How many books does Dena have?", 8),
    ("Dena collected 2 fewer shells than twice the number of shells Fia collected.",
     "Fia collected 5 shells.", "How many shells did Dena collect?", 8),
    ("Dena collected twice the number of shells Fia collected.",
     "Fia collected 5 shells.", "How many shells did Dena collect?", 10),
    ("Dena collected half the number of shells Fia collected.",
     "Fia collected 6 shells.", "How many shells did Dena collect?", 3),
    ("Dena has 2 more than twice Fia's books.",
     "Fia has 5 books.", "How many books does Dena have?", 12),
    ("Dena has 2 less than twice as much money as Fia.",
     "Fia has 5 dollars.", "How much money does Dena have?", 8),
    ("Dena has 2 less than twice as much as Fia.",
     "Fia has 5 dollars.", "How much money does Dena have?", 8),
    ("Dena has 2 less than twice Fia's money.",
     "Fia has 5 dollars.", "How much money does Dena have?", 8),
    ("Dena has 2 more books and 3 more toys than Fia.",
     "Fia has 5 books. Fia has 4 toys.", "How many books does Dena have?", 7),
    ("Dena has 2 fewer purposes than twice the number of purposes Fia has.",
     "Fia has 5 purposes.", "How many purposes does Dena have?", 8),
    ("Dena has 2 fewer books than Fia has.",
     "Fia has 5 books.", "How many books does Dena have?", 3),
    ("Dena has 5 books. Fia has 2 fewer books than she has.",
     "", "How many books do they have together?", 8),
    ("Dena owns 3 more books than Fia has.",
     "Fia has 5 books.", "How many books does Dena have?", 8),
    ("Dena has 3 more books than Fia owns.",
     "Fia has 5 books.", "How many books does Dena have?", 8),
    ("Dena sold 2 more red cards than Fia sold.",
     "Fia sold 5 cards.", "How many red cards did Dena sell?", 7),
    ("Dena sold twice as many red cards as Fia sold.",
     "Fia sold 5 cards.", "How many red cards did Dena sell?", 10),
])
def test_valid_comparisons_answer_and_account_for_offsets(project, premise, anchor, question, expected):
    result = solve(f"{premise} {anchor} {question}", project.registry)
    assert result.answer.kind == "number", result.answer.reason
    assert result.value == pytest.approx(expected)
    assert not result.deficiencies()


@pytest.mark.parametrize("sentence", [
    "Dena has twice as many books as Fia have.",
    "Dena has half as many books as Fia have.",
    "Dena has 2 fewer than twice as many books as Fia have.",
    "Dena collects 2 more shells than Fia collect.",
    "Dena collect twice as many shells as Fia collects.",
    "Dena collects half of what Fia collect.",
    "Dena has twice as many books as Fia evaporated.",
    "Dena has half as many books as Fia evaporated.",
    "Dena has 2 more books than Fia evaporated.",
])
def test_each_comparison_predicate_agrees_with_its_subject(project, sentence):
    assert not solve(sentence, project.registry).store.by_kind(Relation)


@pytest.mark.parametrize("sentence", [
    "Dena ate twice the number of books Fia ate.",
    "Dena ate half the number of books Fia ate.",
    "Dena ate 2 fewer books than twice the number of books Fia ate.",
    "Dena ate 2 fewer books than twice the number of books that Fia ate.",
    "Dena ate 20% more books than Fia.",
    "The sea ate half the number of apples Fia ate.",
])
def test_licensed_predicates_still_require_compatible_roles(project, sentence):
    assert not solve(sentence, project.registry).store.by_kind(Relation)


def test_known_scoring_predicates_keep_their_quantitative_comparison_role():
    reg = load_project(Path("projects/gsm8k")).registry
    result = solve(
        "Dena scored 4 points. Fia scored 2 points more than Dena. "
        "How many points did Fia score?", reg,
    )
    assert result.value == pytest.approx(6), result.answer.reason


@pytest.mark.parametrize("sentence", [
    "The planks cover twice the number of plants Dena covers.",
    "The truck holds twice as many boxes as the van.",
])
def test_existing_physical_quantity_predicates_remain_comparable(sentence):
    reg = load_project(Path("projects/gsm8k")).registry
    assert solve(sentence, reg).store.by_kind(Relation)


@pytest.mark.parametrize("sentence", [
    "The teacher left 3 fewer books than the gardener.",
    "The box contains twice the number of books the jar contains.",
])
def test_declared_quantity_event_and_content_families_remain_comparable(project, sentence):
    assert solve(sentence, project.registry).store.by_kind(Relation)


def test_affine_generation_uses_the_same_predicate_boundary(project):
    with pytest.raises(GenerationError):
        generate_candidate(
            project, rule_id="arithmetic/affine-frame-relation-clause", seed=4,
            locked_bindings={"verb": "evaporated"},
        )
    candidate = generate_candidate(
        project, rule_id="arithmetic/affine-frame-relation-clause", seed=4,
        locked_bindings={
            "who": "Dena", "verb": "has", "n": "2", "dir": "fewer",
            "k": "twice", "frame": "number", "item": "books",
            "std": "Fia", "echo_verb": "has",
        },
    )
    assert candidate.clean_reading
    replay = retest_candidate(
        project, rule_id=candidate.target_rule, sentence=candidate.sentence,
        seed=candidate.seed, requested_bindings=candidate.requested_bindings,
    )
    assert replay.clean_reading


@pytest.mark.parametrize("ending", [
    "the water evaporates", "all the water evaporated",
    "the water has evaporated", "the water had fully evaporated",
])
def test_evaporation_remains_available_in_mixture_recovery(project, ending):
    result = solve(
        "Dena collects 4 liters of seawater. The water has 15% salt content. "
        f"How many ml of salt will be left when {ending}?", project.registry,
    )
    assert result.value == pytest.approx(600), result.answer.reason


def test_mixture_recovery_requires_present_subject_agreement(project):
    result = solve(
        "Dena collects 4 liters of seawater. The water is 15% salt. "
        "How many ml of salt will be left when the water evaporate?", project.registry,
    )
    assert not result.answer.committed
