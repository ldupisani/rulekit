"""Regression gates for the second 2026-08-07 curated review batch."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from rulekit.data.project import load_project
from rulekit.data.schemas import MeasureHolderCompatibilityPredicate
from rulekit.generation import (
    GenerationError,
    generate_candidate,
    list_rule_availability,
    promote_reading_candidate,
    promote_sentence_review_candidate,
)
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantity, Relation
from rulekit.server.api import ServerState, TraceBody, build_router


CURATED = Path("projects/curated")


def _matched_rules(text: str, registry) -> set[str]:
    result = solve(text, registry)
    return {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


@pytest.mark.parametrize(
    ("rule_id", "reviewed"),
    [
        (
            "arithmetic/anchored-relation-elided",
            "Fia arrives 18 older than the animal.",
        ),
        (
            "arithmetic/anaphoric-multiplier-standard",
            "Pantry arrived double this number.",
        ),
        (
            "arithmetic/anchored-relation-postfix-dimension",
            "Cato is 30 years longer than Dena.",
        ),
        (
            "arithmetic/fraction-as-much",
            "Aven gives eight tenths as much money in the bench as Mary.",
        ),
        (
            "arithmetic/anaphoric-multiplier-standard-many",
            "John cost twice that many.",
        ),
        (
            "arithmetic/fraction-delta-relation-elided",
            (
                "Aven travels five tenths younger than their violinist "
                "Bira."
            ),
        ),
        (
            "arithmetic/dangling-comparative-relation",
            "The bird is 18 dogs wider.",
        ),
        (
            "arithmetic/anchored-relation-postfix-age",
            "The apple is 1 year younger than the number.",
        ),
        (
            "arithmetic/group-total-sum-of-age",
            "The sum of his ages was 0.",
        ),
        (
            "arithmetic/anchored-relation-possessive-kinship-standard",
            "Age teach 50 less cookies on the tree than your Cato.",
        ),
    ],
)
def test_latest_reviewed_targets_decline(
    rule_id: str, reviewed: str, registry
) -> None:
    assert rule_id not in _matched_rules(reviewed, registry)


def test_valid_affine_relative_clause_review_remains_matched(registry) -> None:
    sentence = (
        "Head has 40 more than thrice the amount of marbles that his "
        "teacher John has."
    )

    assert "arithmetic/affine-frame-relation" in _matched_rules(
        sentence, registry
    )


def test_ungrammatical_affine_as_standard_surface_is_narrowed(registry) -> None:
    rule_id = "arithmetic/affine-frame-relation-as-standard"
    sentence = (
        "Fia loses 8 more than triple the amount of dogs at the university "
        "as the guardian."
    )

    assert rule_id in {rule.id for rule in registry.rules}
    assert rule_id not in _matched_rules(sentence, registry)
    assert rule_id in _matched_rules(
        (
            "Cato has 4 more than twice the number of pencils as Dena."
        ),
        registry,
    )


def test_arrival_does_not_take_a_direct_quantity_anaphor(registry) -> None:
    assert "arithmetic/anaphoric-multiplier-standard" in _matched_rules(
        "Cato has double this number.", registry
    )
    assert "arithmetic/anaphoric-multiplier-standard" not in _matched_rules(
        "Cato arrived double this number.", registry
    )


def test_elided_deltas_do_not_admit_an_unmeasured_age_comparative(
    registry,
) -> None:
    assert "arithmetic/anchored-relation-elided" in _matched_rules(
        "Fia has 18 more than the animal.", registry
    )
    assert "arithmetic/anchored-relation-elided" not in _matched_rules(
        "Fia has 18 older than the animal.", registry
    )
    assert "arithmetic/fraction-delta-relation-elided" in _matched_rules(
        "Aven eats five tenths more than Bira.", registry
    )


def test_count_anaphors_exclude_price_predicates(registry) -> None:
    for rule_id, sentence in (
        (
            "arithmetic/anaphoric-multiplier-standard-many",
            "John cost twice that many.",
        ),
        (
            "arithmetic/anaphoric-multiplier-standard-as-many",
            "John costs twice as many.",
        ),
    ):
        assert rule_id not in _matched_rules(sentence, registry)

    assert "arithmetic/anaphoric-multiplier-standard-many" in _matched_rules(
        "John bought twice that many.", registry
    )


def test_interior_location_boundary_keeps_surface_locations_distinct(
    registry,
) -> None:
    rule_id = "arithmetic/fraction-as-much"

    assert rule_id not in _matched_rules(
        "Aven gives half as much money in the bench as Mary.", registry
    )
    assert rule_id in _matched_rules(
        "Aven gives half as much money in the cupboard as Mary.", registry
    )
    assert rule_id in _matched_rules(
        "Aven gives half as much money on the bench as Mary.", registry
    )


def test_dimension_proper_names_are_limited_to_physical_measures() -> None:
    registry = load_project(Path("projects/gsm8k")).registry
    rule_id = "arithmetic/anchored-relation-postfix-dimension"

    assert rule_id not in _matched_rules(
        "Cato is 30 years longer than Dena.", registry
    )
    assert rule_id in _matched_rules(
        "The gap is 30 years longer than the trip.", registry
    )
    assert rule_id in _matched_rules(
        "Cato is 3 inches taller than Dena.", registry
    )


def test_age_relations_require_age_bearing_holders(registry) -> None:
    rule_id = "arithmetic/anchored-relation-postfix-age"

    assert rule_id not in _matched_rules(
        "The apple is 1 year younger than the number.", registry
    )
    assert rule_id in _matched_rules(
        "The dog is 1 year younger than the cat.", registry
    )
    assert rule_id in _matched_rules(
        "Cato is 1 year younger than Dena.", registry
    )


def test_sum_of_ages_uses_a_plural_possessor(registry) -> None:
    rule_id = "arithmetic/group-total-sum-of-age"

    assert rule_id not in _matched_rules(
        "The sum of his ages was 10.", registry
    )
    assert rule_id in _matched_rules(
        "The sum of their ages was 10.", registry
    )
    assert rule_id in _matched_rules("The sum of ages was 10.", registry)


def test_possessive_kinship_standard_is_an_animate_common_noun(
    registry,
) -> None:
    rule_id = "arithmetic/anchored-relation-possessive-kinship-standard"

    assert rule_id in _matched_rules(
        "The teacher teaches 5 fewer students than your guardian.", registry
    )
    assert rule_id not in _matched_rules(
        "The teacher teaches 5 fewer students than your Cato.", registry
    )


def test_dangling_comparative_safety_is_not_a_generation_target() -> None:
    project = load_project(CURATED)
    availability = {
        item.id: item for item in list_rule_availability(project)
    }
    safety = availability["arithmetic/dangling-comparative-safety"]

    assert not safety.supported
    assert safety.blockers == ("declared non-generative safety consumer",)
    with pytest.raises(
        GenerationError, match="declared non-generative safety consumer"
    ):
        generate_candidate(
            project,
            rule_id="arithmetic/dangling-comparative-safety",
            seed=0,
        )


def test_broad_dangling_safety_still_blocks_the_absolute_quantity_fold(
    registry,
) -> None:
    result = solve("The bird is 18 dogs wider.", registry)
    matched = {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }

    assert "arithmetic/dangling-comparative-relation" not in matched
    assert "arithmetic/dangling-comparative-safety" in matched
    assert not result.store.by_kind(Quantity)
    assert not result.store.by_kind(Relation)


def test_anchored_invalid_dimension_is_not_presented_as_a_premise_match(
    registry,
) -> None:
    sentence = "Cato is 30 years longer than Dena."
    result = solve(sentence, registry)
    matched = {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }

    assert matched == {"arithmetic/dangling-comparative-safety"}
    assert not result.store.by_kind(Quantity)
    assert not result.store.by_kind(Relation)

    project = load_project(CURATED)
    candidate = promote_sentence_review_candidate(
        project, sentence=sentence
    )
    assert candidate.target_status == "unmatched"
    assert candidate.actual_matches == ()
    assert [
        match.rule_id for match in candidate.safety_interceptions
    ] == ["arithmetic/dangling-comparative-safety"]
    assert candidate.to_json()["actual_rule_ids"] == []
    assert candidate.to_json()["safety_rule_ids"] == [
        "arithmetic/dangling-comparative-safety"
    ]

    router = build_router(ServerState(CURATED))
    trace_endpoint = next(
        route.endpoint
        for route in router.routes
        if route.path == "/api/trace" and "POST" in route.methods
    )
    trace = trace_endpoint(TraceBody(text=sentence))
    reading = trace["sentences"][0]
    assert reading["review_targets"] == []
    assert [
        item["rule_id"] for item in reading["safety_interceptions"]
    ] == ["arithmetic/dangling-comparative-safety"]

    with pytest.raises(
        GenerationError,
        match="a safety consumer is not a premise review target",
    ):
        promote_reading_candidate(
            project,
            rule_id="arithmetic/dangling-comparative-safety",
            sentence=sentence,
        )


def test_valid_anchorless_comparative_remains_a_reviewable_premise() -> None:
    sentence = "Cato is 2 years older."
    project = load_project(CURATED)
    candidate = promote_sentence_review_candidate(
        project, sentence=sentence
    )

    assert [match.rule_id for match in candidate.actual_matches] == [
        "arithmetic/dangling-comparative-relation"
    ]
    assert candidate.safety_interceptions == ()

    router = build_router(ServerState(CURATED))
    trace_endpoint = next(
        route.endpoint
        for route in router.routes
        if route.path == "/api/trace" and "POST" in route.methods
    )
    trace = trace_endpoint(TraceBody(text=sentence))
    reading = trace["sentences"][0]
    assert [item["rule_id"] for item in reading["review_targets"]] == [
        "arithmetic/dangling-comparative-relation"
    ]
    assert reading["safety_interceptions"] == []


def test_proper_name_measure_filter_requires_explicit_name_opt_in() -> None:
    with pytest.raises(
        ValidationError,
        match="proper-name measure categories require allow_proper_name",
    ):
        MeasureHolderCompatibilityPredicate(
            measure="item",
            holders=["who"],
            proper_name_measure_categories=["length_measure"],
        )
