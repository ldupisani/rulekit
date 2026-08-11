"""Mining increment 132: anaphoric distance chains and combined totals."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantity, Relation


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects" / "gsm8k"
GENERIC_ANAPHOR_RULE = "arithmetic/anaphoric-multiplier-standard"
ANAPHOR_RULE = "arithmetic/anaphoric-multiplier-standard-motion-distance"
DISTANCE_RULE = "arithmetic/motion-distance-comparative"


@pytest.fixture(scope="module")
def registry():
    return load_project(PROJECT).registry


def _matched_rules(result, sentence: int = 0) -> set[str]:
    return {
        match.match.rule.id
        for match in result.document.rule_results.get(sentence, [])
    }


def _derived_quantities(result) -> list[Quantity]:
    return [
        fact
        for fact in result.store.by_kind(Quantity)
        if fact.provenance.source == "synth/relation"
    ]


def test_strict_positive_measured_farther_relation(registry) -> None:
    result = solve("Aven traveled 4 miles farther than Bira.", registry)

    assert DISTANCE_RULE in _matched_rules(result)
    relation = next(
        fact
        for fact in result.store.by_kind(Relation)
        if fact.provenance.source == DISTANCE_RULE
    )
    assert relation.subject == "aven"
    assert relation.standard == "bira"
    assert relation.measure == "mile"
    assert relation.factor == 1.0
    assert relation.offset == 4.0
    assert relation.verb == "travel"


def test_strict_positive_is_generated_and_matcher_confirmed() -> None:
    candidate = generate_candidate(
        load_project(PROJECT),
        rule_id=DISTANCE_RULE,
        seed=0,
        locked_bindings={
            "who": "Aven",
            "verb": "traveled",
            "item": "4 miles",
            "dir": "farther",
            "std": "Bira",
        },
    )

    assert candidate.sentence == "Aven traveled 4 miles farther than Bira."
    assert candidate.target_status == "matched"
    fact = next(fact for fact in candidate.facts if fact["type"] == "Relation")
    assert fact["source"] == DISTANCE_RULE
    assert fact["fields"]["offset"] == 4.0


def test_distance_anaphor_is_generated_and_matcher_confirmed() -> None:
    candidate = generate_candidate(
        load_project(PROJECT),
        rule_id=ANAPHOR_RULE,
        seed=0,
        locked_bindings={
            "who": "Bira",
            "verb": "ran",
            "k": "twice",
            "head": "distance",
        },
    )

    assert candidate.sentence == "Bira ran twice this distance."
    assert candidate.target_status == "matched"
    fact = next(fact for fact in candidate.facts if fact["type"] == "Relation")
    assert fact["source"] == ANAPHOR_RULE
    assert fact["fields"]["standard"] == "$anaphor:quantity$"
    assert fact["fields"]["factor"] == 2.0


def test_boundary_probe_rejects_outside_linear_comparative(registry) -> None:
    strict = solve("Aven traveled 4 miles farther than Bira.", registry)
    boundary = solve("Aven traveled 4 miles older than Bira.", registry)

    assert DISTANCE_RULE in _matched_rules(strict)
    assert DISTANCE_RULE not in _matched_rules(boundary)


@pytest.mark.parametrize("head", ["height", "weight"])
def test_outside_category_anaphor_heads_are_absent(head: str, registry) -> None:
    result = solve(
        f"Aven ran 6 miles. Bira ran twice that {head}.",
        registry,
    )

    assert ANAPHOR_RULE not in _matched_rules(result, sentence=1)
    assert not any(
        fact.provenance.source == ANAPHOR_RULE
        for fact in result.store.by_kind(Relation)
    )


@pytest.mark.parametrize("head", ["that distance", "the distance"])
def test_complete_chain_saturates_twice_and_answers_exact_named_pair(
    head: str, registry
) -> None:
    result = solve(
        "Aven ran 6 miles. "
        f"Bira ran twice {head}. "
        "Cato ran 3 miles farther than Bira. "
        "How many miles did Bira and Cato run in total?",
        registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == 27
    assert result.answer.reason == "Σ over ['bira', 'cato']"

    anaphor = next(
        fact
        for fact in result.store.by_kind(Relation)
        if fact.provenance.source == ANAPHOR_RULE
    )
    farther = next(
        fact
        for fact in result.store.by_kind(Relation)
        if fact.provenance.source == DISTANCE_RULE
    )
    assert (anaphor.standard, anaphor.measure, anaphor.factor) == (
        "$anaphor:quantity$",
        None,
        2.0,
    )
    assert anaphor.anaphor_measure_category == "length_measure"
    assert anaphor.anaphor_verb_category == "motion_comparison_verb"
    assert anaphor.provenance.sentence == 1
    assert (farther.subject, farther.standard, farther.measure) == (
        "cato",
        "bira",
        "mile",
    )
    assert (farther.factor, farther.offset, farther.provenance.sentence) == (
        1.0,
        3.0,
        2,
    )

    derived = {
        (quantity.entity, quantity.measure): (
            quantity.value,
            quantity.provenance.source,
            quantity.provenance.sentence,
        )
        for quantity in _derived_quantities(result)
    }
    assert derived == {
        ("bira", "mile"): (12.0, "synth/relation", 1),
        ("cato", "mile"): (15.0, "synth/relation", 2),
    }


def test_two_eligible_earlier_distances_make_anaphor_ambiguous(registry) -> None:
    result = solve(
        "Aven ran 6 miles. Dena ran 5 miles. "
        "Bira ran twice that distance. "
        "Cato ran 3 miles farther than Bira. "
        "How many miles did Bira and Cato run in total?",
        registry,
    )

    assert result.answer.kind == "decline"
    assert ANAPHOR_RULE in _matched_rules(result, sentence=2)
    assert DISTANCE_RULE in _matched_rules(result, sentence=3)
    assert not any(
        quantity.entity in {"bira", "cato"}
        for quantity in _derived_quantities(result)
    )


@pytest.mark.parametrize(
    ("antecedent", "measure", "verb"),
    [
        ("Aven has 6 apples.", "apple", "have"),
        ("Aven ran 6 hours.", "hour", "run"),
        ("Aven spent 6 dollars.", "dollar", "spend"),
        ("Aven ran 6 years.", "year", "run"),
        ("Aven has 6 miles.", "mile", "have"),
    ],
)
def test_distance_anaphor_rejects_unique_incompatible_antecedent(
    antecedent: str,
    measure: str,
    verb: str,
    registry,
) -> None:
    result = solve(
        f"{antecedent} Bira ran twice that distance. "
        "How many miles did Bira run?",
        registry,
    )

    assert any(
        quantity.entity == "aven"
        and quantity.measure == measure
        and quantity.verb == verb
        for quantity in result.store.by_kind(Quantity)
    )
    assert ANAPHOR_RULE in _matched_rules(result, sentence=1)
    assert not any(
        quantity.entity == "bira"
        for quantity in _derived_quantities(result)
    )
    assert result.answer.kind == "decline"


def test_incompatible_quantity_does_not_compete_with_unique_distance(
    registry,
) -> None:
    result = solve(
        "Aven ran 6 miles. Dena has 5 apples. "
        "Bira ran twice that distance. How many miles did Bira run?",
        registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == 12
    assert {
        (quantity.entity, quantity.measure, quantity.value)
        for quantity in _derived_quantities(result)
    } == {("bira", "mile", 12.0)}


@pytest.mark.parametrize(
    "sentence",
    [
        "Aven has 4 miles farther than Bira.",
        "Aven traveled 4 days farther than Bira.",
        "Aven traveled 4 apples farther than Bira.",
        "The box traveled 4 miles farther than Bira.",
        "Aven traveled 4 miles farther than the box.",
    ],
)
def test_motion_distance_relation_rejects_incompatible_slots(
    sentence: str, registry
) -> None:
    result = solve(sentence, registry)

    assert DISTANCE_RULE not in _matched_rules(result)
    assert not any(
        fact.provenance.source == DISTANCE_RULE
        for fact in result.store.by_kind(Relation)
    )


@pytest.mark.parametrize(
    "sentence",
    [
        "Aven traveled 4 miles farther than Aven.",
        "Aven traveled 4 miles farther.",
    ],
)
def test_motion_distance_relation_rejects_self_or_missing_standard(
    sentence: str, registry
) -> None:
    result = solve(sentence, registry)

    assert DISTANCE_RULE not in _matched_rules(result)


@pytest.mark.parametrize(
    "sentence",
    [
        "Aven ran 6 miles. Bira ran twice distance.",
        "Aven ran 6 miles. Bira ran twice the distance of Aven.",
        "Aven ran 6 miles. Bira ran twice the distance than Aven.",
    ],
)
def test_distance_anaphor_preserves_introducer_partitive_and_direct_standard_boundaries(
    sentence: str, registry
) -> None:
    result = solve(sentence, registry)

    assert ANAPHOR_RULE not in _matched_rules(result, sentence=1)
    assert GENERIC_ANAPHOR_RULE not in _matched_rules(result, sentence=1)


@pytest.mark.parametrize(
    "sentence",
    [
        "Aven ran 6 miles. Bira ran twice that number.",
        "Aven ran 6 miles. Bira arrived twice that distance.",
        "The box ran 6 miles. The box ran twice that distance.",
    ],
)
def test_specialized_anaphor_does_not_widen_generic_motion_or_object_frames(
    sentence: str, registry
) -> None:
    result = solve(sentence, registry)

    assert ANAPHOR_RULE not in _matched_rules(result, sentence=1)
    assert not any(
        fact.provenance.source == ANAPHOR_RULE
        for fact in result.store.by_kind(Relation)
    )


def test_exact_named_pair_excludes_unrequested_holder(registry) -> None:
    result = solve(
        "Aven ran 6 miles. "
        "Bira ran twice that distance. "
        "Cato ran 3 miles farther than Bira. "
        "Dena ran 100 miles. "
        "How many miles did Bira and Cato run in total?",
        registry,
    )

    assert result.answer.value == 27
    assert result.answer.reason == "Σ over ['bira', 'cato']"


def test_exact_named_holder_list_declines_when_any_holder_is_missing(
    registry,
) -> None:
    result = solve(
        "Aven ran 6 miles. "
        "Bira ran twice the distance. "
        "Cato ran 3 miles farther than Bira. "
        "How many miles did Bira, Cato, and Dena run in total?",
        registry,
    )

    assert result.answer.kind == "decline"
