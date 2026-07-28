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
from rulekit.kernel.patterns import is_bare_verb_form


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
        (
            "arithmetic/temporal-offset-times-as-old-as-future",
            "In 12 pounds Dena will be double as old as her child Fia.",
        ),
        (
            "arithmetic/temporal-offset-age-future-intensified",
            "In 15 more friend Cato would be 3 friends old.",
        ),
        (
            "arithmetic/affine-frame-relation-as-standard",
            "Remainder travels 14 older than thrice number of coin as your student Eron.",
        ),
        (
            "arithmetic/goal-desire-quantity",
            "Cato wanting to needed 3 pounds.",
        ),
        (
            "arithmetic/times-the-number-of",
            "Inch are triple amount of rose as coin.",
        ),
        (
            "arithmetic/temporal-offset-age-future",
            "In 30 toys Bira would be 13 apples old.",
        ),
        (
            "arithmetic/times-as-many-elided-standard",
            "Eron buys twice as many roses of their year.",
        ),
        (
            "arithmetic/times-as-many-elided",
            "Teacher travels twice as many as its student Fia.",
        ),
        (
            "arithmetic/partition-rest-membership",
            "Rest of the rabbits were ages.",
        ),
        (
            "arithmetic/fraction-as-many",
            "Toy spent fourteen thirds as many apples as garden.",
        ),
        (
            "arithmetic/periodic-rate-every-span",
            "Student should gets 12 hamsters some 6 apples.",
        ),
        (
            "arithmetic/times-as-much",
            "Bira sells triple as much rest in their animal as Dena.",
        ),
        (
            "arithmetic/anchored-relation-possessive-kinship-standard",
            "Apple are 20 more fish than your student.",
        ),
        (
            "arithmetic/anaphoric-price-standard",
            "Animal ran double that price.",
        ),
        (
            "arithmetic/times-as-many-conjunct-elided-standard",
            "Hamster has 4 cans on my pound and once as many teachers.",
        ),
        (
            "arithmetic/times-as-many",
            "Tree received once as many prices at the population as rest.",
        ),
        (
            "arithmetic/existential-premise",
            "There gives 60 plums on cat.",
        ),
        (
            "arithmetic/fraction-as-many-elided-standard",
            "Pencil gave eight sixths as many trees from the inch.",
        ),
        (
            "arithmetic/rest-of-pool",
            "Eron cost remainder.",
        ),
        (
            "arithmetic/times-as-many-possessive-kinship-standard",
            "Hamster lost double as many birds on my inch as my marble.",
        ),
        (
            "arithmetic/affine-times-as-much",
            "Bira had 3 more than twice as much rest from its animal as your teacher Cato.",
        ),
        (
            "arithmetic/partition-rest-attribute",
            "Rest of the ages were small.",
        ),
        (
            "arithmetic/affine-fraction-as-many",
            "Fia travels 9 less than seventeen fifths as many cookies from her animal as its friend Aven.",
        ),
        (
            "arithmetic/percent-change-event",
            "Animal rose forty sixths fewer dollar.",
        ),
        (
            "arithmetic/existential-premise-total",
            "There are 18 rabbits with combined.",
        ),
        (
            "arithmetic/existential-premise-total",
            "There are 13 areas at average.",
        ),
        (
            "arithmetic/existential-premise-total",
            "There is 1 rose with total.",
        ),
        (
            "arithmetic/existential-premise-total",
            "There are 12 toys to total.",
        ),
        (
            "arithmetic/affine-frame-relation",
            "Garden lose 19 fewer than once the amount of animals that bird.",
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
        "arithmetic/temporal-offset-times-as-old-as-future",
        "arithmetic/temporal-offset-age-future-intensified",
        "arithmetic/affine-frame-relation-as-standard",
        "arithmetic/goal-desire-quantity",
        "arithmetic/times-the-number-of",
        "arithmetic/temporal-offset-age-future",
        "arithmetic/times-as-many-elided-standard",
        "arithmetic/times-as-many-elided",
        "arithmetic/partition-rest-membership",
        "arithmetic/fraction-as-many",
        "arithmetic/periodic-rate-every-span",
        "arithmetic/times-as-much",
        "arithmetic/anchored-relation-possessive-kinship-standard",
        "arithmetic/anaphoric-price-standard",
        "arithmetic/times-as-many-conjunct-elided-standard",
        "arithmetic/times-as-many",
        "arithmetic/existential-premise",
        "arithmetic/fraction-as-many-elided-standard",
        "arithmetic/rest-of-pool",
        "arithmetic/times-as-many-possessive-kinship-standard",
        "arithmetic/affine-times-as-much",
        "arithmetic/partition-rest-attribute",
        "arithmetic/affine-fraction-as-many",
        "arithmetic/percent-change-event",
        "arithmetic/existential-premise-total",
        "arithmetic/times-frame-relation-clause",
        "arithmetic/affine-frame-relation",
        "arithmetic/affine-frame-relation-clause",
        "arithmetic/affine-item-relation-clause",
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
        "Fia receives two eighths the amount of books that Dena receives.",
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


@pytest.mark.parametrize(
    ("text", "rule_id"),
    [
        (
            "In 12 years Dena will be double as old as her child Fia.",
            "arithmetic/temporal-offset-times-as-old-as-future",
        ),
        (
            "In 15 more years Cato would be 30 years old.",
            "arithmetic/temporal-offset-age-future-intensified",
        ),
        (
            "In 3 years Bira would be 13 years old.",
            "arithmetic/temporal-offset-age-future",
        ),
    ],
)
def test_temporal_age_rules_keep_declared_age_units(
    text: str, rule_id: str, registry
) -> None:
    assert rule_id in _matched_rules(text, registry)


@pytest.mark.parametrize(
    ("text", "rule_id"),
    [
        (
            "In 12 pounds Dena will be double as old as Fia.",
            "arithmetic/temporal-offset-times-as-old-as-future",
        ),
        (
            "In 15 more friend Cato would be 30 years old.",
            "arithmetic/temporal-offset-age-future-intensified",
        ),
        (
            "In 3 years Bira would be 13 apples old.",
            "arithmetic/temporal-offset-age-future",
        ),
    ],
)
def test_temporal_age_rules_reject_non_age_counted_nouns(
    text: str, rule_id: str, registry
) -> None:
    assert rule_id not in _matched_rules(text, registry)


@pytest.mark.parametrize(
    "text",
    [
        "Remainder sold 14 older than thrice the number of coins as Eron.",
        "Cato sold 14 less coins than thrice the number of coins as Eron.",
        "Cato sold 14 more coins than thrice the number of coin as Eron.",
        "Cato traveled 14 more coins than thrice the number of coins as Eron.",
    ],
)
def test_affine_count_frame_rejects_reviewed_incomplete_classes(
    text: str, registry
) -> None:
    assert "arithmetic/affine-frame-relation-as-standard" not in _matched_rules(
        text, registry
    )


@pytest.mark.parametrize("frame", ["amount", "number"])
def test_affine_count_frame_keeps_its_complete_surface(
    frame: str, registry
) -> None:
    assert "arithmetic/affine-frame-relation-as-standard" in _matched_rules(
        f"Cato sold 14 more coins than thrice the {frame} of coins as Eron.",
        registry,
    )


@pytest.mark.parametrize(
    "text",
    [
        "Cato wanting to buy 3 pounds.",
        "Cato wants to needed 3 pounds.",
        "Cato want to buy 3 pounds.",
    ],
)
def test_desire_goal_rejects_nonfinite_matrix_and_inflected_complement(
    text: str, registry
) -> None:
    assert "arithmetic/goal-desire-quantity" not in _matched_rules(
        text, registry
    )


def test_desire_goal_keeps_finite_matrix_and_bare_complement(registry) -> None:
    assert "arithmetic/goal-desire-quantity" in _matched_rules(
        "Cato wants to buy 3 pounds.", registry
    )


@pytest.mark.parametrize(
    "text",
    [
        "Inch has triple the number of roses as Dena.",
        "Cato has triple the number of rose as Dena.",
    ],
)
def test_number_frame_rejects_measure_holders_and_incomplete_count_frames(
    text: str, registry
) -> None:
    assert "arithmetic/times-the-number-of" not in _matched_rules(
        text, registry
    )


@pytest.mark.parametrize("frame", ["amount", "number"])
def test_number_frame_keeps_complete_count_relation(
    frame: str, registry
) -> None:
    assert "arithmetic/times-the-number-of" in _matched_rules(
        f"Cato has triple the {frame} of roses as Dena.", registry
    )


def test_affine_item_echo_agrees_with_the_offset_count(registry) -> None:
    rule_id = "arithmetic/affine-frame-relation"

    assert rule_id in _matched_rules(
        "Cato has 1 more apple than triple the number of apples that Dena has.",
        registry,
    )
    assert rule_id not in _matched_rules(
        "Cato has 2 more apple than triple the number of apples that Dena has.",
        registry,
    )
    assert rule_id in _matched_rules(
        "Cato has 2 more than triple the number of apples that Dena has.",
        registry,
    )


@pytest.mark.parametrize(
    "sentence",
    [
        "There are 12 toys total.",
        "There are 12 toys altogether.",
        "There are 12 toys combined.",
        "There are 12 toys together.",
        "There are 12 toys in total.",
    ],
)
def test_existential_group_totals_keep_declared_marker_collocations(
    sentence: str, registry
) -> None:
    assert "arithmetic/existential-premise-total" in _matched_rules(
        sentence, registry
    )


@pytest.mark.parametrize(
    "sentence",
    [
        "There are 12 toys average.",
        "There are 12 toys on total.",
        "There are 12 toys in combined.",
    ],
)
def test_group_total_is_not_an_average_or_arbitrary_preposition_pair(
    sentence: str, registry
) -> None:
    assert "arithmetic/existential-premise-total" not in _matched_rules(
        sentence, registry
    )


@pytest.mark.parametrize(
    ("rule_id", "complete", "incomplete"),
    [
        (
            "arithmetic/times-frame-relation-clause",
            "Cato has twice the number of animals Dena has.",
            "Cato has twice the number of animals Dena.",
        ),
        (
            "arithmetic/affine-frame-relation",
            "Cato has 2 fewer than twice the number of animals that Dena has.",
            "Cato has 2 fewer than twice the number of animals that Dena.",
        ),
        (
            "arithmetic/affine-frame-relation-clause",
            "Cato has 2 fewer than twice the number of animals Dena has.",
            "Cato has 2 fewer than twice the number of animals Dena.",
        ),
    ],
)
def test_count_frames_require_complete_relative_clauses(
    rule_id: str, complete: str, incomplete: str, registry
) -> None:
    assert rule_id in _matched_rules(complete, registry)
    assert rule_id not in _matched_rules(incomplete, registry)


def test_affine_money_frame_requires_its_relative_clause_predicate(
    registry,
) -> None:
    rule_id = "arithmetic/affine-item-relation-clause"
    anchor = " Dena has 30 apples."

    assert rule_id in _matched_rules(
        "Cato has 2 less than twice the apple Dena has." + anchor,
        registry,
    )
    assert rule_id not in _matched_rules(
        "Cato has 2 less than twice the apple Dena." + anchor,
        registry,
    )


def test_count_frame_relative_clause_can_state_a_duration_span(
    registry,
) -> None:
    assert "arithmetic/affine-frame-relation-clause" in _matched_rules(
        "Cato has 2 fewer than twice the number of apples Dena has in 1 year.",
        registry,
    )


def test_affine_frame_subject_and_echo_verbs_must_agree(registry) -> None:
    rule_id = "arithmetic/affine-frame-relation"

    assert rule_id in _matched_rules(
        "Garden loses 19 fewer than once the amount of animals that bird loses.",
        registry,
    )
    assert rule_id not in _matched_rules(
        "Garden lose 19 fewer than once the amount of animals that bird loses.",
        registry,
    )
    assert rule_id not in _matched_rules(
        "Garden loses 19 fewer than once the amount of animals that bird has.",
        registry,
    )


def test_elided_standard_pp_uses_declared_object_compatibility(registry) -> None:
    assert "arithmetic/times-as-many-elided-standard" in _matched_rules(
        "Eron buys twice as many apples in the garden.", registry
    )
    assert "arithmetic/times-as-many-elided-standard" not in _matched_rules(
        "Eron buys twice as many apples of their year.", registry
    )


def test_animate_appositive_refuses_inanimate_possessive(registry) -> None:
    assert "arithmetic/times-as-many-elided" in _matched_rules(
        "Teacher travels twice as many as their student Fia.", registry
    )
    assert "arithmetic/times-as-many-elided" not in _matched_rules(
        "Teacher travels twice as many as its student Fia.", registry
    )


def test_explicit_membership_collection_requires_declared_superclass() -> None:
    registry = load_project(Path("projects/curated")).registry
    assert "arithmetic/partition-rest-membership" in _matched_rules(
        "Rest of the animals were rabbits.", registry
    )
    assert "arithmetic/partition-rest-membership" not in _matched_rules(
        "Rest of the rabbits were ages.", registry
    )


def test_agentive_verb_roles_are_conditional_and_pack_owned(registry) -> None:
    rule_id = "arithmetic/fraction-as-many"

    assert rule_id in _matched_rules(
        "Teacher spent half as many apples as Cato.", registry
    )
    assert rule_id not in _matched_rules(
        "Toy spent half as many apples as Cato.", registry
    )
    assert rule_id not in _matched_rules(
        "Cato spent half as many apples as garden.", registry
    )
    assert rule_id in _matched_rules(
        "Garden has half as many apples as Cato.", registry
    )


def test_verb_role_compatibility_is_an_explicit_schema_predicate() -> None:
    predicate = WherePredicate(
        verb_role_compatible={
            "verb": "verb",
            "roles": ["who", "std"],
            "verb_cat": "spend_verb",
            "role_cat": "animate",
        }
    )

    assert predicate.verb_role_compatible is not None
    assert predicate.verb_role_compatible.roles == ["who", "std"]


def test_finite_form_is_an_explicit_scalar_verb_qualifier() -> None:
    token = MatchToken(slot="want", cat="finite_desire", finite_form=True)
    assert token.finite_form is True

    with pytest.raises(
        ValidationError, match="`finite_form` only qualifies a slot"
    ):
        MatchToken(lit="want", finite_form=True)

    with pytest.raises(
        ValidationError, match="cannot require both finite and bare form"
    ):
        MatchToken(
            slot="want",
            cat="finite_desire",
            finite_form=True,
            bare_form=True,
        )

    with pytest.raises(
        ValidationError, match="a span slot takes no"
    ):
        MatchToken(slot="want", span=True, finite_form=True)


def test_generic_animal_ownership_is_core_and_not_shadowed() -> None:
    project = load_project(Path("projects/curated"))
    animal_entries = [
        entry
        for word, entry in project.registry.lexicon.items()
        if word == "animal"
    ]

    assert len(animal_entries) == 1
    assert (
        project.source_index.lexicon["animal"].path.resolve()
        == (
            Path("packs/core-english/lexicon/core.yaml").resolve()
        )
    )


@pytest.mark.parametrize(
    "text",
    [
        "Student should gets 12 hamsters every 6 years.",
        "Student should get 12 hamsters some 6 years.",
        "Student should get 12 hamsters every 6 apples.",
    ],
)
def test_periodic_rate_rejects_nonbare_modal_verbs_and_nonperiodic_spans(
    text: str, registry
) -> None:
    assert "arithmetic/periodic-rate-every-span" not in _matched_rules(
        text, registry
    )


@pytest.mark.parametrize(
    "text",
    [
        "Student should get 12 hamsters every 6 years.",
        "Student gets 12 hamsters every 6 years.",
    ],
)
def test_periodic_rate_keeps_modal_and_finite_duration_forms(
    text: str, registry
) -> None:
    assert "arithmetic/periodic-rate-every-span" in _matched_rules(
        text, registry
    )


def test_modal_periodic_generation_uses_bare_form_and_declared_frequency() -> None:
    project = load_project(Path("projects/curated"))
    candidate = generate_candidate(
        project,
        rule_id="arithmetic/periodic-rate-every-span",
        seed=0,
        locked_bindings={"aux": "should"},
    )
    bindings = {
        row.slot: row.binding
        for row in candidate.premises
        if row.slot is not None
    }

    assert candidate.target_status == "matched"
    assert bindings["aux"] == "should"
    verb = bindings["verb"]
    assert is_bare_verb_form(
        verb, project.registry.verb_lemmas.get(verb, verb)
    )
    assert bindings["freq"] == "every"
    assert bindings["span"].endswith((" year", " years"))


@pytest.mark.parametrize(
    ("text", "matched"),
    [
        ("Bira sells triple as much rest as Dena.", False),
        ("Bira sells triple as much litter in their garden as Dena.", True),
        ("Bira has triple as much rest in their garden as Dena.", True),
        ("Bira has triple as much rest in their animal as Dena.", False),
    ],
)
def test_mass_relation_uses_conditional_verb_role_and_pp_compatibility(
    text: str, matched: bool, registry
) -> None:
    assert (
        "arithmetic/times-as-much" in _matched_rules(text, registry)
    ) is matched


def test_conditional_form_and_excluded_role_are_explicit_schema_predicates() -> None:
    conditional = WherePredicate(
        bound_requires_form={
            "bound": "aux",
            "slot": "verb",
            "form": "bare",
        }
    )
    exclusion = WherePredicate(
        verb_role_compatible={
            "verb": "verb",
            "roles": ["item"],
            "verb_cat": "sell",
            "excluded_role_cat": "remnant",
        }
    )

    assert conditional.bound_requires_form is not None
    assert conditional.bound_requires_form.form == "bare"
    assert exclusion.verb_role_compatible is not None
    assert exclusion.verb_role_compatible.excluded_role_cat == "remnant"


def test_quantitative_verb_boundaries_keep_valid_neighboring_forms(
    registry,
) -> None:
    valid = {
        "arithmetic/anchored-relation-possessive-kinship-standard":
            "Apple has 20 more fish than your student.",
        "arithmetic/anaphoric-price-standard":
            "Animal is double that price.",
        "arithmetic/rest-of-pool": "Eron ate remainder.",
    }

    for rule_id, text in valid.items():
        assert rule_id in _matched_rules(text, registry)


@pytest.mark.parametrize(
    ("rule_id", "text"),
    [
        (
            "arithmetic/existential-premise",
            "There are 60 plums on tree.",
        ),
        (
            "arithmetic/existential-premise-distributive",
            "There are 60 plums in every garden.",
        ),
        (
            "arithmetic/existential-premise-bare",
            "There are 60 plums.",
        ),
        (
            "arithmetic/existential-premise-bare-conjoined",
            "There are 60 plums and 4 apples.",
        ),
        (
            "arithmetic/existential-premise-total",
            "There are 60 plums altogether.",
        ),
    ],
)
def test_existential_family_requires_agreeing_copulas(
    rule_id: str, text: str, registry
) -> None:
    assert rule_id in _matched_rules(text, registry)
    assert rule_id not in _matched_rules(
        text.replace("There are", "There gives"), registry
    )


@pytest.mark.parametrize(
    ("rule_id", "text"),
    [
        (
            "arithmetic/times-as-many-conjunct-elided-standard",
            "Hamster has 4 cans in my garden and once as many teachers.",
        ),
        (
            "arithmetic/times-as-many",
            "Tree received once as many apples in the garden as Dena.",
        ),
        (
            "arithmetic/fraction-as-many-elided-standard",
            "Pencil gave eight sixths as many trees in the garden.",
        ),
        (
            "arithmetic/times-as-many-possessive-kinship-standard",
            "Hamster lost double as many birds in my garden as my marble.",
        ),
    ],
)
def test_reviewed_quantity_pp_rules_keep_declared_locations(
    rule_id: str, text: str, registry
) -> None:
    assert rule_id in _matched_rules(text, registry)


def test_affine_mass_pp_requires_an_animate_determiner_for_named_subject(
    registry,
) -> None:
    rule_id = "arithmetic/affine-times-as-much"
    valid = (
        "Bira had 3 more than twice as much rest in her garden "
        "as your teacher Cato."
    )
    invalid = valid.replace("in her garden", "in its garden")

    assert rule_id in _matched_rules(valid, registry)
    assert rule_id not in _matched_rules(invalid, registry)


def test_explicit_rest_attribute_uses_declared_noun_compatibility(
    registry,
) -> None:
    rule_id = "arithmetic/partition-rest-attribute"

    assert rule_id in _matched_rules(
        "Rest of the apples were small.", registry
    )
    assert rule_id not in _matched_rules(
        "Rest of the ages were small.", registry
    )
    assert rule_id in _matched_rules("Rest were small.", registry)


def test_complex_affine_fraction_refuses_unframed_motion_verbs(
    registry,
) -> None:
    rule_id = "arithmetic/affine-fraction-as-many"
    valid = (
        "Fia has 9 less than seventeen fifths as many cookies "
        "in her garden as her friend Aven."
    )

    assert rule_id in _matched_rules(valid, registry)
    assert rule_id not in _matched_rules(
        valid.replace("Fia has", "Fia travels"), registry
    )


@pytest.mark.parametrize(
    ("text", "matched"),
    [
        ("Animal rose forty sixths fewer dollar.", False),
        ("Animal rose forty sixths more dollar.", True),
        ("Animal had forty sixths fewer dollar.", True),
    ],
)
def test_percent_change_scopes_directional_verb_polarity(
    text: str, matched: bool, registry
) -> None:
    assert (
        "arithmetic/percent-change-event" in _matched_rules(text, registry)
    ) is matched


def test_scoped_polarity_is_an_explicit_schema_predicate() -> None:
    predicate = WherePredicate(
        polarity_compatible={
            "slots": ["verb", "dir"],
            "categories": ["directional_change_verb", "delta"],
        }
    )

    assert predicate.polarity_compatible is not None
    assert predicate.polarity_compatible.slots == ["verb", "dir"]

    with pytest.raises(
        ValidationError, match="one category per slot"
    ):
        WherePredicate(
            polarity_compatible={
                "slots": ["verb", "dir"],
                "categories": [
                    "directional_change_verb",
                    "delta",
                    "comparative",
                ],
            }
        )
