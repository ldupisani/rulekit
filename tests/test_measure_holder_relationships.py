"""Measure/holder relations are category data, not disguised verb frames."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import GenerationError, generate_candidate
from rulekit.kernel.engine import solve


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
MIGRATED_RULES = {
    "arithmetic/anchored-relation",
    "arithmetic/anchored-relation-conjoined-anchor",
    "arithmetic/anchored-relation-elided-standard",
    "arithmetic/anchored-relation-postfix",
}


def _matched_rules(text: str, registry) -> set[str]:
    result = solve(text, registry)
    return {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


def _write_inherited_relationship_project(root: Path) -> None:
    base = root / "base"
    extension = root / "extension"
    base.mkdir(parents=True)
    extension.mkdir()
    (root / "project.yaml").write_text(
        """\
format: rulekit/project@1
name: inherited-measure-holder-relationship
packs: [./base, ./extension]
"""
    )
    (base / "pack.yaml").write_text(
        "format: rulekit/pack@1\nname: base\nversion: 0.1.0\n"
    )
    (extension / "pack.yaml").write_text(
        "format: rulekit/pack@1\nname: extension\nversion: 0.1.0\n"
    )
    (base / "lexicon.yaml").write_text(
        """\
format: rulekit/lexicon@1
entries:
  student: {senses: [noun], plural: students}
  undergraduate: {senses: [noun], plural: undergraduates}
  university: {senses: [noun], plural: universities}
  college: {senses: [noun], plural: colleges}
  book: {senses: [noun], plural: books}
"""
    )
    (base / "categories.yaml").write_text(
        """\
format: rulekit/categories@1
categories:
  population_measure: {parent: noun}
  student_measure: {parent: population_measure}
  undergraduate_measure: {parent: student_measure}
  education_holder: {parent: noun}
  university_holder: {parent: education_holder}
  college_holder: {parent: university_holder}
members:
  student_measure: [student]
  undergraduate_measure: [undergraduate]
  university_holder: [university]
  college_holder: [college]
measure_holder_compatibility:
  student_measure: [university_holder]
"""
    )
    (extension / "lexicon.yaml").write_text(
        """\
format: rulekit/lexicon@1
entries:
  scholar: {senses: [noun], plural: scholars}
  academy: {senses: [noun], plural: academies}
"""
    )
    # Extension packs can add vocabulary to either descendant without
    # redefining the categories or touching a grammar rule.
    (extension / "categories.yaml").write_text(
        """\
format: rulekit/categories@1
members:
  undergraduate_measure: [scholar]
  college_holder: [academy]
"""
    )


def test_student_relationship_is_declared_once_and_rules_only_map_slots() -> None:
    registry = load_project(CURATED).registry

    assert registry.measure_holder_compatibility[
        "student_quantity_measure"
    ] == ("student_quantity_holder",)
    for rule in registry.rules:
        for predicate in rule.where:
            legacy = predicate.verb_role_compatible
            assert not (
                legacy is not None
                and legacy.verb == "item"
                and legacy.verb_cat == "student_quantity_measure"
            )

    migrated = {
        rule.id
        for rule in registry.rules
        if rule.id in MIGRATED_RULES
        and any(
            predicate.measure_holder_compatible is not None
            and predicate.measure_holder_compatible.measure == "item"
            and predicate.measure_holder_compatible.holders == ["who"]
            and predicate.measure_holder_compatible.allow_proper_name
            and predicate.measure_holder_compatible.when_declared
            for predicate in rule.where
        )
    }
    assert migrated == MIGRATED_RULES


def test_student_measure_boundary_is_conditional_and_behavior_preserving() -> None:
    registry = load_project(CURATED).registry

    assert registry.measure_applies_to_holder("student", "teacher")
    assert not registry.measure_applies_to_holder("student", "book")
    assert "arithmetic/anchored-relation" in _matched_rules(
        "The teacher has 5 more students than the gardener.", registry
    )
    assert "arithmetic/anchored-relation" not in _matched_rules(
        "The book has 5 more students than the gardener.", registry
    )
    # An unrelated measure has no declared boundary and remains open, exactly
    # as it did under the old conditional trigger predicate.
    assert "arithmetic/anchored-relation" in _matched_rules(
        "The book has 5 more apples than the gardener.", registry
    )
    # The old positive predicate admitted proper names; the migration does too.
    assert "arithmetic/anchored-relation" in _matched_rules(
        "Arden has 5 more students than Briar.", registry
    )


@pytest.mark.parametrize("rule_id", sorted(MIGRATED_RULES))
def test_strict_generation_uses_the_declared_student_holder_boundary(
    rule_id: str,
) -> None:
    project = load_project(CURATED)
    candidate = generate_candidate(
        project,
        rule_id=rule_id,
        seed=13,
        identity_bindings={"who": "teacher", "item": "student"},
    )
    assert candidate.target_status == "matched"

    with pytest.raises(GenerationError, match="no filler"):
        generate_candidate(
            project,
            rule_id=rule_id,
            seed=13,
            identity_bindings={"who": "book", "item": "student"},
        )


def test_measure_and_holder_descendants_inherit_an_extensible_relationship(
    tmp_path: Path,
) -> None:
    _write_inherited_relationship_project(tmp_path)
    registry = load_project(tmp_path).registry

    assert registry.measure_has_holder_boundary("undergraduate")
    assert registry.measure_applies_to_holder("undergraduate", "college")
    assert registry.measure_applies_to_holder("scholar", "academy")
    assert not registry.measure_applies_to_holder("student", "book")
