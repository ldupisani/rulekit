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
from rulekit.generation import (
    GenerationError,
    generate_candidate,
    retest_candidate,
)
from rulekit.generation.sample import (
    _broader_lexical_domain,
    _load_fixtures,
)
from rulekit.kernel.engine import analyze, solve
from rulekit.kernel.model import (
    GroupTotal,
    PartitionQuantity,
    Quantity,
    Rate,
    Relation,
)
from rulekit.kernel.patterns import is_bare_verb_form


def _matched_rules(text: str, registry) -> set[str]:
    result = solve(text, registry)
    return {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


def test_fraction_within_whole_is_an_explicit_slot_qualifier() -> None:
    token = MatchToken(
        slot="f", type="fraction", fraction_within_whole=True
    )
    assert token.fraction_within_whole is True

    with pytest.raises(
        ValidationError,
        match="only qualifies a `type: fraction` slot",
    ):
        MatchToken(
            slot="n", type="number", fraction_within_whole=True
        )


def test_word_fraction_within_whole_is_an_explicit_slot_qualifier() -> None:
    token = MatchToken(
        slot="f", type="fraction", word_fraction_within_whole=True
    )
    assert token.word_fraction_within_whole is True

    with pytest.raises(
        ValidationError,
        match="only qualifies a `type: fraction` slot",
    ):
        MatchToken(
            slot="n", type="number", word_fraction_within_whole=True
        )


def test_positive_fraction_is_an_explicit_slot_qualifier() -> None:
    token = MatchToken(slot="f", type="fraction", fraction_positive=True)
    assert token.fraction_positive is True

    with pytest.raises(
        ValidationError,
        match="only qualifies a `type: fraction` slot",
    ):
        MatchToken(slot="n", type="number", fraction_positive=True)


def test_common_noun_role_is_an_explicit_entity_qualifier() -> None:
    token = MatchToken(
        slot="who", type="entity", common_noun_cat="quantity_holder"
    )
    assert token.common_noun_cat == "quantity_holder"

    with pytest.raises(
        ValidationError,
        match="only qualifies a `type: entity` slot",
    ):
        MatchToken(
            slot="who", type="noun", common_noun_cat="quantity_holder"
        )


def test_category_membership_agreement_is_a_closed_where_predicate() -> None:
    predicate = WherePredicate(
        same_category_membership={
            "slots": ["left", "right"],
            "cat": "timeperiod",
        }
    )
    assert predicate.same_category_membership is not None
    assert predicate.same_category_membership.slots == ["left", "right"]

    with pytest.raises(
        ValidationError, match="category membership agreement repeats a slot"
    ):
        WherePredicate(
            same_category_membership={
                "slots": ["left", "left"],
                "cat": "timeperiod",
            }
        )


def test_measure_holder_compatibility_is_a_closed_where_predicate() -> None:
    predicate = WherePredicate(
        measure_holder_compatible={
            "measure": "item",
            "holders": ["who", "std"],
            "allow_proper_name": True,
        }
    )
    assert predicate.measure_holder_compatible is not None
    assert predicate.measure_holder_compatible.holders == ["who", "std"]

    with pytest.raises(
        ValidationError, match="measure-holder compatibility repeats a holder"
    ):
        WherePredicate(
            measure_holder_compatible={
                "measure": "item",
                "holders": ["who", "who"],
            }
        )


POSITIVE_FRACTION_RULES = {
    "arithmetic/affine-fraction-as-many",
    "arithmetic/fraction-as-far",
    "arithmetic/fraction-as-many",
    "arithmetic/fraction-as-many-qualified-measures",
    "arithmetic/fraction-as-many-elided",
    "arithmetic/fraction-as-many-elided-standard",
    "arithmetic/fraction-as-much",
    "arithmetic/fraction-as-much-elided",
    "arithmetic/fraction-as-much-elided-standard",
    "arithmetic/fraction-delta-relation",
    "arithmetic/fraction-delta-relation-elided",
    "arithmetic/fraction-delta-relation-mass",
    "arithmetic/fraction-frame-relation",
    "arithmetic/goal-progress-fraction-needed",
    "arithmetic/percent-change-event",
    "arithmetic/percent-change-event-count",
}

WORD_FRACTION_COMPARISON_RULES = POSITIVE_FRACTION_RULES


def test_every_fraction_comparison_or_change_requires_positive_magnitude(
    registry,
) -> None:
    rules = {rule.id: rule for rule in registry.rules}
    actual = set()
    for rule in registry.rules:
        fraction_tokens = [
            token
            for token in rule.match.get("sentence", [])
            if token.slot == "f" and token.type == "fraction"
        ]
        if any(emit.fact in {"relation", "percent_change"} for emit in rule.emits):
            actual.update(rule.id for _ in fraction_tokens)
        for token in fraction_tokens:
            if rule.id in POSITIVE_FRACTION_RULES:
                assert token.fraction_positive is True

    assert actual == POSITIVE_FRACTION_RULES
    for rule_id in {
        "arithmetic/fraction-of-pool",
        "arithmetic/fraction-of-pronoun",
        "arithmetic/fraction-of-remnant",
        "arithmetic/partition-attribute-fraction",
        "arithmetic/partition-membership-fraction",
    }:
        token = next(
            token
            for token in rules[rule_id].match["sentence"]
            if token.slot == "f"
        )
        assert token.fraction_positive is False


def test_word_fraction_comparisons_stay_within_one_whole(registry) -> None:
    rules = {rule.id: rule for rule in registry.rules}

    for rule_id in WORD_FRACTION_COMPARISON_RULES:
        token = next(
            token
            for token in rules[rule_id].match["sentence"]
            if token.slot == "f"
        )
        assert token.word_fraction_within_whole is True

@pytest.mark.parametrize(
    ("rule_id", "zero", "positive"),
    [
        (
            "arithmetic/affine-fraction-as-many",
            "The teacher has 10 more than zero sixths as many pencils as Fia.",
            "The teacher has 10 more than half as many pencils as Fia.",
        ),
        (
            "arithmetic/fraction-as-many",
            "The teacher has zero sixths as many pencils as Fia.",
            "The teacher has half as many pencils as Fia.",
        ),
        (
            "arithmetic/fraction-delta-relation",
            "Bira has zero sixths more pencils than Fia.",
            "Bira has half more pencils than Fia.",
        ),
        (
            "arithmetic/percent-change-event",
            "Bira has zero sixths more money.",
            "Bira has half more money.",
        ),
    ],
)
def test_fraction_comparisons_reject_zero_but_keep_positive_neighbours(
    rule_id: str, zero: str, positive: str, registry
) -> None:
    assert rule_id not in _matched_rules(zero, registry)
    assert rule_id in _matched_rules(positive, registry)


@pytest.mark.parametrize(
    ("rule_id", "reviewed"),
    [
        (
            "arithmetic/as-many",
            "The bird be as many amounts in the pantry as the puzzle.",
        ),
        (
            "arithmetic/affine-times-as-much-elided",
            "Bira be 7 more than twice as much as Aven.",
        ),
        (
            "arithmetic/times-as-many-possessive-kinship-standard",
            "Dena travels twice as many grapes as your guardian.",
        ),
        (
            "arithmetic/times-the-number-of",
            "Librarian traveled in once the amount of apples as dog.",
        ),
        (
            "arithmetic/fraction-as-many",
            "The key had nine eighths as many birds with the rest as the hamster.",
        ),
    ],
)
def test_latest_arithmetic_reviews_retest_absent(
    rule_id: str, reviewed: str
) -> None:
    candidate = retest_candidate(
        load_project(Path("projects/curated")),
        rule_id=rule_id,
        sentence=reviewed,
        seed=0,
        origin="generated",
    )

    assert candidate.target_status == "absent"


def test_latest_arithmetic_review_boundaries_keep_ordinary_neighbours(
    registry,
) -> None:
    assert "arithmetic/as-many" in _matched_rules(
        "The bird has as many apples in the pantry as the rabbit.", registry
    )
    assert "arithmetic/affine-times-as-much-elided" in _matched_rules(
        "Bira has 7 more than twice as much as Aven.", registry
    )
    assert "arithmetic/times-as-many-possessive-kinship-standard" in (
        _matched_rules(
            "Dena travels twice as many times as your guardian.", registry
        )
    )
    assert "arithmetic/times-the-number-of" in _matched_rules(
        "The teacher has twice the number of apples as the guardian.",
        registry,
    )
    assert "arithmetic/fraction-as-many" in _matched_rules(
        "The teacher had three eighths as many birds in the garden as the hamster.",
        registry,
    )


@pytest.mark.parametrize(
    "text",
    [
        "The teacher had nine eighths as many birds as the hamster.",
        "The teacher had half as many birds with the rest as the hamster.",
    ],
)
def test_fraction_as_many_requires_a_bounded_fraction_and_nonremnant_pp(
    text: str, registry
) -> None:
    assert "arithmetic/fraction-as-many" not in _matched_rules(text, registry)


def test_affine_fraction_generation_refuses_zero_magnitude() -> None:
    project = load_project(Path("projects/curated"))
    rule_id = "arithmetic/affine-fraction-as-many"
    bindings = {
        "who": "the teacher",
        "verb": "has",
        "n": "10",
        "dir": "more",
        "item": "pencils",
        "std": "Fia",
    }

    with pytest.raises(GenerationError, match="no filler for f"):
        generate_candidate(
            project,
            rule_id=rule_id,
            seed=0,
            locked_bindings={**bindings, "f": "zero sixths"},
        )

    candidate = generate_candidate(
        project,
        rule_id=rule_id,
        seed=0,
        locked_bindings={**bindings, "f": "sixth"},
    )
    assert candidate.target_status == "matched"
    premise = next(item for item in candidate.premises if item.slot == "f")
    assert "strictly positive" in premise.reason


@pytest.mark.parametrize(
    ("rule_id", "valid", "invalid"),
    [
        (
            "arithmetic/fraction-of-pool",
            "Mary takes two thirds of the apples.",
            "Mary takes six thirds of the apples.",
        ),
        (
            "arithmetic/fraction-of-pronoun",
            "Mary takes two thirds of it.",
            "Mary takes six thirds of it.",
        ),
        (
            "arithmetic/fraction-of-remnant",
            "Mary takes two thirds of the remainder.",
            "Mary takes six thirds of the remainder.",
        ),
    ],
)
def test_fraction_of_one_whole_rejects_improper_fractions(
    rule_id: str, valid: str, invalid: str, registry
) -> None:
    assert rule_id in _matched_rules(valid, registry)
    assert rule_id not in _matched_rules(invalid, registry)


@pytest.mark.parametrize(
    "rule_id",
    [
        "arithmetic/fraction-of-pool",
        "arithmetic/fraction-of-pronoun",
        "arithmetic/fraction-of-remnant",
    ],
)
def test_fraction_of_whole_generation_refuses_improper_fraction(
    rule_id: str,
) -> None:
    project = load_project(Path("projects/curated"))

    with pytest.raises(GenerationError, match="no filler for f"):
        generate_candidate(
            project,
            rule_id=rule_id,
            seed=0,
            locked_bindings={"f": "six thirds"},
        )

    candidate = generate_candidate(
        project,
        rule_id=rule_id,
        seed=0,
        locked_bindings={"f": "two thirds"},
    )
    assert candidate.target_status in {"matched", "shadowed"}


@pytest.mark.parametrize(
    ("rule_id", "text"),
    [
        ("arithmetic/fraction-of-pool", "Mary take half of apples."),
        ("arithmetic/fraction-of-pronoun", "Mary take half of it."),
        (
            "arithmetic/fraction-of-remnant",
            "Mary take half of remainder.",
        ),
    ],
)
def test_fraction_of_whole_requires_subject_verb_agreement(
    rule_id: str, text: str, registry
) -> None:
    assert rule_id not in _matched_rules(text, registry)


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
            "6 of the animals are dogs.",
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
            "In 12 pounds Dena will be twice as old as her child Fia.",
        ),
        (
            "arithmetic/temporal-offset-age-future-intensified",
            "In 15 more friend Cato would be 3 friends old.",
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
            "Cato has 30 more than twice as many apples as Eron.",
        ),
        (
            "arithmetic/fraction-as-much-elided-standard",
            "Aven has seven tenths as much rest.",
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
            "The bird found 15 coins in the garden and twice that many.",
        ),
        (
            "arithmetic/anaphoric-multiplier-conjunct-many",
            "The bird found 15 coins in the garden and twice this many.",
        ),
        (
            "arithmetic/anaphoric-multiplier-conjunct-many",
            "Eron received 15 coins with the rest and twice that many.",
        ),
        (
            "arithmetic/times-as-many-conjunct",
            "Aven received 80 apples and thrice as many books as Bira.",
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


def test_integer_only_qualifies_number_slots() -> None:
    token = MatchToken(slot="year", type="number", integer=True)
    assert token.integer is True

    with pytest.raises(
        ValidationError,
        match="`integer` only qualifies a `type: number` slot",
    ):
        MatchToken(slot="item", type="counted", integer=True)


def test_numeric_bounds_qualify_scalar_and_counted_slots() -> None:
    assert MatchToken(
        slot="span", type="counted", value_min=1
    ).value_min == 1
    assert MatchToken(
        slot="span", cat="duration_measure", counted=True, value_min=1
    ).value_min == 1

    with pytest.raises(
        ValidationError,
        match="only qualify a `type: number` or counted slot",
    ):
        MatchToken(slot="item", type="noun", value_min=1)


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
        "arithmetic/anaphoric-multiplier-standard",
        "arithmetic/anaphoric-multiplier-standard-many",
        "arithmetic/anaphoric-multiplier-standard-much",
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
        "arithmetic/goal-desire-quantity",
        "arithmetic/times-the-number-of",
        "arithmetic/temporal-offset-age-future",
        "arithmetic/times-as-many-elided-standard",
        "arithmetic/times-as-many-elided",
        "arithmetic/partition-rest-membership",
        "arithmetic/fraction-as-many",
        "arithmetic/fraction-as-far",
        "arithmetic/fraction-as-many-elided",
        "arithmetic/fraction-delta-relation",
        "arithmetic/fraction-delta-relation-mass",
        "arithmetic/periodic-rate-every-span",
        "arithmetic/times-as-much",
        "arithmetic/fraction-as-much",
        "arithmetic/anchored-relation-possessive-kinship-standard",
        "arithmetic/anaphoric-price-standard",
        "arithmetic/times-as-many-conjunct-elided-standard",
        "arithmetic/times-as-many",
        "arithmetic/existential-premise",
        "arithmetic/existential-premise-bare",
        "arithmetic/existential-premise-bare-conjoined",
        "arithmetic/fraction-as-many-elided-standard",
        "arithmetic/rest-of-pool",
        "arithmetic/times-as-many-possessive-kinship-standard",
        "arithmetic/affine-times-as-much",
        "arithmetic/partition-rest-attribute",
        "arithmetic/affine-fraction-as-many",
        "arithmetic/percent-change-event",
        "arithmetic/percent-change-event-count",
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
        "It takes money 60 years to receive 13 animals.",
        "It takes the money 60 years to receive 13 animals.",
    ],
)
def test_duration_rate_rejects_nonparticipant_infinitive_actor(
    text: str, registry
) -> None:
    assert "arithmetic/extraposed-duration-rate" not in _matched_rules(
        text, registry
    )


def test_duration_rate_keeps_a_named_infinitive_actor(registry) -> None:
    text = "It takes Cato 60 years to receive 13 animals."
    assert "arithmetic/extraposed-duration-rate" in _matched_rules(
        text, registry
    )


def test_duration_rate_declares_the_infinitive_actor_boundaries(
    registry,
) -> None:
    rule = next(
        rule
        for rule in registry.rules
        if rule.id == "arithmetic/extraposed-duration-rate"
    )
    who = next(
        token
        for token in rule.match["sentence"]
        if isinstance(token, MatchToken) and token.slot == "who"
    )
    compatibility = next(
        predicate.verb_role_compatible
        for predicate in rule.where
        if predicate.verb_role_compatible is not None
    )

    assert who.referential is True
    assert who.bare_reference_category == "bare_entity_reference"
    assert compatibility.verb == "verb"
    assert compatibility.roles == ["who"]
    assert compatibility.verb_cat == "quantity_event_verb"
    assert compatibility.role_cat == "quantity_event_participant"
    assert registry.word_in_category(
        "teacher", compatibility.role_cat
    )
    assert not registry.word_in_category(
        "money", compatibility.role_cat
    )


def test_latest_duration_rate_review_cannot_be_regenerated() -> None:
    project = load_project(Path("projects/curated"))

    with pytest.raises(GenerationError, match="no filler for who"):
        generate_candidate(
            project,
            rule_id="arithmetic/extraposed-duration-rate",
            seed=2257502023170305,
            locked_bindings={"who": "money", "verb": "receive"},
        )

    retest = retest_candidate(
        project,
        rule_id="arithmetic/extraposed-duration-rate",
        sentence="It takes money 60 years to receive 13 animals.",
        seed=2257502023170305,
        origin="generated",
    )
    assert retest.target_status == "absent"


def test_duration_rate_generator_uses_a_nonmerging_actor_before_the_count() -> None:
    candidate = generate_candidate(
        load_project(Path("projects/curated")),
        rule_id="arithmetic/extraposed-duration-rate",
        seed=1103,
    )

    assert candidate.target_status == "matched"
    actor = next(
        premise for premise in candidate.premises if premise.slot == "who"
    )
    assert any(source["kind"] == "generation-fixture" for source in actor.sources)


@pytest.mark.parametrize(
    "text",
    [
        "The animal drops double as many as the hamster.",
        "The hamster drops double as many as the animal.",
        "Animals have double as many as hamsters.",
    ],
)
def test_comparison_roles_reject_category_member_overlap(
    text: str, registry
) -> None:
    assert "arithmetic/times-as-many-elided" not in _matched_rules(
        text, registry
    )


@pytest.mark.parametrize(
    "text",
    [
        "The dog drops twice as many as the hamster.",
        "Cato drops twice as many as the hamster.",
        "Cato's animal drops twice as many as Dena's hamster.",
    ],
)
def test_comparison_roles_keep_separate_entities(
    text: str, registry
) -> None:
    assert "arithmetic/times-as-many-elided" in _matched_rules(
        text, registry
    )


def test_event_role_compatibility_uses_surface_and_lemma(registry) -> None:
    rule_id = "arithmetic/times-as-many-elided"

    assert rule_id in _matched_rules(
        "The animal drops twice as many as Cato.", registry
    )
    assert rule_id not in _matched_rules(
        "The garden drops twice as many as Cato.", registry
    )


def test_category_nonoverlap_is_an_explicit_schema_predicate() -> None:
    predicate = WherePredicate(category_nonoverlap=["who", "std"])

    assert predicate.category_nonoverlap == ["who", "std"]
    with pytest.raises(ValidationError, match="repeats a slot"):
        WherePredicate(category_nonoverlap=["who", "who"])


def test_category_containment_is_an_explicit_directional_predicate() -> None:
    predicate = WherePredicate(
        category_contains={"collection": "coll", "members": ["attr"]}
    )

    assert predicate.category_contains is not None
    assert predicate.category_contains.collection == "coll"
    assert predicate.category_contains.members == ["attr"]
    with pytest.raises(ValidationError, match="repeats a member slot"):
        WherePredicate(
            category_contains={
                "collection": "coll",
                "members": ["attr", "attr"],
            }
        )
    with pytest.raises(ValidationError, match="reuse its collection"):
        WherePredicate(
            category_contains={"collection": "coll", "members": ["coll"]}
        )


def test_every_common_noun_comparison_declares_nonoverlap() -> None:
    registry = load_project(Path("projects/curated")).registry

    for rule in registry.rules:
        if not any(
            predicate.distinct == ["who", "std"]
            for predicate in rule.where
        ):
            continue
        slots: dict[str, MatchToken] = {}

        def collect(tokens: list[MatchToken]) -> None:
            for token in tokens:
                if token.slot is not None:
                    slots.setdefault(token.slot, token)
                if token.opt is not None:
                    collect(token.opt)

        sentence = rule.match.get("sentence", [])
        if sentence and isinstance(sentence[0], list):
            for alternative in sentence:
                collect(alternative)
        else:
            collect(sentence)
        if (
            slots.get("who") is not None
            and slots["who"].type == "entity"
            and slots.get("std") is not None
            and slots["std"].type == "entity"
        ):
            assert any(
                predicate.category_nonoverlap == ["who", "std"]
                for predicate in rule.where
            ), rule.id


def test_latest_category_overlap_review_cannot_be_regenerated() -> None:
    project = load_project(Path("projects/curated"))
    rule_id = "arithmetic/times-as-many-elided"

    with pytest.raises(GenerationError, match="no filler for who"):
        generate_candidate(
            project,
            rule_id=rule_id,
            seed=2257502023170308,
            locked_bindings={
                "who": "the animal",
                "verb": "drops",
                "k": "twice",
                "std": "the hamster",
            },
        )

    valid = generate_candidate(
        project,
        rule_id=rule_id,
        seed=2257502023170308,
        locked_bindings={
            "who": "the dog",
            "verb": "drops",
            "k": "twice",
            "std": "the hamster",
        },
    )
    overlap = next(
        premise
        for premise in valid.premises
        if premise.expression.startswith("category_nonoverlap(")
    )
    assert valid.target_status == "matched"
    assert overlap.status == "passed"
    assert "category/member containment" in overlap.reason

    retest = retest_candidate(
        project,
        rule_id=rule_id,
        sentence="The animal drops double as many as the hamster.",
        seed=2257502023170308,
        origin="generated",
    )
    assert retest.target_status == "absent"


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
        "The book is 30 inches smaller than Bira.",
        "The book is 30 pounds heavier than Bira.",
        "The gap was 30 years longer than the trip.",
    ],
)
def test_dimension_relation_keeps_compatible_units(
    text: str,
) -> None:
    registry = load_project(Path("projects/gsm8k")).registry
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
        (
            "Dena receives 30 years in the garden and twice as many "
            "on the tree."
        ),
        (
            "Dena receives 30 years with the rest and twice as many "
            "with the remainder."
        ),
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
            "In 12 years Dena will be twice as old as her child Fia.",
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
            "In 12 pounds Dena will be twice as old as Fia.",
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
def test_affine_count_frame_rejects_the_retired_as_standard_surface(
    frame: str, registry
) -> None:
    assert "arithmetic/affine-frame-relation-as-standard" not in _matched_rules(
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
    anchor = " Dena has 30 dollars."

    assert rule_id in _matched_rules(
        "Cato has 2 dollars less than twice the money Dena has." + anchor,
        registry,
    )
    assert rule_id not in _matched_rules(
        "Cato has 2 dollars less than twice the money Dena." + anchor,
        registry,
    )


def test_count_frame_relative_clause_can_state_a_duration_span(
    registry,
) -> None:
    assert "arithmetic/affine-frame-relation-clause" in _matched_rules(
        (
            "Cato finished 2 fewer than twice the number of puzzles "
            "Dena finished in 1 year."
        ),
        registry,
    )


def test_affine_frame_subject_and_echo_verbs_must_agree(registry) -> None:
    rule_id = "arithmetic/affine-frame-relation"

    assert rule_id in _matched_rules(
        "Teacher loses 19 fewer than once the amount of animals that bird loses.",
        registry,
    )
    assert rule_id not in _matched_rules(
        "Teacher lose 19 fewer than once the amount of animals that bird loses.",
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
        "The teacher has twice as many as their student Fia.", registry
    )
    assert "arithmetic/times-as-many-elided" not in _matched_rules(
        "The teacher has twice as many as its student Fia.", registry
    )


def test_explicit_membership_collection_requires_declared_superclass() -> None:
    registry = load_project(Path("projects/curated")).registry
    assert "arithmetic/partition-rest-membership" in _matched_rules(
        "The rest of the animals were rabbits.", registry
    )
    assert "arithmetic/partition-rest-membership" not in _matched_rules(
        "The rest of the rabbits were ages.", registry
    )


def test_agentive_verb_roles_are_conditional_and_pack_owned(registry) -> None:
    rule_id = "arithmetic/fraction-as-many"

    assert rule_id in _matched_rules(
        "The teacher spent half as many apples as Cato.", registry
    )
    assert rule_id not in _matched_rules(
        "The toy spent half as many apples as Cato.", registry
    )
    assert rule_id not in _matched_rules(
        "Cato spent half as many apples as the garden.", registry
    )
    assert rule_id in _matched_rules(
        "The garden has half as many apples as Cato.", registry
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

    plural_standard = WherePredicate(
        verb_role_compatible={
            "verb": "verb",
            "roles": ["std"],
            "verb_cat": "quantity_event_verb",
            "role_cat": "quantity_event_participant",
            "allow_plural_class": True,
        }
    )
    assert plural_standard.verb_role_compatible is not None
    assert plural_standard.verb_role_compatible.allow_plural_class is True

    with pytest.raises(
        ValidationError,
        match="plural comparison classes require a positive role category",
    ):
        WherePredicate(
            verb_role_compatible={
                "verb": "verb",
                "roles": ["item"],
                "verb_cat": "sell",
                "excluded_role_cat": "remnant",
                "allow_plural_class": True,
            }
        )


def test_finite_form_is_an_explicit_scalar_verb_qualifier() -> None:
    token = MatchToken(
        slot="want", cat="finite_infinitival_goal_predicate", finite_form=True
    )
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
            cat="finite_infinitival_goal_predicate",
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
        "The student should gets 12 hamsters every 6 years.",
        "The student should get 12 hamsters some 6 years.",
        "The student should get 12 hamsters every 6 apples.",
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
        "The student should get 12 hamsters every 6 years.",
        "The student gets 12 hamsters every 6 years.",
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
    assert bindings["span"].endswith(
        (
            " minute", " minutes", " hour", " hours", " day", " days",
            " week", " weeks", " year", " years",
        )
    )


@pytest.mark.parametrize(
    ("text", "matched"),
    [
        ("Bira sells thrice as much rest as Dena.", False),
        ("Bira sells thrice as much litter in their garden as Dena.", True),
        ("Bira has thrice as much rest in their garden as Dena.", True),
        ("Bira has thrice as much rest in their animal as Dena.", False),
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
            "The teacher has 20 more fish than your student.",
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
            "There are 60 plums on the tree.",
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
            "The hamster has 4 cans in my garden and twice as many teachers.",
        ),
        (
            "arithmetic/times-as-many",
            "The teacher received twice as many apples in the garden as Dena.",
        ),
        (
            "arithmetic/fraction-as-many-elided-standard",
            "The student gave five sixths as many trees in the garden.",
        ),
        (
            "arithmetic/times-as-many-possessive-kinship-standard",
            "The hamster lost twice as many birds in my garden as my teacher.",
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
        "The rest of the apples were small.", registry
    )
    assert rule_id not in _matched_rules(
        "The rest of the ages were small.", registry
    )
    assert rule_id in _matched_rules("The rest were small.", registry)


def test_complex_affine_fraction_refuses_unframed_motion_verbs(
    registry,
) -> None:
    rule_id = "arithmetic/affine-fraction-as-many"
    valid = (
        "Fia has 9 less than three fifths as many cookies "
        "in her garden as her friend Aven."
    )

    assert rule_id in _matched_rules(valid, registry)
    assert rule_id not in _matched_rules(
        valid.replace("Fia has", "Fia travels"), registry
    )


@pytest.mark.parametrize(
    ("rule_id", "text", "matched"),
    [
        (
            "arithmetic/percent-change-event",
            "Teacher own nineteen eighths less dollar.",
            False,
        ),
        (
            "arithmetic/percent-change-event",
            "Teacher owns one eighth less money.",
            True,
        ),
        (
            "arithmetic/percent-change-event-count",
            "Teacher owns one eighth fewer dollars.",
            True,
        ),
        (
            "arithmetic/percent-change-event",
            "Teacher owns one eighth fewer dollars.",
            False,
        ),
        (
            "arithmetic/percent-change-event-count",
            "Teacher owns one eighth less money.",
            False,
        ),
        (
            "arithmetic/percent-change-event",
            "Teacher owns nineteen eighths less money.",
            False,
        ),
        (
            "arithmetic/percent-change-event-count",
            "Teacher owns nineteen eighths fewer dollars.",
            False,
        ),
        (
            "arithmetic/percent-change-event",
            "Animal rose forty sixths less money.",
            False,
        ),
        (
            "arithmetic/percent-change-event",
            "Animal rose forty sixths more money.",
            False,
        ),
        (
            "arithmetic/percent-change-event-count",
            "Animal had forty sixths more dollars.",
            False,
        ),
        (
            "arithmetic/percent-change-event",
            "Animal rose 667 percent more money.",
            True,
        ),
        (
            "arithmetic/percent-change-event-count",
            "Animal had 667 percent more dollars.",
            True,
        ),
    ],
)
def test_percent_change_enforces_agreement_countability_and_safe_polarity(
    rule_id: str, text: str, matched: bool, registry
) -> None:
    assert (rule_id in _matched_rules(text, registry)) is matched


def test_latest_percent_change_review_retests_absent() -> None:
    candidate = retest_candidate(
        load_project(Path("projects/curated")),
        rule_id="arithmetic/percent-change-event",
        sentence="Sticker own nineteen eighths less dollar.",
        seed=912618241230539,
        origin="generated",
    )

    assert candidate.target_status == "absent"


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


def test_proportional_delta_is_an_explicit_schema_predicate() -> None:
    predicate = WherePredicate(
        proportional_delta_compatible={
            "fraction": "f",
            "direction": "dir",
            "direction_cat": "delta",
        }
    )

    assert predicate.proportional_delta_compatible is not None
    assert predicate.proportional_delta_compatible.fraction == "f"

    with pytest.raises(
        ValidationError, match="different fraction/direction slots"
    ):
        WherePredicate(
            proportional_delta_compatible={
                "fraction": "f",
                "direction": "f",
                "direction_cat": "delta",
            }
        )


@pytest.mark.parametrize(
    "text",
    [
        "Bira finds 40 older than once Fia's fish.",
        "Cato walked 90 younger than once Bira's flower.",
        "Fia need 20 fewer than once Cato's pencil.",
        "Aven owns 11 older than twice Fia's apple.",
        # Each boundary is independently observable, not only in the exact
        # reviewed combinations.
        "Bira has 40 more than once Fia's fish.",
        "Bira has 40 more than twice Fia's apple.",
        "Bira finds 40 more than twice Fia's apples.",
        "Bira was 40 more than twice Fia's apples.",
        "Bira has 40 less than twice Fia's apples.",
        "Fia has 40 more than twice Fia's apples.",
    ],
)
def test_affine_possessive_relation_rejects_reviewed_boundary_defects(
    text: str, registry
) -> None:
    assert (
        "arithmetic/affine-times-as-many-possessive-standard"
        not in _matched_rules(text, registry)
    )


@pytest.mark.parametrize(
    "text",
    [
        "Bira has 40 more than twice Fia's fish.",
        "Aven owns 11 fewer than triple Fia's apples.",
    ],
)
def test_affine_possessive_relation_keeps_state_count_neighbours(
    text: str, registry
) -> None:
    assert (
        "arithmetic/affine-times-as-many-possessive-standard"
        in _matched_rules(text, registry)
    )


@pytest.mark.parametrize(
    ("text", "matched"),
    [
        ("Bira has 40 less than twice Fia's rest.", True),
        ("Bira owns 40 more than triple Fia's rest.", True),
        ("Bira has 40 fewer than twice Fia's rest.", False),
        ("Bira has 40 less than twice Fia's rests.", False),
        ("Fia has 40 less than twice Fia's rest.", False),
    ],
)
def test_affine_possessive_mass_relation_has_its_own_countability_boundary(
    text: str, matched: bool, registry
) -> None:
    assert (
        "arithmetic/affine-times-as-much-possessive-standard"
        in _matched_rules(text, registry)
    ) is matched


def test_affine_possessive_relation_still_emits_the_scoped_relation(
    registry,
) -> None:
    result = solve(
        "Bira has 40 more than twice Fia's fish.",
        registry,
    )
    relation = next(
        fact
        for fact in result.store.by_kind(Relation)
        if fact.provenance.source
        == "arithmetic/affine-times-as-many-possessive-standard"
    )

    assert relation.subject == "bira"
    assert relation.standard == "fia"
    assert relation.measure == "fish"
    assert relation.factor == 2
    assert relation.offset == 40
    assert relation.verb == "have"


@pytest.mark.parametrize(
    ("rule_id", "valid", "invalid"),
    [
        (
            "arithmetic/times-as-many-possessive-standard",
            "Bira has twice Fia's apples.",
            "Fia has twice Fia's apples.",
        ),
        (
            "arithmetic/times-as-much-possessive-standard",
            "Bira has twice Fia's rest.",
            "Fia has twice Fia's rest.",
        ),
    ],
)
def test_possessive_ratio_siblings_keep_subject_and_owner_distinct(
    rule_id: str, valid: str, invalid: str, registry
) -> None:
    assert rule_id in _matched_rules(valid, registry)
    assert rule_id not in _matched_rules(invalid, registry)


def test_entity_owner_distinction_is_an_explicit_schema_predicate() -> None:
    predicate = WherePredicate(
        distinct_from_owner={"entity": "who", "possessed": "std"}
    )

    assert predicate.distinct_from_owner is not None
    assert predicate.distinct_from_owner.entity == "who"
    assert predicate.distinct_from_owner.possessed == "std"


@pytest.mark.parametrize(
    "rule_id",
    [
        "arithmetic/times-as-many-possessive-standard",
        "arithmetic/times-as-much-possessive-standard",
        "arithmetic/affine-times-as-many-possessive-standard",
        "arithmetic/affine-times-as-much-possessive-standard",
    ],
)
def test_possessive_ratio_generation_respects_owner_and_multiplier_boundaries(
    rule_id: str,
) -> None:
    project = load_project(Path("projects/curated"))

    for seed in range(16):
        candidate = generate_candidate(project, rule_id=rule_id, seed=seed)
        bindings = {
            row.slot: row.binding
            for row in candidate.premises
            if row.slot is not None
        }
        assert candidate.target_status == "matched"
        assert bindings["k"] != "once"
        assert bindings["who"].casefold() != bindings["std"].split(
            "'", 1
        )[0].casefold()


@pytest.mark.parametrize(
    "text",
    [
        "Fia travels twice as much rest at his number.",
        "Fia has twice as much rest at his number.",
        "Fia travels twice as much rest.",
    ],
)
def test_elided_mass_standard_rejects_reviewed_verb_and_pp_defects(
    text: str, registry
) -> None:
    assert (
        "arithmetic/times-as-much-elided-standard"
        not in _matched_rules(text, registry)
    )


@pytest.mark.parametrize(
    "text",
    [
        "Fia has twice as much rest.",
        "Fia has twice as much rest in her garden.",
    ],
)
def test_elided_mass_standard_keeps_declared_neighbours(
    text: str, registry
) -> None:
    assert (
        "arithmetic/times-as-much-elided-standard"
        in _matched_rules(text, registry)
    )


def test_comparative_need_is_a_dedicated_premise_relation(registry) -> None:
    result = solve("Fia needs 20 fewer pencils than Cato.", registry)
    rule_id = "arithmetic/goal-need-comparative-quantity"
    relation = next(
        fact
        for fact in result.store.by_kind(Relation)
        if fact.provenance.source == rule_id
    )

    assert rule_id in _matched_rules(
        "Fia needs 20 fewer pencils than Cato.", registry
    )
    assert relation.subject == "fia"
    assert relation.standard == "cato"
    assert relation.measure == "pencil"
    assert relation.factor == 1
    assert relation.offset == -20
    assert relation.verb == "need"


@pytest.mark.parametrize(
    "text",
    [
        "Fia need 20 fewer pencils than Cato.",
        "Fia needs 20 less pencils than Cato.",
        "Fia needs 20 younger pencils than Cato.",
        "Fia needs 20 fewer pencil than Cato.",
        "Fia needs 20 fewer pencils than Fia.",
    ],
)
def test_comparative_need_rejects_agreement_and_frame_defects(
    text: str, registry
) -> None:
    assert (
        "arithmetic/goal-need-comparative-quantity"
        not in _matched_rules(text, registry)
    )


def test_comparative_need_count_and_noun_agree(registry) -> None:
    rule_id = "arithmetic/goal-need-comparative-quantity"

    assert rule_id not in _matched_rules(
        "John needs 1 fewer shoppers than Mary.", registry
    )
    assert rule_id in _matched_rules(
        "John needs 1 fewer shopper than Mary.", registry
    )
    assert rule_id not in _matched_rules(
        "John needs 2 fewer shopper than Mary.", registry
    )
    assert rule_id in _matched_rules(
        "John needs 2 fewer shoppers than Mary.", registry
    )


def test_comparative_need_generation_respects_count_and_noun_agreement() -> None:
    project = load_project(Path("projects/curated"))
    rule_id = "arithmetic/goal-need-comparative-quantity"

    singular = generate_candidate(
        project,
        rule_id=rule_id,
        seed=907190546063108,
        locked_bindings={
            "who": "John",
            "need": "needs",
            "n": "1",
            "dir": "fewer",
            "item": "shopper",
            "std": "Mary",
        },
    )
    assert singular.target_status == "matched"

    with pytest.raises(GenerationError, match="no filler for item"):
        generate_candidate(
            project,
            rule_id=rule_id,
            seed=907190546063108,
            locked_bindings={
                "who": "John",
                "need": "needs",
                "n": "1",
                "dir": "fewer",
                "item": "shoppers",
                "std": "Mary",
            },
        )


def test_declared_plural_morphology_does_not_inherit_an_unlicensed_modal(
    registry,
) -> None:
    reading = analyze("Cato needs 16 fewer cans than Eron.", registry)
    cans = next(unit for unit in reading.units if unit.surface == "cans")

    assert cans.senses() == ["noun"]
    assert (
        "arithmetic/goal-need-comparative-quantity"
        in _matched_rules("Cato needs 16 fewer cans than Eron.", registry)
    )


def test_declared_plural_keeps_a_surface_declared_verb_reading(registry) -> None:
    reading = analyze("A book costs three times that price.", registry)
    costs = next(unit for unit in reading.units if unit.surface == "costs")

    assert costs.senses() == ["verb"]


@pytest.mark.parametrize(
    "text",
    [
        "Plum won 4 older than thrice dollar Dena won.",
        "Plum won 4 dollars older than thrice the money Dena won.",
        "Plum won 4 dollars more than thrice the dollar Dena won.",
        "Plum won 4 dollars more than thrice money Dena won.",
    ],
)
def test_affine_currency_clause_rejects_reviewed_frame_defects(
    text: str, registry
) -> None:
    assert (
        "arithmetic/affine-item-relation-clause"
        not in _matched_rules(text, registry)
    )


def test_affine_currency_clause_keeps_the_mass_money_frame(registry) -> None:
    assert "arithmetic/affine-item-relation-clause" in _matched_rules(
        "Cato won 4 dollars more than thrice the money Dena won.",
        registry,
    )


@pytest.mark.parametrize(
    "text",
    [
        "Mary owns ninety sixths older dog on their remainder than her friend Eron.",
        "Mary owns two fifths older dogs than Eron.",
        "Mary owns two fifths more dog than Eron.",
        "Mary owns two fifths more dogs on the remainder than Eron.",
    ],
)
def test_fraction_delta_relation_rejects_reviewed_frame_defects(
    text: str, registry
) -> None:
    assert (
        "arithmetic/fraction-delta-relation"
        not in _matched_rules(text, registry)
    )


def test_fraction_delta_relation_keeps_count_and_compatible_pp_neighbours(
    registry,
) -> None:
    rule_id = "arithmetic/fraction-delta-relation"

    assert rule_id in _matched_rules(
        "Mary owns two fifths more dogs than Eron.", registry
    )
    assert rule_id in _matched_rules(
        "Mary owns two fifths fewer dogs in the garden than Eron.", registry
    )


def test_fraction_delta_count_and_mass_siblings_are_disjoint() -> None:
    registry = load_project(Path("projects/gsm8k")).registry
    count_id = "arithmetic/fraction-delta-relation"
    mass_id = "arithmetic/fraction-delta-relation-mass"

    assert count_id in _matched_rules(
        "Mary owns two fifths fewer dogs than Eron.", registry
    )
    assert mass_id not in _matched_rules(
        "Mary owns two fifths fewer dogs than Eron.", registry
    )
    assert mass_id in _matched_rules(
        "Mary owns two fifths less chicken than Eron.", registry
    )
    assert count_id not in _matched_rules(
        "Mary owns two fifths less chicken than Eron.", registry
    )
    assert not {
        count_id,
        mass_id,
    } & _matched_rules("Mary owns two fifths fewer chicken than Eron.", registry)


def test_fraction_delta_mass_rejects_the_latest_reviewed_composition(
    registry,
) -> None:
    rule_id = "arithmetic/fraction-delta-relation-mass"

    assert rule_id not in _matched_rules(
        (
            "Cato spends nineteen tenths less rest with its remainder "
            "than your friend Eron."
        ),
        registry,
    )


@pytest.mark.parametrize(
    ("rule_id", "text"),
    [
        (
            "arithmetic/fraction-delta-relation-mass",
            "Cato spends one tenth less rest than Eron.",
        ),
        (
            "arithmetic/fraction-delta-relation-mass",
            "Cato spends one tenth less money with its remainder than Eron.",
        ),
        (
            "arithmetic/fraction-delta-relation",
            "Mary spends one tenth fewer dogs than Eron.",
        ),
        (
            "arithmetic/fraction-delta-relation",
            "Mary owns one tenth fewer dogs with the remainder than Eron.",
        ),
    ],
)
def test_fraction_delta_rejects_incompatible_objects_and_remnant_pps(
    rule_id: str, text: str, registry
) -> None:
    assert rule_id not in _matched_rules(text, registry)


@pytest.mark.parametrize(
    ("rule_id", "text"),
    [
        (
            "arithmetic/fraction-delta-relation-mass",
            "Cato gets one tenth less rest than Eron.",
        ),
        (
            "arithmetic/fraction-delta-relation-mass",
            "Cato spends one tenth less money than Eron.",
        ),
        (
            "arithmetic/fraction-delta-relation-mass",
            "Cato spends one tenth less money in the garden than Eron.",
        ),
        (
            "arithmetic/fraction-delta-relation",
            "Mary spends one tenth fewer dollars than Eron.",
        ),
        (
            "arithmetic/fraction-delta-relation",
            "Mary owns one tenth fewer dogs in the garden than Eron.",
        ),
    ],
)
def test_fraction_delta_keeps_compatible_mass_count_and_location_neighbours(
    rule_id: str, text: str, registry
) -> None:
    assert rule_id in _matched_rules(text, registry)


@pytest.mark.parametrize(
    (
        "rule_id",
        "word_decrease",
        "word_increase",
        "percent_decrease",
        "percent_increase",
    ),
    [
        (
            "arithmetic/fraction-delta-relation-mass",
            "Cato gets eleven tenths less rest than Eron.",
            "Cato gets eleven tenths more rest than Eron.",
            "Cato gets 110 percent less rest than Eron.",
            "Cato gets 110 percent more rest than Eron.",
        ),
        (
            "arithmetic/fraction-delta-relation",
            "Mary owns eleven tenths fewer dogs than Eron.",
            "Mary owns eleven tenths more dogs than Eron.",
            "Mary owns 110 percent fewer dogs than Eron.",
            "Mary owns 110 percent more dogs than Eron.",
        ),
        (
            "arithmetic/fraction-delta-relation-elided",
            "Mary owns eleven tenths less than Eron.",
            "Mary owns eleven tenths more than Eron.",
            "Mary owns 110 percent less than Eron.",
            "Mary owns 110 percent more than Eron.",
        ),
    ],
)
def test_improper_word_fractions_decline_but_percent_increases_remain_unbounded(
    rule_id: str,
    word_decrease: str,
    word_increase: str,
    percent_decrease: str,
    percent_increase: str,
    registry,
) -> None:
    assert rule_id not in _matched_rules(word_decrease, registry)
    assert rule_id not in _matched_rules(word_increase, registry)
    assert rule_id not in _matched_rules(percent_decrease, registry)
    assert rule_id in _matched_rules(percent_increase, registry)


def test_fraction_delta_mass_generation_respects_composed_boundaries() -> None:
    project = load_project(Path("projects/curated"))
    rule_id = "arithmetic/fraction-delta-relation-mass"

    for seed in range(32):
        candidate = generate_candidate(project, rule_id=rule_id, seed=seed)
        bindings = candidate.requested_bindings
        relation = next(
            fact for fact in candidate.facts if fact["type"] == "Relation"
        )

        assert candidate.target_status == "matched"
        assert 0.0 <= relation["fields"]["factor"] <= 2.0
        if project.registry.word_in_category(
            bindings["verb"].casefold(), "spend_verb"
        ):
            assert project.registry.word_in_category(
                bindings["item"].casefold(), "currency"
            )
        if "pp_prep" in bindings:
            assert not project.registry.word_in_category(
                bindings["pp_prep"].casefold(),
                "quantity_remainder_preposition",
            )


@pytest.mark.parametrize(
    "rule_id",
    [
        "arithmetic/fraction-delta-relation-mass",
        "arithmetic/as-many",
        "arithmetic/fraction-of-remnant",
    ],
)
def test_numeric_homograph_is_not_advertised_as_a_verb_filler(
    rule_id: str,
) -> None:
    project = load_project(Path("projects/curated"))

    with pytest.raises(GenerationError, match="no filler for verb"):
        generate_candidate(
            project,
            rule_id=rule_id,
            seed=0,
            locked_bindings={"verb": "triple"},
        )

    candidate = generate_candidate(
        project,
        rule_id=rule_id,
        seed=0,
        locked_bindings={"verb": "has"},
    )
    assert candidate.target_status in {"matched", "shadowed"}
    assert candidate.requested_bindings["verb"] == "has"


def test_latest_fraction_of_remnant_review_retests_absent() -> None:
    candidate = retest_candidate(
        load_project(Path("projects/curated")),
        rule_id="arithmetic/fraction-of-remnant",
        sentence="Mary triple six thirds of remainder.",
        seed=2269014546521219,
        origin="generated",
    )

    assert candidate.target_status == "absent"


def test_stated_need_goal_requires_subject_verb_agreement(registry) -> None:
    rule_id = "arithmetic/goal-need-quantity"

    assert rule_id not in _matched_rules("Eron need 15 apples.", registry)
    assert rule_id in _matched_rules("Eron needs 15 apples.", registry)
    assert rule_id in _matched_rules("Eron needed 15 apples.", registry)


def test_stated_need_generation_refuses_locked_agreement_mismatch() -> None:
    project = load_project(Path("projects/curated"))
    rule_id = "arithmetic/goal-need-quantity"

    with pytest.raises(GenerationError, match="no filler for need"):
        generate_candidate(
            project,
            rule_id=rule_id,
            seed=0,
            locked_bindings={
                "who": "Eron",
                "need": "need",
                "item": "15 apples",
            },
        )

    candidate = generate_candidate(
        project,
        rule_id=rule_id,
        seed=0,
        locked_bindings={
            "who": "Eron",
            "need": "needs",
            "item": "15 apples",
        },
    )
    assert candidate.target_status == "matched"


@pytest.mark.parametrize(
    "text",
    [
        "Mary gets twice as many.",
        "Mary gets twice that many.",
        "Mary gets twice this many.",
        "Mary gets twice as much.",
        "Mary gets twice that much.",
        "Mary gets twice this much.",
    ],
)
def test_anaphoric_multiplier_requires_a_grammatical_introducer(
    text: str, registry
) -> None:
    assert {
        "arithmetic/anaphoric-multiplier-standard-many",
        "arithmetic/anaphoric-multiplier-standard-much",
        "arithmetic/anaphoric-multiplier-standard-as-many",
        "arithmetic/anaphoric-multiplier-standard-as-much",
    } & _matched_rules(text, registry)


@pytest.mark.parametrize(
    "text",
    [
        "Mary gets twice many.",
        "Mary gets twice much.",
        "Mary gets twice amount.",
        "The scarf costs twice price.",
    ],
)
def test_anaphoric_multiplier_rejects_bare_heads(
    text: str, registry
) -> None:
    assert not {
        "arithmetic/anaphoric-multiplier-standard-many",
        "arithmetic/anaphoric-multiplier-standard-much",
        "arithmetic/anaphoric-multiplier-standard-as-many",
        "arithmetic/anaphoric-multiplier-standard-as-much",
        "arithmetic/anaphoric-multiplier-standard",
        "arithmetic/anaphoric-price-standard",
    } & _matched_rules(text, registry)


@pytest.mark.parametrize(
    ("rule_id", "text"),
    [
        (
            "arithmetic/anaphoric-multiplier-standard-as-many",
            (
                "Population received thrice as many trees at your area "
                "as pencil."
            ),
        ),
        (
            "arithmetic/anaphoric-multiplier-standard-as-many",
            "Mary gets twice as many apples in the garden as Eron.",
        ),
        (
            "arithmetic/anaphoric-multiplier-standard-as-much",
            "Mary gets twice as much money in the purse as Eron.",
        ),
    ],
)
def test_anaphoric_multiplier_does_not_claim_an_explicit_item_prefix(
    rule_id: str, text: str, registry
) -> None:
    assert rule_id not in _matched_rules(text, registry)


def test_generation_fact_exposes_emit_expression_and_bindings() -> None:
    project = load_project(Path("projects/curated"))
    candidate = retest_candidate(
        project,
        rule_id="arithmetic/fraction-delta-relation",
        sentence="Mary owns two fifths more dogs than Eron.",
        seed=0,
    )
    relation = next(
        fact for fact in candidate.facts if fact["type"] == "Relation"
    )

    assert relation["fields"]["factor"] == pytest.approx(1.4)
    assert relation["derivation"]["templates"]["factor"] == (
        "1 + f * sign(dir)"
    )
    assert relation["derivation"]["bindings"]["f"] == "two fifths"
    assert relation["derivation"]["bindings"]["dir"] == "more"


@pytest.mark.parametrize(
    ("rule_id", "text"),
    [
        (
            "arithmetic/times-as-many-conjunct-elided-item",
            "Plum traveled 90 cards on her garden and thrice as many.",
        ),
        (
            "arithmetic/existential-premise",
            "There are 40 fish of rabbit.",
        ),
        (
            "arithmetic/affine-fraction-as-many",
            "Marble found 2 less than nine tenths as many animals as area.",
        ),
        (
            "arithmetic/fraction-as-much",
            "Dena ate sixty halves as much money to the plum as her teacher Fia.",
        ),
        (
            "arithmetic/fraction-as-many-elided",
            "Fia sells eleven thirds as many as inch.",
        ),
    ],
)
def test_latest_reviewed_comparative_surfaces_are_rejected(
    rule_id: str, text: str, registry
) -> None:
    assert rule_id not in _matched_rules(text, registry)


def test_received_comparison_requires_referential_event_participants(
    registry,
) -> None:
    rule_id = "arithmetic/times-as-many"
    anaphoric_rule_id = "arithmetic/anaphoric-multiplier-standard-many"
    anaphoric_as_rule_id = (
        "arithmetic/anaphoric-multiplier-standard-as-many"
    )

    # The reviewed sentence fails independently on bare common-noun reference,
    # an implausible event participant, and the preposition/place pairing.
    reviewed_matches = _matched_rules(
        (
            "Population received thrice as many trees at your area "
            "as pencil."
        ),
        registry,
    )
    assert rule_id not in reviewed_matches
    assert anaphoric_rule_id not in reviewed_matches
    assert anaphoric_as_rule_id not in reviewed_matches

    # A demonstrative anaphor may still state its measure; this is the
    # legitimate DEV-train neighbour that requires the rule-family split.
    demonstrative_matches = _matched_rules(
        "Jerome lost three times that many pounds.", registry
    )
    assert anaphoric_rule_id in demonstrative_matches
    assert anaphoric_as_rule_id not in demonstrative_matches
    assert rule_id not in _matched_rules(
        (
            "The population received thrice as many trees in your area "
            "as the pencil."
        ),
        registry,
    )
    assert rule_id not in _matched_rules(
        (
            "The teacher received thrice as many trees at your area "
            "as the student."
        ),
        registry,
    )
    assert rule_id in _matched_rules(
        (
            "The teacher received thrice as many trees in your area "
            "as the student."
        ),
        registry,
    )


def test_plain_as_many_emits_an_equal_quantity_relation(registry) -> None:
    rule_id = "arithmetic/as-many"
    sentence = "Tom buys as many roses as Mary."
    result = solve(sentence, registry)
    relation = next(
        fact
        for fact in result.store.by_kind(Relation)
        if fact.provenance.source == rule_id
    )

    assert rule_id in _matched_rules(sentence, registry)
    assert "arithmetic/times-as-many" not in _matched_rules(
        sentence, registry
    )
    assert relation.subject == "tom"
    assert relation.standard == "mary"
    assert relation.measure == "rose"
    assert relation.factor == 1.0
    assert relation.offset == 0.0
    assert relation.verb == "buy"


def test_plain_and_multiplied_as_many_forms_are_structurally_disjoint(
    registry,
) -> None:
    multiplied = "Tom buys twice as many roses as Mary."

    assert "arithmetic/times-as-many" in _matched_rules(
        multiplied, registry
    )
    assert "arithmetic/as-many" not in _matched_rules(multiplied, registry)


def test_plain_as_many_relation_answers_from_the_standard_quantity(
    registry,
) -> None:
    result = solve(
        (
            "Mary buys 7 roses. Tom buys as many roses as Mary. "
            "How many roses does Tom buy?"
        ),
        registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == 7


def test_plain_as_many_rule_generates_a_reviewable_match() -> None:
    candidate = generate_candidate(
        load_project(Path("projects/curated")),
        rule_id="arithmetic/as-many",
        seed=0,
    )

    assert candidate.target_status == "matched"


def test_event_role_boundary_does_not_restrict_possession_states(
    registry,
) -> None:
    assert "arithmetic/times-as-many" in _matched_rules(
        (
            "The garden has thrice as many trees in your area "
            "as the teacher."
        ),
        registry,
    )
    assert "arithmetic/times-as-many" in _matched_rules(
        "Cato has thrice as many apples as pencils.", registry
    )
    assert "arithmetic/times-as-many" not in _matched_rules(
        "Cato has thrice as many apples as pencil.", registry
    )


def test_mined_quarter_morphology_declares_its_plural() -> None:
    registry = load_project(Path("projects/gsm8k")).registry

    assert registry.singular_to_plural["quarter"] == "quarters"
    assert registry.plural_to_singular["quarters"] == "quarter"


def test_received_comparison_generation_uses_declared_participants() -> None:
    project = load_project(Path("projects/curated"))
    candidate = generate_candidate(
        project,
        rule_id="arithmetic/times-as-many",
        seed=2,
        locked_bindings={
            "who": "Cato",
            "verb": "received",
            "pp_prep": "in",
            "pp_det": "your",
            "pp_obj": "area",
            "std": "the hamster",
        },
    )
    bindings = {
        row.slot: row.binding
        for row in candidate.premises
        if row.slot is not None
    }

    assert candidate.target_status == "matched"
    assert candidate.sentence.startswith("Cato received")
    assert bindings["std"] == "hamster"
    assert "in your area" in candidate.sentence


def test_event_role_boundary_follows_a_resolved_name_pronoun(registry) -> None:
    assert "arithmetic/times-as-many" in _matched_rules(
        (
            "Cato has 10 apples. He received twice as many books "
            "as Dena."
        ),
        registry,
    )


def test_elided_item_conjunct_requires_paired_compatible_contexts(
    registry,
) -> None:
    rule_id = "arithmetic/times-as-many-conjunct-elided-item"

    assert rule_id in _matched_rules(
        "Cato has 90 cards and thrice as many.", registry
    )
    assert rule_id in _matched_rules(
        (
            "Cato has 90 cards in her garden and thrice as many "
            "on the tree."
        ),
        registry,
    )
    assert rule_id not in _matched_rules(
        "Cato has 90 cards in her garden and thrice as many.", registry
    )
    assert rule_id not in _matched_rules(
        (
            "Cato traveled 90 cards in her garden and thrice as many "
            "on the tree."
        ),
        registry,
    )


def test_located_existential_requires_a_referential_compatible_place(
    registry,
) -> None:
    rule_id = "arithmetic/existential-premise"

    assert rule_id in _matched_rules(
        "There are 40 fish in the garden.", registry
    )
    assert rule_id in _matched_rules(
        "There are 40 fish in a garden.", registry
    )
    assert rule_id in _matched_rules(
        "There are 40 fish on her tree.", registry
    )
    assert rule_id not in _matched_rules(
        "There are 40 fish in garden.", registry
    )
    assert rule_id not in _matched_rules(
        "There are 40 fish in the rabbit.", registry
    )


@pytest.mark.parametrize(
    ("rule_id", "valid", "invalid"),
    [
        (
            "arithmetic/fraction-as-many",
            "Fia sells three eighths as many animals as the teacher.",
            "Fia sells three eighths as many animals as teacher.",
        ),
        (
            "arithmetic/fraction-as-many-elided",
            "Fia sells two thirds as many as Eron.",
            "Fia sells two thirds as many as the inch.",
        ),
        (
            "arithmetic/affine-fraction-as-many",
            (
                "The teacher found 2 less than nine tenths as many animals "
                "as the student."
            ),
            (
                "The teacher found 2 less than nine tenths as many animals "
                "as student."
            ),
        ),
    ],
)
def test_fraction_many_standards_are_referential_quantity_holders(
    rule_id: str, valid: str, invalid: str, registry
) -> None:
    assert rule_id in _matched_rules(valid, registry)
    assert rule_id not in _matched_rules(invalid, registry)


def test_fraction_much_optional_context_uses_declared_compatibility(
    registry,
) -> None:
    rule_id = "arithmetic/fraction-as-much"

    assert rule_id in _matched_rules(
        (
            "Dena had three fifths as much money in the garden "
            "as her teacher Fia."
        ),
        registry,
    )
    assert rule_id not in _matched_rules(
        (
            "Dena had three fifths as much money to the plum "
            "as her teacher Fia."
        ),
        registry,
    )


@pytest.mark.parametrize(
    "text",
    [
        "There are 40 fish of rabbit.",
        "There are 14 hamsters and 40 pounds.",
    ],
)
def test_rejected_existential_continuations_do_not_fall_back_to_bare_prefix(
    text: str, registry
) -> None:
    assert not {
        rule_id
        for rule_id in _matched_rules(text, registry)
        if rule_id.startswith("arithmetic/existential-premise")
    }


def test_bare_and_conjoined_existentials_keep_complete_count_populations(
    registry,
) -> None:
    assert "arithmetic/existential-premise-bare" in _matched_rules(
        "There are 40 fish.", registry
    )
    assert "arithmetic/existential-premise-bare-conjoined" in _matched_rules(
        "There are 14 hamsters and 40 fish.", registry
    )


@pytest.mark.parametrize(
    "text",
    [
        "7 inches all total.",
        "7 inches all combined.",
        "7 inches all altogether.",
        "7 inches all in total.",
    ],
)
def test_trailing_group_total_rejects_incompatible_marker_pairs(
    text: str, registry
) -> None:
    assert "arithmetic/group-total-trailing" not in _matched_rules(
        text, registry
    )


@pytest.mark.parametrize(
    "text",
    [
        "7 inches total.",
        "7 inches combined.",
        "7 inches altogether.",
        "7 inches together.",
        "7 inches all together.",
        "7 inches in total.",
    ],
)
def test_trailing_group_total_keeps_declared_marker_pairs(
    text: str, registry
) -> None:
    assert "arithmetic/group-total-trailing" in _matched_rules(text, registry)


def test_trailing_group_total_generation_respects_marker_compatibility() -> None:
    project = load_project(Path("projects/curated"))
    rule_id = "arithmetic/group-total-trailing"

    for seed in range(32):
        candidate = generate_candidate(project, rule_id=rule_id, seed=seed)
        bindings = candidate.requested_bindings

        assert candidate.target_status == "matched"
        if "q" in bindings:
            assert bindings["agg"] == "together"
        if "p" in bindings:
            assert bindings["agg"] == "total"

    quantified = generate_candidate(
        project,
        rule_id=rule_id,
        seed=0,
        locked_bindings={"q": "all", "agg": "together"},
    )
    quantified_requirement = next(
        row
        for row in quantified.premises
        if row.kind == "where"
        and row.expression.startswith("bound_requires_category(")
        and "bound='q'" in row.expression
    )

    assert quantified.target_status == "matched"
    assert quantified.sentence.endswith("all together.")
    assert quantified_requirement.status == "passed"
    assert "quantified_group_total_marker" in quantified_requirement.expression

    with pytest.raises(GenerationError):
        generate_candidate(
            project,
            rule_id=rule_id,
            seed=0,
            locked_bindings={"q": "all", "agg": "total"},
        )


def test_latest_group_total_review_retests_absent() -> None:
    candidate = retest_candidate(
        load_project(Path("projects/curated")),
        rule_id="arithmetic/group-total-trailing",
        sentence="7 inches all total.",
        seed=8193571096638527,
        origin="generated",
    )

    assert candidate.target_status == "absent"


def test_latest_postfix_age_review_retests_absent() -> None:
    candidate = retest_candidate(
        load_project(Path("projects/curated")),
        rule_id="arithmetic/anchored-relation-postfix",
        sentence="Fia sells 19 areas older than can.",
        seed=2682948670209000,
        origin="generated",
    )

    assert candidate.target_status == "absent"


@pytest.mark.parametrize(
    "text",
    [
        "Fia sells 19 areas older than can.",
        "Fia sells 19 years older than Cato.",
        "Fia is 19 areas older than Cato.",
        "Fia is 19 years older than can.",
    ],
)
def test_postfix_age_relation_rejects_incompatible_compositions(
    text: str, registry
) -> None:
    assert not {
        "arithmetic/anchored-relation-postfix",
        "arithmetic/anchored-relation-postfix-age",
    } & _matched_rules(text, registry)


def test_postfix_count_and_age_siblings_keep_their_valid_classes(
    registry,
) -> None:
    assert "arithmetic/anchored-relation-postfix" in _matched_rules(
        "Fia sells 19 cans fewer than Cato.", registry
    )
    assert "arithmetic/anchored-relation-postfix" in _matched_rules(
        "Fia sells 19 cans more than apples.", registry
    )
    assert "arithmetic/anchored-relation-postfix-age" in _matched_rules(
        "Fia is 19 years older than Cato.", registry
    )
    assert "arithmetic/anchored-relation-postfix-age" in _matched_rules(
        "Fia was 19 years younger than her friend Cato.", registry
    )


def test_postfix_count_and_age_generation_stays_disjoint() -> None:
    project = load_project(Path("projects/curated"))

    for seed in range(16):
        count = generate_candidate(
            project,
            rule_id="arithmetic/anchored-relation-postfix",
            seed=seed,
        )
        age = generate_candidate(
            project,
            rule_id="arithmetic/anchored-relation-postfix-age",
            seed=seed,
        )

        assert count.target_status == "matched"
        assert count.requested_bindings["dir"] in {"fewer", "less", "more"}
        assert age.target_status == "matched"
        assert age.requested_bindings["dir"] in {"older", "younger"}
        assert project.registry.word_in_category(
            age.requested_bindings["verb"].casefold(), "copula"
        )
        age_item = next(row for row in age.premises if row.slot == "item")
        assert age_item.slot_type == "age_measure"
        assert age_item.category_path[-2:] == ("age_measure", "noun")


def test_postfix_age_keeps_declared_name_homographs_referential() -> None:
    registry = load_project(Path("projects/gsm8k")).registry

    assert "arithmetic/anchored-relation-postfix-age" in _matched_rules(
        "Mark is 8 years older than Bira, who is 12.", registry
    )


def test_postfix_quantity_relation_keeps_distance_events() -> None:
    registry = load_project(Path("projects/asdiv")).registry

    assert "arithmetic/anchored-relation-postfix" in _matched_rules(
        "Aven ran 8 miles more than Bira.", registry
    )


def test_distributive_existential_rejects_the_latest_totality_review(
    registry,
) -> None:
    rule_id = "arithmetic/existential-premise-distributive"

    assert rule_id not in _matched_rules(
        "There are 11 areas in all amount.", registry
    )
    assert rule_id in _matched_rules(
        "There are 11 areas in each garden.", registry
    )
    assert rule_id in _matched_rules(
        "There are 11 areas in every garden.", registry
    )


def test_in_all_is_an_explicit_group_total_surface(registry) -> None:
    rule_id = "arithmetic/group-total-trailing-in-all"
    result = solve("There are 11 areas in all.", registry)
    total = next(
        fact
        for fact in result.store.by_kind(GroupTotal)
        if fact.provenance.source == rule_id
    )

    assert rule_id in _matched_rules("There are 11 areas in all.", registry)
    assert total.measure == "area"
    assert total.value == 11
    assert total.scope is None
    assert not result.store.by_kind(Quantity)


def test_in_all_group_total_is_realisable_and_matcher_confirmed() -> None:
    candidate = generate_candidate(
        load_project(Path("projects/curated")),
        rule_id="arithmetic/group-total-trailing-in-all",
        seed=0,
        locked_bindings={"item": "11 areas"},
    )

    assert candidate.sentence == "11 areas in all."
    assert candidate.target_status == "matched"
    fact = next(fact for fact in candidate.facts if fact["type"] == "GroupTotal")
    assert fact["fields"] == {
        "measure": "area",
        "value": 11.0,
        "verb": "have",
    }
    assert fact["source"] == "arithmetic/group-total-trailing-in-all"


def test_latest_distributive_review_retests_absent() -> None:
    candidate = retest_candidate(
        load_project(Path("projects/curated")),
        rule_id="arithmetic/existential-premise-distributive",
        sentence="There are 11 areas in all amount.",
        seed=781980287943751,
        origin="generated",
    )

    assert candidate.target_status == "absent"


MASS_RATIO_CONTEXT_RULES = {
    "arithmetic/times-as-much",
    "arithmetic/times-as-much-elided-standard",
    "arithmetic/fraction-delta-relation-mass",
    "arithmetic/fraction-as-much",
    "arithmetic/fraction-as-much-elided-standard",
    "arithmetic/affine-times-as-much",
}


@pytest.mark.parametrize(
    ("rule_id", "text"),
    [
        (
            "arithmetic/times-as-much",
            "Mary gave twice as much rest with the remainder as Eron.",
        ),
        (
            "arithmetic/times-as-much-elided-standard",
            "Mary gave twice as much rest with the remainder.",
        ),
        (
            "arithmetic/fraction-delta-relation-mass",
            "Mary gave one tenth more rest with the remainder than Eron.",
        ),
        (
            "arithmetic/fraction-as-much",
            "Mary gave half as much rest with the remainder as Eron.",
        ),
        (
            "arithmetic/fraction-as-much-elided-standard",
            "Mary gave half as much rest with the remainder.",
        ),
        (
            "arithmetic/affine-times-as-much",
            (
                "Mary gave 3 more than twice as much rest with the "
                "remainder as Eron."
            ),
        ),
    ],
)
def test_mass_ratio_family_rejects_transfer_remnants_and_remnant_pps(
    rule_id: str, text: str, registry
) -> None:
    assert rule_id not in _matched_rules(text, registry)


@pytest.mark.parametrize(
    ("text", "matched"),
    [
        ("Mary gave twice as much rest.", False),
        ("Mary has twice as much rest with the remainder.", False),
        ("Mary gave twice as much money with the remainder.", False),
        ("Mary has twice as much rest in the garden.", True),
        ("Mary gave twice as much money in the garden.", True),
    ],
)
def test_elided_mass_standard_separates_verb_object_and_pp_boundaries(
    text: str, matched: bool, registry
) -> None:
    assert (
        "arithmetic/times-as-much-elided-standard"
        in _matched_rules(text, registry)
    ) is matched


def test_mass_ratio_generation_respects_transfer_and_remnant_boundaries() -> None:
    project = load_project(Path("projects/curated"))

    for rule_id in MASS_RATIO_CONTEXT_RULES:
        for seed in range(16):
            candidate = generate_candidate(
                project,
                rule_id=rule_id,
                seed=seed,
            )
            bindings = candidate.requested_bindings

            assert candidate.target_status == "matched"
            if project.registry.word_in_category(
                bindings["verb"].casefold(), "transfer_out"
            ):
                assert not project.registry.word_in_category(
                    bindings["item"].casefold(), "remnant"
                )
            if "pp_prep" in bindings:
                assert not project.registry.word_in_category(
                    bindings["pp_prep"].casefold(),
                    "quantity_remainder_preposition",
                )


def test_latest_mass_ratio_review_retests_absent() -> None:
    candidate = retest_candidate(
        load_project(Path("projects/curated")),
        rule_id="arithmetic/times-as-much-elided-standard",
        sentence="Mary gave twice as much rest with the remainder.",
        seed=781980287943752,
        origin="generated",
    )

    assert candidate.target_status == "absent"


def test_motion_comparisons_require_an_explicit_measure(registry) -> None:
    reviewed = "The rabbit traveled nine ninths as many as the pencil."

    assert "arithmetic/fraction-as-many-elided" not in _matched_rules(
        reviewed, registry
    )
    assert "arithmetic/times-as-many-elided" not in _matched_rules(
        "The rabbit traveled twice as many as the dog.", registry
    )


def test_motion_frequency_uses_the_overt_times_measure(registry) -> None:
    rule_id = "arithmetic/fraction-as-many"
    valid = "The rabbit traveled nine ninths as many times as the dog."
    invalid = "The rabbit traveled nine ninths as many times as the pencil."
    result = solve(valid, registry)
    relation = next(
        fact
        for fact in result.store.by_kind(Relation)
        if fact.provenance.source == rule_id
    )

    assert rule_id in _matched_rules(valid, registry)
    assert rule_id not in _matched_rules(invalid, registry)
    assert relation.subject == "rabbit"
    assert relation.standard == "dog"
    assert relation.measure == "time"
    assert relation.factor == 1.0


def test_as_far_is_a_separate_motion_distance_relation(registry) -> None:
    rule_id = "arithmetic/fraction-as-far"
    valid = "The rabbit traveled nine ninths as far as the dog."
    invalid = "The rabbit traveled nine ninths as far as the pencil."
    result = solve(valid, registry)
    relation = next(
        fact
        for fact in result.store.by_kind(Relation)
        if fact.provenance.source == rule_id
    )

    assert rule_id in _matched_rules(valid, registry)
    assert rule_id not in _matched_rules(invalid, registry)
    assert relation.subject == "rabbit"
    assert relation.standard == "dog"
    assert relation.measure == "distance"
    assert relation.factor == 1.0


def test_mined_vehicle_classes_are_motion_participants() -> None:
    registry = load_project(Path("projects/gsm8k")).registry

    assert "arithmetic/fraction-as-far" in _matched_rules(
        "The car traveled half as far as the truck.", registry
    )
    assert "arithmetic/fraction-as-many" in _matched_rules(
        "The car traveled half as many times as the truck.", registry
    )


@pytest.mark.parametrize(
    ("rule_id", "locked_bindings", "expected_measure"),
    [
        (
            "arithmetic/fraction-as-many",
            {
                "who": "the rabbit",
                "verb": "traveled",
                "f": "nine ninths",
                "item": "times",
                "std": "the dog",
            },
            "time",
        ),
        (
            "arithmetic/fraction-as-far",
            {
                "who": "the rabbit",
                "verb": "traveled",
                "f": "nine ninths",
                "std": "the dog",
            },
            "distance",
        ),
    ],
)
def test_explicit_motion_comparisons_are_reviewable(
    rule_id: str,
    locked_bindings: dict[str, str],
    expected_measure: str,
) -> None:
    candidate = generate_candidate(
        load_project(Path("projects/curated")),
        rule_id=rule_id,
        seed=0,
        locked_bindings=locked_bindings,
    )

    assert candidate.target_status == "matched"
    relation = next(
        fact for fact in candidate.facts if fact["type"] == "Relation"
    )
    assert relation["fields"]["measure"] == expected_measure


def test_latest_motion_review_retests_absent() -> None:
    candidate = retest_candidate(
        load_project(Path("projects/curated")),
        rule_id="arithmetic/fraction-as-many-elided",
        sentence="The rabbit traveled nine ninths as many as the pencil.",
        seed=912618241230548,
        origin="generated",
    )

    assert candidate.target_status == "absent"


@pytest.mark.parametrize("holder", ["money", "time"])
def test_abstract_measures_cannot_be_quantity_holders(
    holder: str, registry
) -> None:
    assert registry.word_in_category(holder, "non_quantity_holder")


def test_latest_percent_change_holder_reviews_retest_absent() -> None:
    project = load_project(Path("projects/curated"))
    for sentence in (
        "Time needs eight eighths more dollars.",
        "Time loses seventeen sevenths more dollars.",
    ):
        candidate = retest_candidate(
            project,
            rule_id="arithmetic/percent-change-event-count",
            sentence=sentence,
            seed=0,
            origin="generated",
        )
        assert candidate.target_status == "absent"


def test_rest_partition_requires_a_definite_plural_rest_subject(
    registry,
) -> None:
    rule_id = "arithmetic/partition-rest-membership"

    assert rule_id in _matched_rules("The rest were dogs.", registry)
    assert rule_id not in _matched_rules("Rest were dogs.", registry)
    assert rule_id not in _matched_rules("The remainder were dogs.", registry)
    assert rule_id not in _matched_rules("Remainder were times.", registry)


def test_temporal_measure_is_not_a_rest_membership_label(registry) -> None:
    rule_id = "arithmetic/partition-rest-membership"

    assert rule_id not in _matched_rules("The rest were times.", registry)
    assert rule_id in _matched_rules("The rest were rabbits.", registry)
    assert registry.word_in_category(
        "time", "membership_predicate_incompatible_noun"
    )


AS_MANY_MUCH_MULTIPLIER_RULES = {
    "arithmetic/times-as-many",
    "arithmetic/times-as-many-elided",
    "arithmetic/times-as-many-elided-standard",
    "arithmetic/times-as-many-possessive-kinship-standard",
    "arithmetic/times-as-many-conjunct",
    "arithmetic/times-as-many-conjunct-elided-standard",
    "arithmetic/times-as-many-conjunct-elided-item",
    "arithmetic/times-as-much",
    "arithmetic/times-as-much-elided",
    "arithmetic/times-as-much-elided-standard",
    "arithmetic/anaphoric-multiplier-standard-as-much",
    "arithmetic/anaphoric-multiplier-standard-as-many",
    "arithmetic/affine-times-as-much",
    "arithmetic/affine-times-as-much-elided",
}


def test_as_many_much_rules_exclude_predeterminer_multipliers() -> None:
    registry = load_project(Path("projects/curated")).registry
    rules = {rule.id: rule for rule in registry.rules}

    assert registry.word_in_category("double", "predeterminer_multiplier")
    assert registry.word_in_category("triple", "predeterminer_multiplier")
    for rule_id in AS_MANY_MUCH_MULTIPLIER_RULES:
        assert any(
            predicate.slot_not_category
            == {"slot": "k", "cat": "predeterminer_multiplier"}
            for predicate in rules[rule_id].where
        )


DEMONSTRATIVE_QUANTITY_PROFORM_RULES = {
    "arithmetic/anaphoric-multiplier-conjunct-many",
    "arithmetic/anaphoric-multiplier-standard-many",
    "arithmetic/anaphoric-multiplier-standard-much",
}


def test_demonstrative_quantity_proforms_exclude_predeterminers() -> None:
    registry = load_project(Path("projects/curated")).registry
    rules = {rule.id: rule for rule in registry.rules}

    for rule_id in DEMONSTRATIVE_QUANTITY_PROFORM_RULES:
        assert any(
            predicate.slot_not_category
            == {"slot": "k", "cat": "predeterminer_multiplier"}
            for predicate in rules[rule_id].where
        )


@pytest.mark.parametrize(
    ("rule_id", "invalid", "valid"),
    [
        (
            "arithmetic/anaphoric-multiplier-standard-many",
            "Bira wanted triple this many.",
            "Bira wanted thrice this many.",
        ),
        (
            "arithmetic/anaphoric-multiplier-standard-much",
            "Bira wanted double that much.",
            "Bira wanted twice that much.",
        ),
        (
            "arithmetic/anaphoric-multiplier-conjunct-many",
            "The dog ate 18 apples and double that many.",
            "The dog ate 18 apples and twice that many.",
        ),
    ],
)
def test_demonstrative_quantity_proform_multiplier_minimal_pairs(
    rule_id: str, invalid: str, valid: str, registry
) -> None:
    assert rule_id not in _matched_rules(invalid, registry)
    assert rule_id in _matched_rules(valid, registry)


def test_reviewed_predeterminer_proform_cannot_be_regenerated() -> None:
    with pytest.raises(GenerationError, match="no filler for k"):
        generate_candidate(
            load_project(Path("projects/curated")),
            rule_id="arithmetic/anaphoric-multiplier-standard-many",
            seed=907190546063107,
            locked_bindings={
                "who": "storeroom",
                "verb": "wanted",
                "k": "triple",
            },
        )


ANAPHORIC_QUANTITY_RULES = {
    "arithmetic/anaphoric-multiplier-standard",
    "arithmetic/anaphoric-multiplier-standard-as-many",
    "arithmetic/anaphoric-multiplier-standard-as-much",
    "arithmetic/anaphoric-multiplier-standard-many",
    "arithmetic/anaphoric-multiplier-standard-much",
}


def test_anaphoric_quantity_relations_exclude_declared_nonholders() -> None:
    registry = load_project(Path("projects/curated")).registry
    rules = {rule.id: rule for rule in registry.rules}

    for rule_id in ANAPHORIC_QUANTITY_RULES:
        assert any(
            predicate.slot_not_category
            == {"slot": "who", "cat": "non_quantity_holder"}
            for predicate in rules[rule_id].where
        )


@pytest.mark.parametrize(
    ("rule_id", "invalid", "valid"),
    [
        (
            "arithmetic/anaphoric-multiplier-standard-as-much",
            "Time dropped thrice as much.",
            "Bira dropped thrice as much.",
        ),
        (
            "arithmetic/anaphoric-multiplier-standard-as-many",
            "Time dropped thrice as many.",
            "Bira dropped thrice as many.",
        ),
        (
            "arithmetic/anaphoric-multiplier-standard-much",
            "Time dropped thrice that much.",
            "Bira dropped thrice that much.",
        ),
        (
            "arithmetic/anaphoric-multiplier-standard-many",
            "Time dropped thrice that many.",
            "Bira dropped thrice that many.",
        ),
        (
            "arithmetic/anaphoric-multiplier-standard",
            "Time dropped triple the amount.",
            "Bira dropped triple the amount.",
        ),
    ],
)
def test_anaphoric_quantity_holder_minimal_pairs(
    rule_id: str, invalid: str, valid: str, registry
) -> None:
    assert rule_id not in _matched_rules(invalid, registry)
    assert rule_id in _matched_rules(valid, registry)


def test_positive_holder_role_rejects_the_reviewed_unit_subjects() -> None:
    project = load_project(Path("projects/gsm8k"))

    reviewed = {
        "arithmetic/times-as-many-conjunct-elided-standard": (
            "The millions measure 4 libraries in the wardrobe and twice "
            "as many afternoons."
        ),
        "arithmetic/times-as-many": (
            "The joule afford twice as many parents as its sister Aven."
        ),
    }
    for rule_id, sentence in reviewed.items():
        candidate = retest_candidate(
            project,
            rule_id=rule_id,
            sentence=sentence,
            seed=0,
            origin="generated",
        )
        assert candidate.target_status == "absent"


@pytest.mark.parametrize(
    ("sentence", "matches"),
    [
        (
            "The teacher has 4 libraries in the wardrobe and twice as "
            "many afternoons.",
            False,
        ),
        (
            "The teacher has 4 libraries in the wardrobe and twice as "
            "many books.",
            True,
        ),
        (
            "The teacher has 4 mornings in the wardrobe and twice as "
            "many afternoons.",
            True,
        ),
    ],
)
def test_conjunct_measures_agree_on_temporal_membership(
    sentence: str, matches: bool
) -> None:
    registry = load_project(Path("projects/gsm8k")).registry
    rule_id = "arithmetic/times-as-many-conjunct-elided-standard"
    assert (rule_id in _matched_rules(sentence, registry)) is matches


def test_reviewed_verbs_do_not_claim_direct_quantity_objects() -> None:
    registry = load_project(Path("projects/gsm8k")).registry
    for surface in ("afford", "affords", "measure", "measured", "measures"):
        assert registry.word_in_category(
            surface, "non_quantity_object_verb"
        )

    assert "arithmetic/times-as-many" in _matched_rules(
        "The teacher has twice as many parents as her sister Aven.",
        registry,
    )


def test_reviewed_morphology_shares_one_lemma_and_number() -> None:
    registry = load_project(Path("projects/gsm8k")).registry

    assert registry.singular_to_plural["million"] == "millions"
    assert registry.plural_to_singular["millions"] == "million"
    assert registry.lexicon["measure"].number == "plural"
    assert registry.lexicon["measures"].number == "singular"
    assert registry.verb_lemmas["measures"] == "measure"
    assert registry.lexicon["afford"].number == "plural"
    assert registry.lexicon["affords"].number == "singular"
    assert registry.verb_lemmas["affords"] == "afford"


def test_strict_generation_filters_unlicensed_common_noun_holders() -> None:
    project = load_project(Path("projects/gsm8k"))

    with pytest.raises(GenerationError, match="no filler for who"):
        generate_candidate(
            project,
            rule_id="arithmetic/times-as-many",
            seed=0,
            locked_bindings={
                "who": "the joule",
                "verb": "has",
                "k": "twice",
                "item": "parents",
                "std": "Aven",
            },
        )

    candidate = generate_candidate(
        project,
        rule_id="arithmetic/times-as-many",
        seed=0,
        locked_bindings={
            "who": "the teacher",
            "verb": "has",
            "k": "twice",
            "item": "parents",
            "std": "Aven",
        },
    )
    assert candidate.target_status == "matched"
    who = next(premise for premise in candidate.premises if premise.slot == "who")
    assert "quantity_holder" in who.expression
    assert "common noun" in who.reason


def test_holder_gate_remains_available_to_lexical_boundary_probes() -> None:
    project = load_project(Path("projects/gsm8k"))
    rule = next(
        rule
        for rule in project.registry.rules
        if rule.id == "arithmetic/times-as-many"
    )
    token = next(
        token for token in rule.match["sentence"] if token.slot == "who"
    )
    broader = _broader_lexical_domain(
        token, project.registry, _load_fixtures(project.root)
    )

    assert broader is not None
    fillers, requirement, parent = broader
    assert requirement == "common-noun category 'quantity_holder'"
    assert parent == "root sense 'noun'"
    assert any(filler.identity == "joule" for filler in fillers)


def test_declared_name_homographs_remain_quantity_holders() -> None:
    registry = load_project(Path("projects/gsm8k")).registry

    assert registry.word_in_category("bill", "bare_entity_reference")
    assert registry.word_in_category("bill", "quantity_holder")
    assert "arithmetic/times-as-many" in _matched_rules(
        "Bill has twice as many nuts as Harry.", registry
    )


def test_animate_appositive_requires_a_compatible_possessor() -> None:
    project = load_project(Path("projects/gsm8k"))
    registry = project.registry
    rule_id = "arithmetic/times-as-many"

    assert rule_id not in _matched_rules(
        "The store has twice as many parents as its sister Aven.",
        registry,
    )
    assert rule_id in _matched_rules(
        "The dog has twice as many parents as its sister Aven.",
        registry,
    )
    assert rule_id in _matched_rules(
        "Tom has twice as many parents as his sister Aven.",
        registry,
    )

    rule = next(rule for rule in registry.rules if rule.id == rule_id)
    requirement = next(
        predicate.bound_requires_category
        for predicate in rule.where
        if predicate.bound_requires_category is not None
        and predicate.bound_requires_category.bound == "appos_role"
        and predicate.bound_requires_category.slot == "who"
    )
    assert requirement.cat == "quantity_event_participant"
    assert requirement.allow_proper_name is True

    with pytest.raises(GenerationError, match="no filler for who"):
        generate_candidate(
            project,
            rule_id=rule_id,
            seed=0,
            locked_bindings={
                "who": "the store",
                "verb": "has",
                "k": "twice",
                "item": "parents",
                "appos_det": "its",
                "appos_role": "sister",
                "std": "Aven",
            },
        )


ADVERBIAL_AGE_MULTIPLIER_RULES = {
    "arithmetic/temporal-offset-times-as-old-as-future",
    "arithmetic/temporal-offset-times-as-old-as-future-std-now",
    "arithmetic/temporal-offset-times-as-old-as-past",
    "arithmetic/times-as-old-as",
    "arithmetic/times-comparative-age-relation",
}


def test_adverbial_age_ratios_exclude_predeterminer_multipliers() -> None:
    registry = load_project(Path("projects/curated")).registry
    rules = {rule.id: rule for rule in registry.rules}

    for rule_id in ADVERBIAL_AGE_MULTIPLIER_RULES:
        assert any(
            predicate.slot_not_category
            == {"slot": "k", "cat": "predeterminer_multiplier"}
            for predicate in rules[rule_id].where
        )


@pytest.mark.parametrize(
    ("rule_id", "invalid", "valid"),
    [
        (
            "arithmetic/times-comparative-age-relation",
            "Aven is double older than Cato.",
            "Aven is twice older than Cato.",
        ),
        (
            "arithmetic/times-as-old-as",
            "Aven is double as old as Cato.",
            "Aven is twice as old as Cato.",
        ),
        (
            "arithmetic/temporal-offset-times-as-old-as-future",
            "In 18 years Aven would be double as old as Cato.",
            "In 18 years Aven would be twice as old as Cato.",
        ),
        (
            "arithmetic/temporal-offset-times-as-old-as-future-std-now",
            "In 18 years Aven would be double as old as Cato today.",
            "In 18 years Aven would be twice as old as Cato today.",
        ),
        (
            "arithmetic/temporal-offset-times-as-old-as-past",
            "18 years ago Aven was double as old as Cato.",
            "18 years ago Aven was twice as old as Cato.",
        ),
    ],
)
def test_adverbial_age_multiplier_minimal_pairs(
    rule_id: str, invalid: str, valid: str, registry
) -> None:
    assert rule_id not in _matched_rules(invalid, registry)
    assert rule_id in _matched_rules(valid, registry)


def test_new_guard_reviews_cannot_be_regenerated() -> None:
    project = load_project(Path("projects/curated"))

    with pytest.raises(GenerationError, match="no filler for who"):
        generate_candidate(
            project,
            rule_id="arithmetic/anaphoric-multiplier-standard-as-much",
            seed=2269014546521227,
            locked_bindings={
                "who": "time",
                "verb": "dropped",
                "k": "thrice",
            },
        )
    with pytest.raises(GenerationError, match="no filler for k"):
        generate_candidate(
            project,
            rule_id="arithmetic/temporal-offset-times-as-old-as-future",
            seed=2269014546521228,
            locked_bindings={
                "n": "18 years",
                "who": "Aven",
                "aux": "would",
                "k": "double",
                "std": "Cato",
            },
        )


def test_affine_count_keeps_established_predeterminer_compatibility(
    registry,
) -> None:
    assert "arithmetic/affine-times-as-many" in _matched_rules(
        "Cato has 2 more than triple as many apples as Eron.", registry
    )


def test_affine_as_much_uses_mass_direction_and_adverbial_multiplier(
    registry,
) -> None:
    rule_id = "arithmetic/affine-times-as-much-elided"

    assert rule_id not in _matched_rules(
        "Fia loses 14 fewer than double as much as Cato.", registry
    )
    assert rule_id in _matched_rules(
        "Fia loses 14 less than thrice as much as Cato.", registry
    )
    assert rule_id in _matched_rules(
        "Fia loses 14 less than three times as much as Cato.", registry
    )


def test_conjunct_comparison_keeps_compatible_measures_and_forms(
    registry,
) -> None:
    rule_id = "arithmetic/times-as-many-conjunct-elided-standard"

    assert rule_id not in _matched_rules(
        "The money had 20 friends and triple as many times.", registry
    )
    assert rule_id not in _matched_rules(
        "Cato had 20 friends and thrice as many times.", registry
    )
    assert rule_id in _matched_rules(
        "Cato had 20 friends and thrice as many teachers.", registry
    )
    assert rule_id in _matched_rules(
        "Cato had 20 friends and three times as many teachers.", registry
    )


CONJUNCT_MOTION_ROLE_SLOTS = {
    "arithmetic/times-as-many-conjunct": {"who", "std"},
    "arithmetic/times-as-many-conjunct-elided-standard": {"who"},
    "arithmetic/times-as-many-conjunct-elided-item": {"who"},
    "arithmetic/anaphoric-multiplier-conjunct-many": {"who"},
}


def test_conjunct_comparisons_share_motion_participant_boundaries() -> None:
    registry = load_project(Path("projects/curated")).registry
    rules = {rule.id: rule for rule in registry.rules}

    for rule_id, expected_roles in CONJUNCT_MOTION_ROLE_SLOTS.items():
        actual_roles = {
            role
            for predicate in rules[rule_id].where
            if predicate.verb_roles_compatible is not None
            for role in predicate.verb_roles_compatible.roles.get("actor", [])
        }
        assert actual_roles == expected_roles


def test_full_conjunct_motion_participant_minimal_pair(registry) -> None:
    rule_id = "arithmetic/times-as-many-conjunct"

    assert rule_id not in _matched_rules(
        "The book traveled 12 inches and twice as many inches as Mary.",
        registry,
    )
    assert rule_id in _matched_rules(
        "The dog traveled 12 inches and twice as many inches as Mary.",
        registry,
    )


def test_full_conjunct_optional_context_uses_declared_compatibility() -> None:
    registry = load_project(Path("projects/curated")).registry
    rules = {rule.id: rule for rule in registry.rules}

    assert any(
        predicate.attribute_compatible is not None
        and predicate.attribute_compatible.attribute == "pp_prep"
        and predicate.attribute_compatible.noun == "pp_obj"
        for predicate in rules["arithmetic/times-as-many-conjunct"].where
    )


def test_full_conjunct_context_minimal_pair(registry) -> None:
    rule_id = "arithmetic/times-as-many-conjunct"

    assert rule_id not in _matched_rules(
        (
            "The dog traveled 12 inches of its dollar and twice as many "
            "inches as Mary."
        ),
        registry,
    )
    assert rule_id in _matched_rules(
        (
            "The dog traveled 12 inches in its garden and twice as many "
            "inches as Mary."
        ),
        registry,
    )


def test_latest_conjunct_review_retests_absent() -> None:
    candidate = retest_candidate(
        load_project(Path("projects/curated")),
        rule_id="arithmetic/times-as-many-conjunct",
        sentence=(
            "The book traveled 90 coins of its dollar and twice as many "
            "trees as their friend Mary."
        ),
        seed=7626256806574971,
        origin="generated",
    )

    assert candidate.target_status == "absent"


def test_valid_thrice_as_much_review_remains_matched(registry) -> None:
    assert "arithmetic/times-as-much-elided" in _matched_rules(
        "Cato buys thrice as much as my friend Aven.", registry
    )


def test_latest_fraction_frame_review_retests_absent_and_keeps_neighbours(
    registry,
) -> None:
    rule_id = "arithmetic/fraction-frame-relation"

    assert rule_id not in _matched_rules(
        (
            "John travels to eighteen fifths the amount of rabbits "
            "that plum traveled to."
        ),
        registry,
    )
    assert rule_id in _matched_rules(
        "John receives half the amount of books that Dena receives.", registry
    )
    assert rule_id in _matched_rules(
        "John travels to half the number of gardens Dena traveled to.",
        registry,
    )
    assert rule_id not in _matched_rules(
        "John travels to half the number of rabbits Dena traveled to.",
        registry,
    )


def test_sum_of_age_requires_the_plural_possessive_copular_frame(
    registry,
) -> None:
    rule_id = "arithmetic/group-total-sum-of-age"

    assert rule_id not in _matched_rules(
        "Sum of somebody age are 11.", registry
    )
    assert rule_id not in _matched_rules("The sum of their age is 11.", registry)
    assert rule_id not in _matched_rules("The sum of their ages are 11.", registry)
    assert rule_id in _matched_rules("The sum of their ages is 11.", registry)
    assert rule_id in _matched_rules("The sum of ages is 11.", registry)


def test_as_many_much_rules_require_a_nonunit_multiplier(registry) -> None:
    rules = {rule.id: rule for rule in registry.rules}

    for rule_id in AS_MANY_MUCH_MULTIPLIER_RULES:
        multiplier = next(
            token
            for token in rules[rule_id].match["sentence"]
            if isinstance(token, MatchToken) and token.slot == "k"
        )
        assert multiplier.type == "nonunit_multiplier"

    assert "arithmetic/times-as-many-elided-standard" not in _matched_rules(
        "The bird buys once as many roses with the remainder.", registry
    )
    assert "arithmetic/times-as-many-elided-standard" in _matched_rules(
        "The bird buys twice as many roses with the remainder.", registry
    )


@pytest.mark.parametrize(
    "rule_id",
    [
        "arithmetic/existential-premise",
        "arithmetic/existential-premise-distributive",
        "arithmetic/existential-premise-bare",
        "arithmetic/existential-premise-bare-conjoined",
        "arithmetic/existential-premise-total",
    ],
)
def test_existential_quantity_rules_refuse_temporal_times(
    rule_id: str, registry
) -> None:
    rules = {rule.id: rule for rule in registry.rules}
    guarded_slots = {
        predicate.slot_not_category["slot"]
        for predicate in rules[rule_id].where
        if predicate.slot_not_category
        and predicate.slot_not_category["cat"]
        == "existential_incompatible_noun"
    }
    expected = {"item", "item2"} if rule_id.endswith("conjoined") else {"item"}
    assert guarded_slots == expected


def test_temporal_times_cannot_be_generated_as_a_bare_population(
    registry,
) -> None:
    assert "arithmetic/existential-premise-bare" not in _matched_rules(
        "There were 30 times.", registry
    )
    assert "arithmetic/existential-premise-bare" in _matched_rules(
        "There were 30 toys.", registry
    )


def test_periodic_rate_requires_a_referential_subject(registry) -> None:
    rule_id = "arithmetic/periodic-rate-every-span"

    assert rule_id not in _matched_rules(
        "Teacher might need 17 hamsters every 18 years.", registry
    )
    assert rule_id in _matched_rules(
        "The teacher might need 17 hamsters every 18 years.", registry
    )
    assert rule_id in _matched_rules(
        "Dena might need 17 hamsters every 18 years.", registry
    )


LATEST_PREMISE_REVIEW_REJECTIONS = {
    "arithmetic/fraction-frame-relation": (
        "The clamp threw to thirty halves the number of wheels the cookie "
        "threw to."
    ),
    "arithmetic/anchored-relation-possessive-kinship-standard": (
        "Ball came 7 less nails than his exhibit."
    ),
    "arithmetic/times-as-many-conjunct-elided-item": (
        "The laptop met 13 trains with the rest and thrice as many in the "
        "aquarium."
    ),
    "arithmetic/anchored-relation-elided": (
        "Lists collects 0 older than rabbit."
    ),
    "arithmetic/affine-frame-relation-clause": (
        "Noon equals 7 fewer than once the number of aquariums her customer "
        "Fia equals."
    ),
    "arithmetic/anaphoric-multiplier-conjunct-many": (
        "The gems traded 19 cups and twice this many."
    ),
    "arithmetic/anchored-relation-postfix-dimension": (
        "Gap is 18 days shorter than gift."
    ),
    "arithmetic/times-the-number-of": (
        "Footage buy once the number of robins as my baker Mary."
    ),
    "arithmetic/anchored-relation-postfix": (
        "The macaron shuck 14 teams more than the hand-written."
    ),
}


@pytest.mark.parametrize(
    ("rule_id", "sentence"), LATEST_PREMISE_REVIEW_REJECTIONS.items()
)
def test_latest_premise_review_rejections_are_absent(
    rule_id: str, sentence: str
) -> None:
    candidate = retest_candidate(
        load_project(Path("projects/gsm8k")),
        rule_id=rule_id,
        sentence=sentence,
        seed=0,
        origin="generated",
    )

    assert candidate.target_status == "absent"


def test_latest_valid_temporal_review_remains_matched() -> None:
    candidate = retest_candidate(
        load_project(Path("projects/gsm8k")),
        rule_id=(
            "arithmetic/temporal-offset-times-as-old-as-future-std-now"
        ),
        sentence=(
            "In 40 years Dena will be twice as old as my seller John is now."
        ),
        seed=0,
        origin="generated",
    )

    assert candidate.target_status == "matched"
    relation = next(fact for fact in candidate.facts if fact["type"] == "Relation")
    assert relation["fields"]["factor"] == 2
    assert relation["fields"]["subject_offset"] == 40
    assert relation["fields"]["standard_offset"] == 0


def test_reviewed_event_boundaries_keep_ordinary_neighbours() -> None:
    registry = load_project(Path("projects/gsm8k")).registry
    assert "arithmetic/affine-frame-relation" in _matched_rules(
        (
            "The painter repainted 19 fewer than twice the number of strips "
            "that her mother Bira repainted."
        ),
        registry,
    )
    assert "arithmetic/anaphoric-multiplier-conjunct-many" in _matched_rules(
        "The teacher traded 19 cups and twice this many.", registry
    )
    assert "arithmetic/times-the-number-of" in _matched_rules(
        "The buyer buys twice the number of robins as her baker Mary.",
        registry,
    )
    assert "arithmetic/anchored-relation-postfix" in _matched_rules(
        "The farmer shucked 14 ears more than the worker.", registry
    )


def test_latest_review_boundaries_keep_ordinary_neighbours() -> None:
    registry = load_project(Path("projects/gsm8k")).registry

    assert "arithmetic/anchored-relation-possessive-kinship-standard" in (
        _matched_rules(
            "The sister has 7 fewer nails than her brother.", registry
        )
    )
    assert "arithmetic/anchored-relation-elided" in _matched_rules(
        "The teacher has 7 fewer than the student.", registry
    )
    assert "arithmetic/times-as-many-conjunct-elided-item" in _matched_rules(
        (
            "The teacher met 13 students at the school and thrice as many "
            "at the party."
        ),
        registry,
    )
    assert "arithmetic/fraction-frame-relation" in _matched_rules(
        (
            "Dena receives half the number of books that Fia receives."
        ),
        registry,
    )
    assert "arithmetic/affine-frame-relation-clause" in _matched_rules(
        (
            "Dena has 7 fewer than twice the number of aquariums Fia has."
        ),
        registry,
    )


def test_reviewed_relative_clause_echo_must_agree() -> None:
    registry = load_project(Path("projects/gsm8k")).registry
    rule_id = "arithmetic/times-frame-relation-clause"

    assert rule_id not in _matched_rules(
        "The planks cover double the number of bonsais her captain Mary cover.",
        registry,
    )
    assert rule_id in _matched_rules(
        "The planks cover double the number of bonsais her captain Mary covers.",
        registry,
    )


def test_dimension_relation_requires_measure_compatible_holders() -> None:
    registry = load_project(Path("projects/gsm8k")).registry
    rule_id = "arithmetic/anchored-relation-postfix-dimension"

    assert rule_id not in _matched_rules(
        "The gap is 18 days shorter than the gift.", registry
    )
    assert rule_id in _matched_rules(
        "The gap is 18 days shorter than the trip.", registry
    )
    assert rule_id in _matched_rules(
        "The gift is 2 inches shorter than the box.", registry
    )
    assert rule_id in _matched_rules(
        "The gift is 2 pounds lighter than the box.", registry
    )


def test_dangling_dimension_comparative_is_consumed_without_a_fact(
) -> None:
    registry = load_project(Path("projects/gsm8k")).registry
    result = solve("The gap is 18 days shorter.", registry)

    assert "arithmetic/dangling-comparative-relation" in {
        match.match.rule.id for match in result.document.rule_results[0]
    }
    assert not result.store.by_kind(Relation)
    assert not result.store.by_kind(Quantity)


def test_reviewed_morphology_normalizes_inflected_event_verbs() -> None:
    registry = load_project(Path("projects/gsm8k")).registry
    assert registry.singular_to_plural["gem"] == "gems"
    assert registry.verb_lemmas["repainting"] == "repaint"
    assert registry.verb_lemmas["traded"] == "trade"
    assert registry.verb_lemmas["shucked"] == "shuck"
    assert registry.lexicon["trade"].number == "plural"
    assert registry.lexicon["trades"].number == "singular"
    assert registry.lexicon["shuck"].number == "plural"
    assert registry.lexicon["shucks"].number == "singular"
