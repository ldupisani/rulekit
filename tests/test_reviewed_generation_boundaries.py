"""Regression gates for defects captured in the Designer review ledger.

The ledger is append-only human evidence.  These synthetic neighbours test the
general declarative boundaries inferred from it; they do not rewrite or mark
the historical reviews as resolved.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from rulekit.data.project import load_project
from rulekit.data.schemas import MatchToken
from rulekit.generation import generate_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import PartitionQuantity, Quantity


def _matched_rules(text: str, registry) -> set[str]:
    result = solve(text, registry)
    return {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


@pytest.mark.parametrize(
    ("text", "rule_id"),
    [
        ("3 of them are red.", "arithmetic/partition-attribute"),
        ("1 of them is red.", "arithmetic/partition-attribute"),
        ("Half of them are red.", "arithmetic/partition-attribute-fraction"),
        ("2 of the marbles are red.", "arithmetic/partition-attribute-of-noun"),
        ("1 of the marbles was red.", "arithmetic/partition-attribute-of-noun"),
        ("4 of them are dogs.", "arithmetic/partition-membership"),
        (
            "Three fourths of them were dogs.",
            "arithmetic/partition-membership-fraction",
        ),
        (
            "6 of the marbles are dogs.",
            "arithmetic/partition-membership-of-noun",
        ),
    ],
)
def test_partition_rules_accept_their_grammatical_surfaces(
    text: str, rule_id: str, registry
) -> None:
    assert rule_id in _matched_rules(text, registry)


@pytest.mark.parametrize(
    ("text", "rule_id"),
    [
        # Reviewed singular-pronoun failures.
        ("9 of i ate red.", "arithmetic/partition-attribute"),
        (
            "Seventeen sixths of he have red.",
            "arithmetic/partition-attribute-fraction",
        ),
        # Copula and agreement neighbours.
        ("3 of them ate red.", "arithmetic/partition-attribute"),
        ("1 of them are red.", "arithmetic/partition-attribute"),
        ("2 of them is red.", "arithmetic/partition-attribute"),
        # A definite noun partition must actually contain the article.
        (
            "2 of marbles spent large.",
            "arithmetic/partition-attribute-of-noun",
        ),
        (
            "2 of marbles are large.",
            "arithmetic/partition-attribute-of-noun",
        ),
        # The plural-predicate rule does not claim a singular membership.
        ("1 of them is dogs.", "arithmetic/partition-membership"),
    ],
)
def test_partition_rules_reject_reviewed_and_neighbouring_bad_surfaces(
    text: str, rule_id: str, registry
) -> None:
    assert rule_id not in _matched_rules(text, registry)


def test_partition_match_still_emits_the_expected_fact(registry) -> None:
    result = solve("3 of them are red.", registry)
    match = next(
        match
        for match in result.document.rule_results[0]
        if match.match.rule.id == "arithmetic/partition-attribute"
    )

    assert match.facts == [
        PartitionQuantity(
            provenance=match.facts[0].provenance,
            collection="them",
            attribute="red",
            value=3,
            verb="be",
        )
    ]


@pytest.mark.parametrize(
    "text",
    [
        "Aven eat 20 apples to Dena.",
        "Cato dropped 50 gardens to Eron.",
        "Aven lost 20 apples to Dena.",
    ],
)
def test_non_transfer_losses_do_not_gain_recipients(text: str, registry) -> None:
    assert "arithmetic/transfer-prepositional" not in _matched_rules(
        text, registry
    )


@pytest.mark.parametrize(
    ("text", "rule_id"),
    [
        ("Aven gave 20 apples to Dena.", "arithmetic/transfer-prepositional"),
        ("Aven sold Dena 20 apples.", "arithmetic/transfer-ditransitive"),
    ],
)
def test_declared_transfer_verbs_keep_both_transfer_surfaces(
    text: str, rule_id: str, registry
) -> None:
    assert rule_id in _matched_rules(text, registry)


def test_transfer_still_emits_balanced_giver_and_recipient_facts(registry) -> None:
    result = solve("Aven gave 20 apples to Dena.", registry)
    quantities = {
        (fact.entity, fact.measure, fact.value, fact.verb)
        for fact in result.store.by_kind(Quantity)
    }

    assert ("aven", "apple", 20, "give") in quantities
    assert ("dena", "apple", 20, "receive") in quantities


@pytest.mark.parametrize(
    "text",
    [
        "Fia owns 0 hamsters old.",
        "Fia has 4 apples old.",
        "Fia are 4 years old.",
    ],
)
def test_stated_age_rejects_reviewed_verb_measure_and_agreement_defects(
    text: str, registry
) -> None:
    assert "arithmetic/stated-age" not in _matched_rules(text, registry)


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("Fia is 1 year old.", 1),
        ("Fia was 4 years old.", 4),
    ],
)
def test_stated_age_requires_a_copula_and_declared_age_unit(
    text: str, value: int, registry
) -> None:
    result = solve(text, registry)
    assert "arithmetic/stated-age" in {
        match.match.rule.id for match in result.document.rule_results[0]
    }
    assert any(
        fact.entity == "fia"
        and fact.measure == "year"
        and fact.value == value
        for fact in result.store.by_kind(Quantity)
    )


def test_counted_category_is_an_explicit_schema_qualifier() -> None:
    token = MatchToken(slot="n", cat="age_measure", counted=True)
    assert token.cat == "age_measure"
    assert token.counted is True

    with pytest.raises(
        ValidationError, match="`counted` only qualifies a category-gated slot"
    ):
        MatchToken(slot="n", type="counted", counted=True)


@pytest.mark.parametrize(
    "rule_id",
    [
        "arithmetic/partition-attribute",
        "arithmetic/partition-membership",
        "arithmetic/partition-attribute-fraction",
        "arithmetic/partition-membership-fraction",
        "arithmetic/partition-attribute-of-noun",
        "arithmetic/partition-membership-of-noun",
        "arithmetic/transfer-ditransitive",
        "arithmetic/transfer-prepositional",
        "arithmetic/stated-age",
    ],
)
def test_review_corrected_rules_generate_only_matching_candidates(
    rule_id: str,
) -> None:
    project = load_project(Path("projects/curated"))

    for seed in range(16):
        candidate = generate_candidate(project, rule_id=rule_id, seed=seed)
        assert candidate.target_status in {"matched", "shadowed"}
        assert candidate.target_rule == rule_id
