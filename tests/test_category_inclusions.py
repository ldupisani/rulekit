"""Nominal role unions reuse taxonomy without changing its meaning."""

from dataclasses import replace
from pathlib import Path

import pytest

from rulekit.data.packs import LoadedPack
from rulekit.data.project import load_project
from rulekit.data.registry import CompileError, compile_registry
from rulekit.data.schemas import CategoriesDoc, LexiconEntry, PackDoc
from rulekit.generation import generate_candidate
from rulekit.kernel.engine import solve


def pack(name, categories=None, members=None, words=()):
    return LoadedPack(
        name=name, root=Path(name),
        manifest=PackDoc(format="rulekit/pack@1", name=name),
        lexicon={w: LexiconEntry(senses=["noun"]) for w in words},
        categories=[CategoriesDoc(format="rulekit/categories@1",
                                  categories=categories or {}, members=members or {})],
        fingerprint=name,
    )


def test_union_includes_descendants_and_later_pack_extensions():
    base = pack("base", {
        "people": {"parent": "noun"},
        "specialists": {"parent": "people"},
        "devices": {"parent": "noun"},
        "actors": {"parent": "noun", "includes": ["people", "devices"]},
        "producers": {"parent": "noun", "includes": ["actors"]},
    }, {"specialists": ["artisan"], "devices": ["printer"],
        "actors": ["collective"]}, ("artisan", "printer", "collective"))
    extension = pack("extension", members={"specialists": ["engineer"]}, words=("engineer",))
    registry = compile_registry([base, extension])
    assert registry.cat_members_deep("producers") == ["artisan", "collective", "engineer", "printer"]
    assert registry.word_in_category("engineer", "actors")
    assert not registry.word_in_category("printer", "people")
    assert not registry.word_in_category("collective", "devices")
    assert registry.cat_ancestors("devices") == ["devices", "noun"]
    assert registry.category_membership_path("engineer", "producers") == (
        "engineer", "specialists", "people", "actors", "producers")
    assert compile_registry([extension, base]).category_members == registry.category_members


@pytest.mark.parametrize("categories,error", [
    ({"a": {"parent": "noun", "includes": ["missing"]}}, "unknown category"),
    ({"a": {"parent": "noun", "includes": ["noun"]}}, "unknown category"),
    ({"a": {"parent": "noun", "includes": ["v"]}, "v": {"parent": "verb"}}, "non-noun"),
    ({"a": {"parent": "verb", "includes": ["n"]}, "n": {"parent": "noun"}}, "noun-rooted target"),
    ({"a": {"parent": "noun", "includes": ["a"]}}, "inclusion cycle"),
    ({"a": {"parent": "noun", "includes": ["b"]},
      "b": {"parent": "noun", "includes": ["a"]}}, "inclusion cycle"),
    ({"a": {"parent": "noun"}, "b": {"parent": "a", "includes": ["a"]}}, "inclusion cycle"),
])
def test_unsafe_or_cyclic_unions_fail_loudly(categories, error):
    with pytest.raises(CompileError, match=error):
        compile_registry([pack("invalid", categories)])


def test_inclusions_do_not_copy_aggregation_flags():
    registry = compile_registry([pack("flags", {
        "units": {"parent": "noun", "interchangeable": True},
        "subjects": {"parent": "noun", "includes": ["units"]},
    }, {"units": ["unit"]}, ("unit",))])
    assert "subjects" not in registry.interchangeable_categories


def test_included_members_still_validate_lexicon_and_antonym_boundaries():
    categories = {"a": {"parent": "noun"},
                  "b": {"parent": "noun", "includes": ["a"]}}
    with pytest.raises(CompileError, match="not in the lexicon"):
        compile_registry([pack("missing", categories, {"a": ["missing"]})])
    categories["b"]["antonym"] = "a"
    with pytest.raises(CompileError, match="share members"):
        compile_registry([pack("overlap", categories, {"a": ["artisan"]}, ("artisan",))])


@pytest.fixture(scope="module")
def project():
    return load_project(Path("projects/curated"))


@pytest.mark.parametrize("role", [
    "student_quantity_holder", "earning_quantity_participant",
    "initiation_quantity_participant", "production_quantity_participant",
    "allocation_participant",
])
def test_person_membership_reaches_each_role_without_copied_word_lists(project, role):
    registry = project.registry
    assert registry.category_includes[role]
    for word in ("parent", "grandparent", "brother", "gardener", "person", "teacher"):
        assert registry.word_in_category(word, role), (word, role)
    for word in ("book", "apple", "dog"):
        assert not registry.word_in_category(word, role), (word, role)
    for loaded in project.packs:
        for document in loaded.categories:
            assert role not in document.members


def test_organization_device_and_person_roles_stay_distinct(project):
    r = project.registry
    assert r.measure_applies_to_holder("student", "university")
    assert not r.measure_applies_to_holder("student", "company")
    assert r.word_in_category("company", "earning_quantity_participant")
    assert r.word_in_category("machine", "production_quantity_participant")
    assert not r.word_in_category("machine", "earning_quantity_participant")
    assert not r.word_in_category("machine", "initiation_quantity_participant")
    for word in ("company", "university", "machine"):
        assert not r.word_in_category(word, "animate")
        assert not r.word_in_category(word, "person")
    assert r.measure_applies_to_holder("university", "company")
    assert r.measure_applies_to_holder("university", "area")
    assert not r.measure_applies_to_holder("university", "teacher")
    for animal in r.cat_members_deep("animal"):
        assert r.word_in_category(animal, "quantity_event_participant")
        assert not r.word_in_category(animal, "intentional_agent")


def test_student_count_does_not_derive_teaching_or_enrollment(project):
    result = solve("The parent has 5 more students than the teacher.", project.registry)
    relations = result.store.facts
    assert relations
    assert all(getattr(f, "verb", "have") not in {"teach", "enroll"} for f in relations)


@pytest.mark.parametrize("text", [
    "The parent has 5 more students than the teacher.",
    "The company earns 5 more dollars than the university.",
    "The brother makes 5 more toys than the teacher.",
    "The machine makes 5 more toys than the teacher.",
    "The parent begins 5 more courses than the teacher.",
])
def test_existing_grammar_uses_reusable_actor_families(project, text):
    result = solve(text, project.registry)
    assert "arithmetic/anchored-relation" in {
        m.match.rule.id for ms in result.document.rule_results.values() for m in ms}


@pytest.mark.parametrize("who,item,verb", [
    ("parent", "student", "have"),
    ("grandparent", "dollar", "earn"),
    ("brother", "toy", "make"),
    ("parent", "course", "begin"),
])
def test_generation_uses_the_same_membership_as_reading(project, who, item, verb):
    result = generate_candidate(project, rule_id="arithmetic/anchored-relation", seed=11,
                                identity_bindings={"who": who, "item": item, "verb": verb})
    assert result.target_status == "matched"


def test_mined_people_extend_roles_without_changing_personal_reference_eligibility():
    r = load_project(Path("projects/gsm8k")).registry
    assert r.word_in_category("doctor", "student_quantity_holder")
    assert r.word_in_category("doctor", "earning_quantity_participant")
    assert r.word_in_category("attendee", "allocation_participant")
    assert not r.word_in_category("attendee", "animate")
    assert not r.word_in_category("player", "intentional_agent")


def test_new_person_and_institution_need_no_role_specific_memberships(project):
    extension = pack("invented-role-extension", {
        "mentors": {"parent": "person"},
        "academies": {"parent": "educational_institution"},
    }, {"mentors": ["mentor"], "academies": ["academy"]}, ("mentor", "academy"))
    r = compile_registry([*project.packs, extension])
    assert not r.word_in_category("mentor", "animate")
    assert r.measure_applies_to_holder("student", "academy")
    for role in ("earning_quantity_participant", "production_quantity_participant",
                 "initiation_quantity_participant", "allocation_participant"):
        assert r.word_in_category("mentor", role)
        assert r.word_in_category("academy", role)
    result = solve("The teacher has 8 students. The mentor has 5 more students than the teacher. "
                   "How many students does the mentor have?", r)
    assert result.answer.value == 13, result.answer
    generated = generate_candidate(replace(project, registry=r),
                                   rule_id="arithmetic/anchored-relation", seed=11,
                                   identity_bindings={"who": "mentor", "item": "student", "verb": "have"})
    assert generated.target_status == "matched"


def test_generated_source_links_explain_included_measure_holder(project):
    result = generate_candidate(project, rule_id="arithmetic/anchored-relation", seed=11,
                                identity_bindings={"who": "parent", "item": "student", "verb": "have"})
    labels = {source["label"] for premise in result.premises for source in premise.sources}
    assert {"parent ∈ animate", "person", "student_quantity_holder"} <= labels
