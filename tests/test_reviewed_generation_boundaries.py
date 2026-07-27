"""Regression gates for defects captured in the Designer review ledger.

The ledger is append-only human evidence.  These synthetic neighbours test the
general declarative boundaries inferred from it; they do not rewrite or mark
the historical reviews as resolved.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from rulekit.data.project import load_project
from rulekit.data.schemas import MatchToken, WherePredicate
from rulekit.generation import generate_candidate, retest_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import PartitionQuantity, Quantity, Rate, Relation


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
    ("rule_id", "sentence"),
    [
        (
            "arithmetic/affine-times-as-many",
            "Cato wilted 30 more than double as many apples to rest as Eron.",
        ),
        (
            "arithmetic/fraction-as-much-elided-standard",
            "Aven wins twelve tenths as much can.",
        ),
        (
            "arithmetic/anchored-relation-elided",
            "Price are 2 more than my pencil Bira.",
        ),
        (
            "arithmetic/anaphoric-multiplier-conjunct-many",
            "Eron received 15 coins with rest and once that many.",
        ),
        (
            "arithmetic/times-as-many-conjunct",
            "Cost took 80 ages and triple as many litter as Bira.",
        ),
        (
            "arithmetic/extraposed-duration-rate",
            "It take Fia 70 friends to drops 19 roses.",
        ),
        (
            "arithmetic/times-as-many-conjunct-elided-item",
            "Dena receives 30 years in the dog and double as many.",
        ),
        (
            "arithmetic/anchored-relation-postfix-dimension",
            "Book took 30 hamsters smaller than your friend Bira.",
        ),
        (
            "arithmetic/fraction-frame-relation",
            "Egg receives eighteen eighths amount of book that their teacher Dena.",
        ),
        (
            "arithmetic/times-as-old-as",
            "Fia owns twice as old as my friend Eron.",
        ),
        (
            "arithmetic/anchored-relation-conjoined-anchor",
            "Amount is 17 fewer birds at its cookie than number and currently was 4 numbers.",
        ),
    ],
)
def test_new_live_review_failures_now_retest_absent(
    rule_id: str, sentence: str
) -> None:
    candidate = retest_candidate(
        load_project(Path("projects/curated")),
        rule_id=rule_id,
        sentence=sentence,
        seed=0,
        origin="reading",
    )

    assert candidate.target_status == "absent"


@pytest.mark.parametrize(
    ("rule_id", "sentence"),
    [
        (
            "arithmetic/affine-times-as-many",
            "Cato has 30 more than double as many apples as Eron.",
        ),
        (
            "arithmetic/fraction-as-much-elided-standard",
            "Aven wins twelve tenths as much rest.",
        ),
        (
            "arithmetic/anchored-relation-elided",
            "The teacher has 2 more than Bira.",
        ),
        (
            "arithmetic/anchored-relation-elided",
            "Cato has 2 more than my friend Bira.",
        ),
        (
            "arithmetic/anaphoric-multiplier-conjunct-many",
            "The bird found 15 coins in the garden and once that many.",
        ),
        (
            "arithmetic/anaphoric-multiplier-conjunct-many",
            "The bird found 15 coins in the garden and once this many.",
        ),
        (
            "arithmetic/anaphoric-multiplier-conjunct-many",
            "Eron received 15 coins with the rest and once that many.",
        ),
        (
            "arithmetic/times-as-many-conjunct",
            "Aven received 80 apples and triple as many books as Bira.",
        ),
    ],
)
def test_review_boundaries_keep_complete_valid_neighbours(
    rule_id: str, sentence: str, registry
) -> None:
    assert rule_id in _matched_rules(sentence, registry)


@pytest.mark.parametrize(
    ("sentence", "rule_id"),
    [
        (
            "The teacher are 2 more than Bira.",
            "arithmetic/anchored-relation-elided",
        ),
        (
            "Cato has 2 more than my pencil Bira.",
            "arithmetic/anchored-relation-elided",
        ),
        (
            "Aven received 80 ages and triple as many books as Bira.",
            "arithmetic/times-as-many-conjunct",
        ),
        (
            "Aven received 80 apples and triple as many litter as Bira.",
            "arithmetic/times-as-many-conjunct",
        ),
        (
            "Aven wins twelve tenths as much apple.",
            "arithmetic/fraction-as-much-elided-standard",
        ),
    ],
)
def test_review_boundaries_reject_complete_invalid_classes(
    sentence: str, rule_id: str, registry
) -> None:
    assert rule_id not in _matched_rules(sentence, registry)


def test_referential_is_an_explicit_schema_qualifier() -> None:
    token = MatchToken(slot="who", type="entity", referential=True)
    pp_token = MatchToken(
        slot="obj",
        type="noun",
        referential=True,
        bare_reference_category="bare_pp_object",
    )

    assert token.referential is True
    assert pp_token.bare_reference_category == "bare_pp_object"

    with pytest.raises(
        ValidationError,
        match="`bare_reference_category` requires `referential: true`",
    ):
        MatchToken(
            slot="obj",
            type="noun",
            bare_reference_category="bare_pp_object",
        )


def test_standalone_only_qualifies_number_slots() -> None:
    token = MatchToken(slot="n", type="number", standalone=True)
    assert token.standalone is True

    with pytest.raises(
        ValidationError,
        match="`standalone` only qualifies a `type: number` slot",
    ):
        MatchToken(slot="item", type="counted", standalone=True)


def test_postfix_counted_relation_does_not_double_fire_as_elided(
    registry,
) -> None:
    matched = _matched_rules(
        "Cato has 6 marbles more than Bira.",
        registry,
    )

    assert "arithmetic/anchored-relation-postfix" in matched
    assert "arithmetic/anchored-relation-elided" not in matched


def test_conditional_standard_type_is_inspectable() -> None:
    candidate = retest_candidate(
        load_project(Path("projects/curated")),
        rule_id="arithmetic/anchored-relation-elided",
        sentence="Cato has 2 more than my friend Bira.",
        seed=0,
        origin="reading",
    )
    premise = next(
        row
        for row in candidate.premises
        if row.kind == "where"
        and row.expression.startswith("bound_requires_type(")
    )

    assert "bound='appos_role'" in premise.expression
    assert "type='proper_name'" in premise.expression
    assert "'appos_role' was bound" in premise.reason
    assert "std='Bira'" in premise.reason


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
        "arithmetic/affine-times-as-many",
        "arithmetic/fraction-as-much-elided-standard",
        "arithmetic/anchored-relation-elided",
        "arithmetic/anaphoric-multiplier-conjunct-many",
        "arithmetic/times-as-many-conjunct",
        "arithmetic/extraposed-duration-rate",
        "arithmetic/times-as-many-conjunct-elided-item",
        "arithmetic/anchored-relation-postfix-dimension",
        "arithmetic/fraction-frame-relation",
        "arithmetic/times-as-old-as",
        "arithmetic/anchored-relation-conjoined-anchor",
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


@pytest.mark.parametrize(
    ("text", "rule_id"),
    [
        ("Fia owns twice as old as Eron.", "arithmetic/times-as-old-as"),
        (
            "Fia owns twice older than Eron.",
            "arithmetic/times-comparative-age-relation",
        ),
        (
            "Fia owns 3 years older.",
            "arithmetic/dangling-comparative-relation",
        ),
        (
            "3 years ago Fia had twice as old as Eron.",
            "arithmetic/temporal-offset-times-as-old-as-past",
        ),
        (
            "3 years ago Fia had 20 years old.",
            "arithmetic/temporal-offset-age-past",
        ),
    ],
)
def test_age_family_rejects_possession_verbs(
    text: str, rule_id: str, registry
) -> None:
    assert rule_id not in _matched_rules(text, registry)


@pytest.mark.parametrize(
    ("text", "rule_id"),
    [
        ("Fia is twice as old as Eron.", "arithmetic/times-as-old-as"),
        (
            "Fia was twice older than Eron.",
            "arithmetic/times-comparative-age-relation",
        ),
        (
            "3 years ago Fia was twice as old as Eron.",
            "arithmetic/temporal-offset-times-as-old-as-past",
        ),
        (
            "3 years ago Fia was 20 years old.",
            "arithmetic/temporal-offset-age-past",
        ),
    ],
)
def test_age_family_keeps_copular_surfaces(
    text: str, rule_id: str, registry
) -> None:
    assert rule_id in _matched_rules(text, registry)


@pytest.mark.parametrize(
    "text",
    [
        "It take Fia 70 years to buy 19 roses.",
        "It takes Fia 70 friends to buy 19 roses.",
        "It takes Fia 70 years to buys 19 roses.",
        "It takes Fia 70 ages to buy 19 roses.",
    ],
)
def test_duration_rate_rejects_reviewed_morphology_and_measure_classes(
    text: str, registry
) -> None:
    assert "arithmetic/extraposed-duration-rate" not in _matched_rules(
        text, registry
    )


def test_duration_rate_keeps_a_finite_matrix_and_bare_infinitive(
    registry,
) -> None:
    result = solve("It took Fia 70 years to buy 19 roses.", registry)

    assert "arithmetic/extraposed-duration-rate" in _matched_rules(
        "It took Fia 70 years to buy 19 roses.", registry
    )
    assert any(
        fact.entity == "fia"
        and fact.measure == "rose"
        and fact.per == "year"
        and fact.numerator == 19
        and fact.denominator == 70
        for fact in result.store.by_kind(Rate)
    )


@pytest.mark.parametrize(
    "text",
    [
        "Book took 30 inches smaller than Bira.",
        "Book is 30 hamsters smaller than Bira.",
        "Book is 30 pounds smaller than Bira.",
        "Book is 30 ages longer than Bira.",
    ],
)
def test_dimension_relation_rejects_wrong_verb_and_unit_classes(
    text: str, registry
) -> None:
    assert (
        "arithmetic/anchored-relation-postfix-dimension"
        not in _matched_rules(text, registry)
    )


@pytest.mark.parametrize(
    "text",
    [
        "Book is 30 inches smaller than Bira.",
        "Book is 30 pounds heavier than Bira.",
        "Book was 30 years longer than Bira.",
    ],
)
def test_dimension_relation_keeps_compatible_units(
    text: str, registry
) -> None:
    result = solve(text, registry)
    assert "arithmetic/anchored-relation-postfix-dimension" in {
        match.match.rule.id for match in result.document.rule_results[0]
    }
    assert result.store.by_kind(Relation)


@pytest.mark.parametrize(
    "text",
    [
        "Fia receives two eighths number of books that Dena receives.",
        "Fia receives two eighths the amount of books that Dena receives.",
        "Fia receives two eighths the number of book that Dena receives.",
        "Fia receives two eighths the number of books that Dena.",
        "Fia traveled to half the number of gardens Dena traveled.",
    ],
)
def test_fraction_frame_requires_a_complete_count_relative_clause(
    text: str, registry
) -> None:
    assert "arithmetic/fraction-frame-relation" not in _matched_rules(
        text, registry
    )


@pytest.mark.parametrize(
    "text",
    [
        "Fia receives two eighths the number of books that Dena receives.",
        "Fia received half the number of books Dena received.",
        "Fia traveled to half the number of gardens Dena traveled to.",
    ],
)
def test_fraction_frame_keeps_complete_direct_and_prepositional_forms(
    text: str, registry
) -> None:
    assert "arithmetic/fraction-frame-relation" in _matched_rules(
        text, registry
    )


def test_same_presence_is_an_explicit_discontinuous_structure_predicate() -> None:
    predicate = WherePredicate(
        same_presence=["verb_prep", "echo_prep"]
    )
    assert predicate.same_presence == ["verb_prep", "echo_prep"]


@pytest.mark.parametrize(
    "text",
    [
        "Dena receives 30 years in the garden and double as many.",
        "Dena receives 30 years with the rest and double as many.",
    ],
)
def test_elided_conjunct_keeps_declared_pp_compatibility(
    text: str, registry
) -> None:
    assert "arithmetic/times-as-many-conjunct-elided-item" in _matched_rules(
        text, registry
    )


def test_conjoined_anchor_keeps_specific_quantity_holders(registry) -> None:
    assert "arithmetic/anchored-relation-conjoined-anchor" in _matched_rules(
        "Fia has 17 fewer birds than cats and currently has 4 cats.",
        registry,
    )
