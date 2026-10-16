"""Role/location language retains exact restrictions across unrelated domains."""
import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Atom, Membership, VerbalRelation

@pytest.fixture(scope="module")
def reg():
    return load_project("projects/curated").registry

@pytest.mark.parametrize("role,place", [("student", "school"), ("teacher", "university"), ("worker", "company"), ("painter", "park")])
@pytest.mark.parametrize("article", ["a", "the"])
@pytest.mark.parametrize("suffix", ["", " in Chicago", " in the town"])
def test_role_and_full_location_survive(reg, role, place, article, suffix):
    result = solve(f"Mira is a {role} at {article} {place}{suffix}. Is Mira a {role}?", reg)
    assert result.answer.value == "yes", result.answer
    assert all(not reading.deficiencies() for reading in result.premises)
    expected = f"{role} at " + ("a " if article == "a" else "") + place + suffix.lower().replace("the town", "town")
    assert any(a.entity == "mira" and a.pred == expected and a.indef_obj == (article == "a") for a in result.store.by_kind(Atom))
    assert not list(result.store.by_kind(VerbalRelation))
    assert not any(m.collection == place for m in result.store.by_kind(Membership))

@pytest.mark.parametrize("role,place", [("student", "school"), ("worker", "company"), ("painter", "park"), ("gardener", "garden")])
def test_role_context_composes_with_budget(reg, role, place):
    text = (f"Mira is a {role} at a {place} in Chicago. "
            "Mira has a budget of $900. She spends 20% on food, 10% on rent, and the rest on books. "
            "How much money does she spend on books?")
    result = solve(text, reg)
    assert result.answer.value == 630, result.answer
    assert not result.deficiencies(), result.deficiencies()

@pytest.mark.parametrize("description", ["a university", "the school", "the university in Chicago"])
def test_restricted_role_does_not_inherit_a_different_class(reg, description):
    result = solve("All teachers at the university have 16 books. "
                   f"Mira is a teacher at {description}. How many books does Mira have?", reg)
    assert not result.answer.committed, result.answer


def test_exact_role_restriction_still_inherits(reg):
    result = solve("All teachers at the university have 16 books. Mira is a teacher at the university. How many books does Mira have?", reg)
    assert result.answer.value == 16, result.answer


def test_role_modifier_is_preserved(reg):
    result = solve("Mira is a head teacher at the university. Is Mira a teacher?", reg)
    assert result.answer.value == "yes", result.answer
    assert any(a.pred == "head teacher at university" for a in result.store.by_kind(Atom))

@pytest.mark.parametrize("text", [
    "Mira is not a teacher at the university.",
    "Mira is a teacher near the university.",
    "Mira is a teacher at the university in a town.",
    "Mira is a teacher at 3 universities.",
])
def test_unlicensed_context_is_not_consumed_as_role_location(reg, text):
    result = solve(text, reg)
    assert not any(a.provenance.source.startswith("arithmetic/personal-role-at-") for a in result.store.by_kind(Atom))


def test_role_location_variants_round_trip_through_generation():
    from rulekit.generation import generate_candidate
    project = load_project("projects/curated")
    for suffix in ("definite-location", "indefinite-location", "definite-location-in-area", "indefinite-location-in-area"):
        rule_id = "arithmetic/personal-role-at-" + suffix
        candidate = generate_candidate(project, rule_id=rule_id, seed=0)
        assert candidate.target_status == "matched", candidate


def test_definite_role_determiner_keeps_the_role_location(reg):
    result = solve("Mira is the teacher at the school. Is Mira a teacher?", reg)
    assert result.answer.value == "yes"
    assert any(a.pred == "teacher at school" for a in result.store.by_kind(Atom))
