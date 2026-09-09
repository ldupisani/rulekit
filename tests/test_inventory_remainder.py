"""Invented inventories: subtype conservation and actor-specific references."""

import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import InventoryScope, InventoryWithdrawal


@pytest.fixture(scope="module")
def registry():
    return load_project("projects/curated").registry


def story():
    return ("In a box, there are 30 red balls, 20 blue balls, and 10 green balls. "
            "If Mira takes away 4 red balls, and Cato takes away 6 red balls and "
            "twice as many blue balls as the number of red balls that he removed, "
            "then calculate the total number of balls that remained in the box.")


def test_inventory_keeps_subtypes_and_removing_actors(registry):
    r = solve(story(), registry)
    assert r.value == 38, r.answer
    assert len(r.store.by_kind(InventoryScope)) == 1
    events = r.store.by_kind(InventoryWithdrawal)
    assert len(events) == 3
    proportional = next(e for e in events if e.factor is not None)
    assert proportional.actor == proportional.standard_actor == "cato"
    assert proportional.standard_qualifier == "red"
    assert "blue: 8 remaining" in r.answer.reason


@pytest.mark.parametrize("old,new,expected", [
    ("takes away", "removes", 38),
    ("twice", "three times", 32),
    ("then calculate", "calculate", 38),
    ("box", "truck", 38),
    ("balls", "hard hats", 38),
    ("red", "pink", 38),
    ("30 red balls, 20 blue balls, and 10 green balls", "30 red balls and 20 blue balls", 28),
    ("4 red balls", "9 red balls", 33),
    ("6 red balls", "5 red balls", 41),
    ("20 blue balls", "10 blue balls", None),
    ("30 red balls", "8 red balls", None),
    ("6 red balls", "6 yellow balls", None),
    ("number of red balls", "number of green balls", None),
    ("that he removed", "that Mira removed", None),
    ("twice", "half", None),
    ("30 red balls", "30 red apples", None),
    ("in the box.", "in the bag.", None),
    ("If Mira", "Mira adds 5 red balls. If Mira", None),
    ("6 red balls", "6 red balls tomorrow", None),
    ("blue", "large", None),
])
def test_inventory_variations_and_boundaries(registry, old, new, expected):
    r = solve(story().replace(old, new), registry)
    assert r.value == expected, r.answer


def test_repeated_same_actor_reference_is_not_guessed(registry):
    text = story().replace("Mira takes away 4", "Cato takes away 4")
    assert not solve(text, registry).answer.committed


def test_consequent_marker_is_not_a_general_question_cue(registry):
    text = "If Mira removes 4 red balls, then Cato removes 2 blue balls."
    r = solve(text, registry)
    assert r.question is None


@pytest.mark.parametrize("project", ["curated", "gsm8k"])
@pytest.mark.parametrize("rule", [
    "located-inventory-two-subtypes", "located-inventory-three-subtypes",
    "inventory-subtype-withdrawal", "inventory-subtype-withdrawal-and-proportion",
    "inventory-subtype-particle-withdrawal", "inventory-subtype-particle-withdrawal-and-proportion",
])
def test_inventory_premises_generate(project, rule):
    from rulekit.generation import generate_candidate
    c = generate_candidate(load_project("projects/" + project), rule_id="arithmetic/" + rule, seed=11)
    assert c.target_status == "matched"
    assert c.facts
