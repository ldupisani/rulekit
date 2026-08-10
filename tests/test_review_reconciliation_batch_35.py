"""Review-led boundaries for the 2026-08-10 curated generation batch."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate, retest_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import QuantifiedQuantity


CURATED = Path(__file__).resolve().parents[1] / "projects" / "curated"


@pytest.fixture(scope="module")
def registry():
    return load_project(CURATED).registry


def _matched_rules(text: str, registry) -> set[str]:
    result = solve(text, registry)
    return {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


REVIEWED_INVALID = [
    (
        "arithmetic/affine-fraction-as-many",
        (
            "The july left 8 less than three thirds as many birds in the "
            "garden as the pantry."
        ),
    ),
    (
        "arithmetic/partition-membership-of-noun",
        "17 of the pounds were benches.",
    ),
    (
        "arithmetic/ratio-split-of-to",
        "Ratio of guardians to pantries owns 10 90.",
    ),
    (
        "logic-arithmetic/universal-all-have-quantity-pp",
        "All marbles at the university have 40 percentages.",
    ),
    (
        "arithmetic/anchored-relation-conjoined-measures",
        "Animal found 1 fewer businesses and 19 more ages than student.",
    ),
]


@pytest.mark.parametrize(("rule_id", "sentence"), REVIEWED_INVALID)
def test_live_reviewed_surfaces_no_longer_match_target(
    rule_id: str, sentence: str, registry
) -> None:
    candidate = retest_candidate(
        load_project(CURATED),
        rule_id=rule_id,
        sentence=sentence,
        seed=35,
        origin="generated",
    )

    assert candidate.target_status == "absent"
    assert rule_id not in _matched_rules(sentence, registry)
    assert all(fact["source"] != rule_id for fact in candidate.facts)


@pytest.mark.parametrize(
    ("rule_id", "sentence"),
    [
        (
            "arithmetic/affine-fraction-as-many",
            (
                "The teacher left 8 less than three thirds as many birds in "
                "the garden as the pantry."
            ),
        ),
        (
            "arithmetic/partition-membership-of-noun",
            "17 of the animals were rabbits.",
        ),
        (
            "arithmetic/ratio-split-of-to",
            "The ratio of guardians to pantries is 10:90.",
        ),
        (
            "logic-arithmetic/universal-all-have-quantity-pp",
            "All teachers at the university have 40 students.",
        ),
        (
            "arithmetic/anchored-relation-conjoined-measures",
            (
                "The teacher found 1 fewer apples and 19 more pencils than "
                "the student."
            ),
        ),
    ],
)
def test_review_boundaries_keep_ordinary_neighbours(
    rule_id: str, sentence: str, registry
) -> None:
    assert rule_id in _matched_rules(sentence, registry)


def test_rejected_universal_quantity_is_consumed_without_a_fallback_fact(
    registry,
) -> None:
    result = solve(
        "All marbles at the university have 40 percentages.", registry
    )

    assert not result.facts()
    assert not result.store.by_kind(QuantifiedQuantity)


def test_review_boundaries_are_pack_declared(registry) -> None:
    rules = {rule.id: rule for rule in registry.rules}

    for rule_id in {
        "arithmetic/affine-times-as-many",
        "arithmetic/affine-fraction-as-many",
    }:
        tokens = {
            token.slot: token for token in rules[rule_id].match["sentence"]
            if token.slot in {"who", "std"}
        }
        assert tokens["who"].common_noun_cat == "quantity_holder"
        assert tokens["std"].common_noun_cat == "quantity_holder"

    partition = rules["arithmetic/partition-membership-of-noun"]
    assert any(
        predicate.slot_not_category
        == {"slot": "coll", "cat": "mass_measure"}
        for predicate in partition.where
    )

    ratio = rules["arithmetic/ratio-split-of-to"]
    verb = next(
        token for token in ratio.match["sentence"] if token.slot == "verb"
    )
    assert verb.cat == "copula"

    universal = rules["logic-arithmetic/universal-all-have-quantity-pp"]
    assert any(
        predicate.slot_not_category
        == {"slot": "item", "cat": "many_incompatible_noun"}
        for predicate in universal.where
    )

    conjoined = rules["arithmetic/anchored-relation-conjoined-measures"]
    assert any(
        predicate.verb_role_compatible is not None
        and predicate.verb_role_compatible.verb_cat == "find_quantity_verb"
        and predicate.verb_role_compatible.roles == ["item", "item2"]
        and predicate.verb_role_compatible.role_cat
        == "findable_quantity_object"
        for predicate in conjoined.where
    )


@pytest.mark.parametrize(
    "rule_id",
    sorted({rule_id for rule_id, _ in REVIEWED_INVALID}),
)
def test_reconciled_rules_still_generate_strict_matches(rule_id: str) -> None:
    candidate = generate_candidate(
        load_project(CURATED), rule_id=rule_id, seed=35
    )

    assert candidate.target_status == "matched"
    assert rule_id in {match.rule_id for match in candidate.actual_matches}
