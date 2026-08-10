"""Review-led declarative boundaries for the 2026-08-08 strict batch."""

import json
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate, retest_candidate
from rulekit.generation.reviews import review_path
from rulekit.kernel.engine import solve


CURATED = Path(__file__).resolve().parents[1] / "projects" / "curated"

REVIEW_CASES = {
    "rev-f8c8abe2bb974c58": (
        "arithmetic/affine-fraction-as-many",
        "The grape teach 16 fewer than two eighths as many storerooms as the cupboard.",
    ),
    "rev-30e61a91c4cd47bf": (
        "arithmetic/periodic-rate-every-span",
        "The pantry travels 9 animals every 16 years.",
    ),
    "rev-da4d4c42019245b3": (
        "arithmetic/anchored-relation-fully-elided",
        "The alpaca had 16 younger.",
    ),
    "rev-84c91c0abe764c08": (
        "arithmetic/times-as-much-elided-standard",
        "Eron gives twice as much sand on its bench.",
    ),
    "rev-446cc6817a63462e": (
        "arithmetic/group-total-leading",
        "In total unlike spends 7 heads.",
    ),
    "rev-18a60fd1e1b54400": (
        "arithmetic/existential-premise-distributive",
        "There are 14 years about each rest.",
    ),
}


def _matched_rules(text: str, registry) -> set[str]:
    result = solve(text, registry)
    return {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


@pytest.mark.parametrize("review_id", REVIEW_CASES)
def test_historical_reviewed_strict_surfaces_retest_absent(review_id: str) -> None:
    project = load_project(CURATED)
    # These review rows are durable regression evidence even after the user
    # tombstones them from the live Designer queue. Read the append-only
    # history rather than its live fold so queue cleanup cannot erase tests.
    history = {
        review["id"]: review
        for review in (
            json.loads(line)
            for line in review_path(project).read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    review = history[review_id]
    rule_id, sentence = REVIEW_CASES[review_id]

    assert review["verdict"] == "invalid"
    assert review["target_rule"] == rule_id
    assert review["sentence"] == sentence

    candidate = retest_candidate(
        project,
        rule_id=rule_id,
        sentence=sentence,
        seed=review["seed"],
        requested_bindings=review["requested_bindings"],
        origin=review["origin"],
    )

    assert candidate.target_status == "absent"
    assert rule_id not in _matched_rules(sentence, project.registry)
    assert all(fact["source"] != rule_id for fact in candidate.facts)


@pytest.mark.parametrize(
    ("rule_id", "text"),
    [
        (
            "arithmetic/affine-fraction-as-many",
            "The teacher teaches 16 fewer than two eighths as many "
            "students as the gardener.",
        ),
        (
            "arithmetic/periodic-rate-every-span",
            "The alpaca travels 9 inches every 16 years.",
        ),
        (
            "arithmetic/anchored-relation-fully-elided",
            "The dog has 20 apples. The alpaca had 16 fewer.",
        ),
        (
            "arithmetic/times-as-much-elided-standard",
            "Eron gives twice as much sand in the garden.",
        ),
        (
            "arithmetic/group-total-leading",
            "In total Eron spends 7 coins.",
        ),
        (
            "arithmetic/existential-premise-distributive",
            "There are 14 books about each topic.",
        ),
    ],
)
def test_review_boundaries_keep_ordinary_neighbours(
    rule_id: str, text: str, registry
) -> None:
    assert rule_id in _matched_rules(text, registry)


def test_review_boundaries_are_pack_declared() -> None:
    project = load_project(CURATED)
    rules = {rule.id: rule for rule in project.registry.rules}

    def verb_roles(rule_id: str) -> set[tuple[str, tuple[str, ...], str]]:
        return {
            (
                predicate.verb_role_compatible.verb_cat,
                tuple(predicate.verb_role_compatible.roles),
                predicate.verb_role_compatible.role_cat or "",
            )
            for predicate in rules[rule_id].where
            if predicate.verb_role_compatible is not None
        }

    for rule_id in {
        "arithmetic/affine-times-as-many",
        "arithmetic/affine-fraction-as-many",
    }:
        assert (
            "animate_subject_verb",
            ("who", "std"),
            "quantity_event_participant",
        ) in verb_roles(rule_id)
        assert (
            "animate_object_verb",
            ("item",),
            "quantity_event_participant",
        ) in verb_roles(rule_id)

    periodic = verb_roles("arithmetic/periodic-rate-every-span")
    assert (
        "motion_comparison_verb",
        ("who",),
        "motion_participant",
    ) in periodic
    assert (
        "motion_comparison_verb",
        ("item",),
        "motion_comparison_measure",
    ) in periodic

    exclusions = {
        rule_id: {
            (
                predicate.slot_not_category["slot"],
                predicate.slot_not_category["cat"],
            )
            for predicate in rules[rule_id].where
            if predicate.slot_not_category is not None
        }
        for rule_id in {
            "arithmetic/anchored-relation-elided-standard",
            "arithmetic/anchored-relation-fully-elided",
            "arithmetic/times-as-much-elided-standard",
            "arithmetic/group-total-leading",
            "arithmetic/group-total-leading-marker",
        }
    }
    assert ("dir", "age_comparative") in exclusions[
        "arithmetic/anchored-relation-elided-standard"
    ]
    assert ("dir", "age_comparative") in exclusions[
        "arithmetic/anchored-relation-fully-elided"
    ]
    assert ("pp_prep", "quantity_surface_preposition") in exclusions[
        "arithmetic/times-as-much-elided-standard"
    ]
    for rule_id in {
        "arithmetic/group-total-leading",
        "arithmetic/group-total-leading-marker",
    }:
        assert ("who", "preposition") in exclusions[rule_id]

    distributive = rules["arithmetic/existential-premise-distributive"]
    assert any(
        predicate.attribute_compatible is not None
        and predicate.attribute_compatible.attribute == "prep"
        and predicate.attribute_compatible.noun == "place"
        for predicate in distributive.where
    )


@pytest.mark.parametrize(
    "rule_id", sorted({case[0] for case in REVIEW_CASES.values()})
)
def test_reconciled_rules_still_generate_strict_matches(rule_id: str) -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id=rule_id,
        seed=34,
    )

    assert candidate.target_status == "matched"
    assert rule_id in {match.rule_id for match in candidate.actual_matches}
