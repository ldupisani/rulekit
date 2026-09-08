"""Same-holder affine comparisons over explicitly distinct item modifiers."""

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Relation

RULE = "arithmetic/affine-fraction-qualified-measures"


@pytest.fixture(scope="module")
def project():
    return load_project("projects/curated")


@pytest.mark.parametrize("direction,expected", [("fewer", 57), ("less", 57), ("more", 63)])
@pytest.mark.parametrize("subject", ["Cato", "He also"])
def test_fraction_precedes_offset_and_qualified_counts_sum(project, direction, expected, subject):
    result = solve(
        f"Cato has 40 red balls. {subject} has 3 {direction} than half as many "
        "blue balls as red balls. How many balls does Cato have in all?",
        project.registry,
    )
    assert result.value == expected
    relation, = result.store.by_kind(Relation)
    assert (relation.measure, relation.standard) == ("ball", "ball")
    assert (relation.measure_qualifier, relation.standard_qualifier) == ("blue", "red")


def test_compound_modifiers_and_owned_site_use_existing_reading(project):
    result = solve(
        "Dena has 48 coconut trees on her farm. She also has 4 more than one fourth "
        "as many mango trees as coconut trees. How many trees does Dena have in all on her farm?",
        project.registry,
    )
    assert result.value == 64


def test_named_subtype_ask_keeps_its_modifier(project):
    result = solve(
        "Cato has 40 red balls. Cato has 3 fewer than half as many blue balls as red balls. "
        "How many blue balls does Cato have?", project.registry,
    )
    assert result.value == 17


@pytest.mark.parametrize("premise", [
    "Cato has 40 green balls.",
    "Dena has 40 red balls.",
    "Cato has 4 red balls.",
])
def test_missing_wrong_or_negative_anchor_declines(project, premise):
    result = solve(premise + " Cato has 3 fewer than half as many blue balls as red balls. "
                   "How many balls does Cato have?", project.registry)
    assert not result.answer.committed


@pytest.mark.parametrize("premise", [
    "Cato has 3 fewer than half as many blue balls as blue balls.",
    "Cato has 3 fewer than half as many balls as red balls.",
    "Cato has 3 fewer than half as many blue balls as red coats.",
    "Cato hopes 3 fewer than half as many blue balls as red balls.",
    "Cato has 3 fewer than half as many blue balls as Dena's red balls.",
    "Cato has 3 fewer than half as many blue balls as 20 red balls.",
])
def test_incompatible_construction_does_not_match(project, premise):
    result = solve(premise, project.registry)
    assert not any(fact.provenance.source == RULE for fact in result.store.by_kind(Relation))


def test_rule_generates_qualified_neighbours(project):
    candidate = generate_candidate(project, rule_id=RULE, seed=17)
    assert candidate.target_status == "matched"


@pytest.mark.parametrize("subject", ["Dena's teacher", "the tall teacher", "teacher B"])
def test_scoped_holder_identity_cannot_be_discarded(project, subject):
    text = ("Cato's teacher has 40 red balls. " + subject
            + " has 3 fewer than half as many blue balls as red balls. "
            + "How many balls does " + subject + " have?")
    result = solve(text, project.registry)
    assert not result.answer.committed
    assert not any(f.provenance.source == RULE for f in result.store.by_kind(Relation))


def test_bare_slot_checks_the_pronouns_actual_referent(project):
    from rulekit.data.schemas import MatchToken
    from rulekit.kernel.model import Obligation, Unit
    from rulekit.kernel.patterns import _slot_ok

    owner = Unit(uid=0, words=(), features={
        "senses": ["noun"], "lemma": "teacher", "owner": "cato",
    })
    pronoun = Unit(uid=1, words=(), features={
        "senses": ["pronoun"], "lemma": "she",
        "obligations": [Obligation(role="pronoun", need="refers", target=owner)],
    })
    assert not _slot_ok(pronoun, MatchToken(slot="who", type="entity", bare=True), project.registry)
    owner.features.pop("owner")
    assert _slot_ok(pronoun, MatchToken(slot="who", type="entity", bare=True), project.registry)
