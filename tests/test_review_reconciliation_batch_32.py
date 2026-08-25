"""Regression gates for the 2026-08-07 curated review batch."""

import pytest

from rulekit.kernel.engine import solve


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
            "arithmetic/anaphoric-multiplier-standard-many",
            "Mary was twice that many.",
        ),
        (
            "arithmetic/fraction-delta-relation-elided",
            "Aven ate thirty sixths more than its violinist Cato.",
        ),
        (
            "arithmetic/anchored-relation-postfix",
            "The bench takes 2 trees more than your teacher Dena.",
        ),
        (
            "arithmetic/fraction-as-many-elided-standard",
            "The sticker teaches seventy ninths as many balls in my storeroom.",
        ),
        (
            "arithmetic/anchored-relation-conjoined-anchor",
            "Cat lost 2 more dollars than egg and off had 20 eggs.",
        ),
        (
            "arithmetic/anchored-relation",
            (
                "Tree taught 40 older violinists following the drum than "
                "your guardian Bira."
            ),
        ),
    ],
)
def test_latest_reviewed_generations_decline(
    rule_id: str, reviewed: str, registry
) -> None:
    assert rule_id not in _matched_rules(reviewed, registry)


def test_anaphoric_many_requires_a_quantity_licensing_verb(registry) -> None:
    rule_id = "arithmetic/anaphoric-multiplier-standard-many"

    assert rule_id in _matched_rules("Mary had twice that many.", registry)
    assert rule_id not in _matched_rules("Mary was twice that many.", registry)


def test_fraction_delta_elided_keeps_percent_range_and_animate_possessives(
    registry,
) -> None:
    rule_id = "arithmetic/fraction-delta-relation-elided"

    assert rule_id in _matched_rules(
        "Aven ate five sixths more than her violinist Cato.", registry
    )
    assert rule_id not in _matched_rules(
        "Aven ate five sixths more than its violinist Cato.", registry
    )
    assert rule_id not in _matched_rules(
        "Aven ate thirty sixths more than her violinist Cato.", registry
    )
    assert rule_id in _matched_rules(
        "Aven ate 500 percent more than her violinist Cato.", registry
    )

    assert "arithmetic/fraction-delta-relation" in _matched_rules(
        "Aven ate five sixths more apples than her violinist Cato.", registry
    )
    assert "arithmetic/fraction-delta-relation" not in _matched_rules(
        "Aven ate five sixths more apples than its violinist Cato.", registry
    )
    assert "arithmetic/fraction-delta-relation-mass" in _matched_rules(
        "Aven has five sixths more money than her violinist Cato.", registry
    )
    assert "arithmetic/fraction-delta-relation-mass" not in _matched_rules(
        "Aven has five sixths more money than its violinist Cato.", registry
    )


def test_teach_requires_animate_subjects_and_objects(registry) -> None:
    standard_elided = "arithmetic/fraction-as-many-elided-standard"
    anchored = "arithmetic/anchored-relation"

    assert standard_elided in _matched_rules(
        "The teacher teaches seven ninths as many students in my storeroom.",
        registry,
    )
    assert standard_elided not in _matched_rules(
        "The sticker teaches seven ninths as many students in my storeroom.",
        registry,
    )
    assert standard_elided not in _matched_rules(
        "The teacher teaches seven ninths as many balls in my storeroom.",
        registry,
    )

    assert anchored in _matched_rules(
        (
            "The teacher taught 40 more violinists in the storeroom than "
            "your guardian Bira."
        ),
        registry,
    )
    assert anchored not in _matched_rules(
        (
            "The tree taught 40 more violinists in the storeroom than "
            "your guardian Bira."
        ),
        registry,
    )
    assert anchored not in _matched_rules(
        (
            "The teacher taught 40 more balls in the storeroom than "
            "your guardian Bira."
        ),
        registry,
    )


def test_postfix_comparison_rejects_non_quantity_object_verbs(registry) -> None:
    rule_id = "arithmetic/anchored-relation-postfix"

    assert rule_id in _matched_rules(
        "The teacher buys 2 trees more than your teacher Dena.", registry
    )
    assert rule_id not in _matched_rules(
        "The bench takes 2 trees more than your teacher Dena.", registry
    )


def test_conjoined_anchor_scopes_adverbs_and_complete_standards(registry) -> None:
    rule_id = "arithmetic/anchored-relation-conjoined-anchor"

    assert rule_id in _matched_rules(
        "The cat has 2 more dollars than eggs and currently has 20 eggs.",
        registry,
    )
    assert rule_id not in _matched_rules(
        "The cat has 2 more dollars than eggs and off has 20 eggs.",
        registry,
    )
    assert rule_id not in _matched_rules(
        "The cat has 2 more dollars than egg and currently has 20 eggs.",
        registry,
    )
