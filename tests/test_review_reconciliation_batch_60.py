"""Review-led measure/holder boundaries for explicit count-ratio relations."""

import json
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.generation.reviews import review_path
from rulekit.kernel.engine import solve


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
REVIEW_ID = "rev-6439b086bb1c44b2"
REVIEWED_SENTENCE = (
    "The storeroom had 0 less than eight eighths as many universities "
    "as her student Dena."
)
COUNT_RATIO_FORMS = (
    ("arithmetic/as-many", "{holder} had as many {measure} as Dena."),
    (
        "arithmetic/times-as-many",
        "{holder} had twice as many {measure} as Dena.",
    ),
    (
        "arithmetic/fraction-as-many",
        "{holder} had half as many {measure} as Dena.",
    ),
    (
        "arithmetic/affine-times-as-many",
        "{holder} had 1 fewer than twice as many {measure} as Dena.",
    ),
    (
        "arithmetic/affine-fraction-as-many",
        "{holder} had 1 fewer than half as many {measure} as Dena.",
    ),
)


@pytest.fixture(scope="module")
def project():
    return load_project(CURATED)


def _matched_rules(text: str, registry) -> set[str]:
    result = solve(text, registry)
    return {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


def test_latest_invalid_review_remains_in_the_append_only_ledger(project) -> None:
    rows = {
        row["id"]: row
        for line in review_path(project).read_text(encoding="utf-8").splitlines()
        if line.strip()
        for row in [json.loads(line)]
    }

    assert rows[REVIEW_ID]["verdict"] == "invalid"
    assert rows[REVIEW_ID]["target_rule"] == (
        "arithmetic/affine-fraction-as-many"
    )
    assert rows[REVIEW_ID]["sentence"] == REVIEWED_SENTENCE


def test_reviewed_storeroom_university_relation_no_longer_matches(project) -> None:
    assert "arithmetic/affine-fraction-as-many" not in _matched_rules(
        REVIEWED_SENTENCE,
        project.registry,
    )


@pytest.mark.parametrize(("rule_id", "surface"), COUNT_RATIO_FORMS)
def test_count_ratio_family_rejects_incompatible_institution_holders(
    project, rule_id: str, surface: str
) -> None:
    sentence = surface.format(holder="The storeroom", measure="universities")
    assert rule_id not in _matched_rules(sentence, project.registry)


@pytest.mark.parametrize(("rule_id", "surface"), COUNT_RATIO_FORMS)
def test_count_ratio_family_keeps_declared_institution_holders(
    project, rule_id: str, surface: str
) -> None:
    sentence = surface.format(holder="The area", measure="universities")
    assert rule_id in _matched_rules(sentence, project.registry)


@pytest.mark.parametrize(("rule_id", "surface"), COUNT_RATIO_FORMS)
def test_narrow_institution_boundary_does_not_restrict_unbounded_objects(
    project, rule_id: str, surface: str
) -> None:
    sentence = surface.format(holder="The storeroom", measure="apples")
    assert rule_id in _matched_rules(sentence, project.registry)


def test_institution_measure_holder_relationship_is_pack_declared(project) -> None:
    registry = project.registry

    assert registry.word_in_category("university", "institution_quantity_measure")
    assert registry.word_in_category("area", "institution_quantity_holder")
    assert registry.measure_applies_to_holder("university", "area")
    assert not registry.measure_applies_to_holder("university", "storeroom")

    rules = {rule.id: rule for rule in registry.rules}
    for rule_id, _surface in COUNT_RATIO_FORMS:
        assert any(
            predicate.measure_holder_compatible is not None
            and predicate.measure_holder_compatible.measure == "item"
            and predicate.measure_holder_compatible.holders == ["who", "std"]
            and predicate.measure_holder_compatible.allow_proper_name
            and predicate.measure_holder_compatible.when_declared
            for predicate in rules[rule_id].where
        )


@pytest.mark.parametrize("rule_id", [item[0] for item in COUNT_RATIO_FORMS])
def test_repaired_count_ratio_rules_remain_strictly_generatable(
    project, rule_id: str
) -> None:
    candidate = generate_candidate(project, rule_id=rule_id, seed=60)
    assert candidate.target_status in {"matched", "shadowed"}
