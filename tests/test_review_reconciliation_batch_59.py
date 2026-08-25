"""Review-led boundaries for anchored quantity relations with PP modifiers."""

import json
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.generation.reviews import review_path
from rulekit.kernel.engine import solve


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
INVALID_REVIEWS = {
    "rev-6ac6c0fa79a64d9e": (
        "arithmetic/anchored-relation-possessive-kinship-standard",
        "The bench left 14 fewer populations about the topic than his gardener.",
    ),
    "rev-198ebe188f494eca": (
        "arithmetic/anchored-relation",
        "The shopper lost 50 older populations about the storeroom than the friend.",
    ),
}
PP_RELATION_RULES = {
    "arithmetic/anchored-relation",
    "arithmetic/anchored-relation-possessive-kinship-standard",
    "arithmetic/anchored-relation-conjoined-anchor",
    "arithmetic/anchored-relation-elided-standard",
}


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


def test_latest_invalid_reviews_remain_in_the_append_only_ledger(project) -> None:
    rows = {
        row["id"]: row
        for line in review_path(project).read_text(encoding="utf-8").splitlines()
        if line.strip()
        for row in [json.loads(line)]
    }

    assert INVALID_REVIEWS.keys() <= rows.keys()
    for review_id, (rule_id, sentence) in INVALID_REVIEWS.items():
        assert rows[review_id]["verdict"] == "invalid"
        assert rows[review_id]["target_rule"] == rule_id
        assert rows[review_id]["sentence"] == sentence


@pytest.mark.parametrize(
    ("rule_id", "sentence"),
    tuple(INVALID_REVIEWS.values()),
)
def test_reviewed_invalid_relations_no_longer_match(
    project, rule_id: str, sentence: str
) -> None:
    assert rule_id not in _matched_rules(sentence, project.registry)


@pytest.mark.parametrize(
    ("rule_id", "sentence"),
    (
        (
            "arithmetic/anchored-relation",
            "The shopper lost 50 more books about the topic than the friend.",
        ),
        (
            "arithmetic/anchored-relation-possessive-kinship-standard",
            "The teacher left 14 fewer books about the topic than her gardener.",
        ),
        (
            "arithmetic/anchored-relation",
            "The shopper left 14 fewer apples than the gardener.",
        ),
        (
            "arithmetic/anchored-relation-elided-standard",
            "Mary has 5 more books about the topic.",
        ),
    ),
)
def test_relation_boundaries_keep_ordinary_positive_neighbours(
    project, rule_id: str, sentence: str
) -> None:
    assert rule_id in _matched_rules(sentence, project.registry)


@pytest.mark.parametrize(
    ("rule_id", "sentence"),
    (
        (
            "arithmetic/anchored-relation",
            "The shopper lost 50 older books than the friend.",
        ),
        (
            "arithmetic/anchored-relation",
            "The shopper lost 50 more populations about the topic than the friend.",
        ),
        (
            "arithmetic/anchored-relation",
            "The shopper lost 50 more books about the storeroom than the friend.",
        ),
        (
            "arithmetic/anchored-relation",
            "The bench left 14 fewer apples than the gardener.",
        ),
        (
            "arithmetic/anchored-relation-elided-standard",
            "Mary has 5 more populations about the topic.",
        ),
    ),
)
def test_each_new_boundary_rejects_its_independent_negative_neighbour(
    project, rule_id: str, sentence: str
) -> None:
    assert rule_id not in _matched_rules(sentence, project.registry)


def test_pp_relation_family_declares_one_consistent_attachment_contract(
    project,
) -> None:
    rules = {rule.id: rule for rule in project.registry.rules}

    for rule_id in PP_RELATION_RULES:
        rule = rules[rule_id]
        assert any(
            predicate.attribute_compatible is not None
            and predicate.attribute_compatible.attribute == "pp_prep"
            and predicate.attribute_compatible.noun == "pp_obj"
            for predicate in rule.where
        )
        assert any(
            predicate.modifier_host_compatible is not None
            and predicate.modifier_host_compatible.modifier == "pp_prep"
            and predicate.modifier_host_compatible.host == "item"
            and predicate.modifier_host_compatible.object == "pp_obj"
            for predicate in rule.where
        )
        assert any(
            predicate.slot_not_category
            == {"slot": "dir", "cat": "age_comparative"}
            for predicate in rule.where
        )


def test_quantitative_left_has_construction_owned_actor_and_theme_maps(
    project,
) -> None:
    rules = {rule.id: rule for rule in project.registry.rules}

    for rule_id in {
        "arithmetic/anchored-relation",
        "arithmetic/anchored-relation-possessive-kinship-standard",
    }:
        mappings = {
            (
                predicate.verb_role_compatible.verb_cat,
                tuple(predicate.verb_role_compatible.roles),
                predicate.verb_role_compatible.role_cat,
            )
            for predicate in rules[rule_id].where
            if predicate.verb_role_compatible is not None
        }
        assert (
            "past_departure_quantity_verb",
            ("who",),
            "quantity_event_participant",
        ) in mappings
        assert (
            "past_departure_quantity_verb",
            ("item",),
            "transferable_quantity_object",
        ) in mappings


@pytest.mark.parametrize("rule_id", sorted(PP_RELATION_RULES))
def test_repaired_relation_rules_remain_strictly_generatable(
    project, rule_id: str
) -> None:
    candidate = generate_candidate(project, rule_id=rule_id, seed=59)
    assert candidate.target_status in {"matched", "shadowed"}
