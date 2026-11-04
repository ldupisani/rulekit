"""Attributed subgroups whose stated parts determine a collection total.

All prose is synthetic. The class combines an uncounted collection context,
a cardinal subgroup, a proportional sibling, and a final subgroup sized from
the explicitly coordinated sibling total.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation.sample import GenerationError, generate_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import (
    CollectionContext,
    PartitionAggregateShare,
    PartitionQuantity,
    Predication,
    Quantity,
)
from rulekit.kernel.patterns import match_ask


@pytest.fixture(scope="module")
def project():
    return load_project(Path("projects/curated"))


@pytest.fixture(scope="module")
def registry(project):
    return project.registry


def _story(*, direction: str = "more") -> str:
    return (
        "Mira has a pantry with different color marbles. "
        f"Sixteen of them are red, and there are 25% {direction} of them in blue. "
        "There are only 25% as many green marbles as there are red and blue marbles. "
        "How many marbles are in Mira's pantry?"
    )


def test_attributed_partitions_compose_into_the_located_collection(registry) -> None:
    result = solve(_story(), registry)

    assert (result.answer.kind, result.answer.value) == ("number", 45.0)
    assert not result.deficiencies()
    assert any(
        context.holder == "pantry"
        and context.holder_owner == "mira"
        and context.collection == "marble"
        for context in result.store.by_kind(CollectionContext)
    )
    resolved = {
        partition.attribute: partition.value
        for partition in result.store.by_kind(PartitionQuantity)
        if partition.collection == "marble"
    }
    assert resolved == {"red": 16.0, "blue": 20.0, "green": 9.0}
    qualified = {
        quantity.measure_qualifier: quantity.value
        for quantity in result.store.by_kind(Quantity)
        if quantity.entity == "pantry" and quantity.owner == "mira"
    }
    assert qualified == {"red": 16.0, "blue": 20.0, "green": 9.0}


def test_proportional_decrease_uses_the_same_partition_contract(registry) -> None:
    result = solve(_story(direction="fewer"), registry)

    assert (result.answer.kind, result.answer.value) == ("number", 35.0)


def test_promoted_color_vocabulary_is_available_in_core_english(registry) -> None:
    result = solve(
        "Tova has a cupboard with different color stickers. "
        "Twelve of them are yellow, and there are 50% more of them in purple. "
        "There are 50% as many violet stickers as there are yellow and purple stickers. "
        "How many stickers are in Tova's cupboard?",
        registry,
    )

    assert (result.answer.kind, result.answer.value) == ("number", 45.0)


def test_mixed_collection_anaphors_and_owned_location_ask_compose(registry) -> None:
    result = solve(
        "Tova has a garden with flowers. "
        "She planted plants of three different colors in it. "
        "Twelve of them are yellow, and there are 50% more of those in purple. "
        "There are 50% as many green flowers as there are yellow and purple flowers. "
        "How many flowers does Tova have in her garden?",
        registry,
    )
    matched = match_ask(result.question, registry) if result.question else None

    assert matched is not None
    assert matched[0].id == "ask/how-many-owner-has-in-owned-place"
    assert (result.answer.kind, result.answer.value) == ("number", 45.0)
    assert not result.deficiencies()
    location_pronoun = next(
        unit for unit in result.premises[1].units if unit.surface == "it"
    )
    referent = next(
        obligation.target
        for obligation in location_pronoun.obligations()
        if obligation.need == "refers" and obligation.met
    )
    assert referent.features["lemma"] == "garden"


def test_owned_location_ask_requires_subject_and_possessor_to_agree(registry) -> None:
    result = solve(
        "Tova has a garden with flowers. "
        "Twelve of them are yellow, and there are 50% more of those in purple. "
        "There are 50% as many green flowers as there are yellow and purple flowers. "
        "How many flowers does Mira have in her garden?",
        registry,
    )

    assert not result.answer.committed


def test_owned_location_evidence_precedes_holder_fallback(registry) -> None:
    result = solve(
        "Tova has 4 flowers. "
        "Tova's garden has 8 flowers. "
        "How many flowers does Tova have in her garden?",
        registry,
    )

    assert (result.answer.kind, result.answer.value) == ("number", 8.0)


def test_missing_collection_context_never_guesses_a_holder(registry) -> None:
    result = solve(
        "Sixteen of them are red, and there are 25% more of them in blue. "
        "There are 25% as many green marbles as there are red and blue marbles. "
        "How many marbles are there?",
        registry,
    )

    assert not result.answer.committed
    assert not result.store.by_kind(Quantity)


@pytest.mark.parametrize(
    "standards",
    ["red and yellow marbles", "red and red marbles"],
)
def test_aggregate_share_requires_two_distinct_known_siblings(
    registry, standards
) -> None:
    result = solve(
        "Mira has a pantry with marbles. "
        "Sixteen of them are red, and there are 25% more of them in blue. "
        f"There are 25% as many green marbles as there are {standards}. "
        "How many marbles are in Mira's pantry?",
        registry,
    )

    assert any(result.store.by_kind(PartitionAggregateShare))
    assert not result.answer.committed
    assert result.veto is not None
    assert "named prior partitions" in result.veto.reason


def test_possessed_location_ask_does_not_borrow_another_owners_parts(
    registry,
) -> None:
    result = solve(
        "Mira has a pantry with marbles. "
        "Sixteen of them are red, and there are 25% more of them in blue. "
        "There are 25% as many green marbles as there are red and blue marbles. "
        "How many marbles are in Tova's pantry?",
        registry,
    )
    matched = match_ask(result.question, registry) if result.question else None

    assert matched is not None
    assert matched[0].id == "ask/how-many-in-owned-place"
    assert not result.answer.committed


@pytest.mark.parametrize(
    "rule_id",
    [
        "arithmetic/possessed-location-collection-context",
        "arithmetic/collection-attribute-class-frame",
        "arithmetic/partition-cardinal-proportional-delta",
        "arithmetic/partition-aggregate-share",
    ],
)
def test_new_partition_premises_are_generator_reachable(project, rule_id) -> None:
    candidate = generate_candidate(project, rule_id=rule_id, seed=19)

    assert candidate.target_status == "matched"
    assert candidate.target_rule == rule_id


@pytest.mark.parametrize("item, lemma", [("flowers", "flower"), ("plants", "plant")])
def test_attribute_class_context_reuses_the_target_collection(
    project, item, lemma
) -> None:
    candidate = generate_candidate(
        project,
        rule_id="arithmetic/collection-attribute-class-frame",
        seed=19,
        locked_bindings={"verb": "planted", "item": item},
    )

    assert candidate.target_status == "matched"
    assert candidate.context_before[0].endswith(f"with {item}.")
    result = solve(candidate.to_json()["text"], project.registry)
    contexts = result.store.by_kind(CollectionContext)
    assert len(contexts) == 1
    assert candidate.target_bindings["item"] == item
    assert contexts[0].collection == lemma
    assert not result.store.by_kind(Quantity)


def test_attribute_class_context_has_no_independent_semantic_filter(project) -> None:
    rule = next(
        rule for rule in project.registry.rules
        if rule.id == "arithmetic/collection-attribute-class-frame"
    )
    context = rule.generation_context
    assert context is not None
    token = next(
        token for token in context.before[0].sentence
        if token.slot == "context_item"
    )
    assert token.type == "plural"
    assert token.cat is None
    assert context.target_identity_links["context_item"] == "item"
    owner = next(token for token in context.before[0].sentence if token.slot == "context_owner")
    target_owner = next(token for token in rule.match["sentence"] if token.slot == "who")
    assert owner.type == target_owner.type == "entity"
    assert owner.bare_reference_category == target_owner.bare_reference_category


@pytest.mark.parametrize(
    "verb, item",
    [
        ("planted", "plants"),
        ("sold", "pencils"),
        ("made", "toys"),
        ("ate", "cookies"),
        ("found", "marbles"),
    ],
)
def test_attribute_class_frame_uses_each_verbs_declared_roles(
    project, verb, item
) -> None:
    result = solve(
        f"Tova has a storeroom with {item}. "
        f"Tova {verb} {item} of three different colors in it.",
        project.registry,
    )
    matched = {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }
    assert "arithmetic/collection-attribute-class-frame" in matched
    assert not result.deficiencies()
    assert not result.store.by_kind(Quantity)
    predicates = result.store.by_kind(Predication)
    assert len(predicates) == 1
    assert predicates[0].subject == "tova"
    assert predicates[0].dobj_unquantified

    candidate = generate_candidate(
        project,
        rule_id="arithmetic/collection-attribute-class-frame",
        seed=19,
        locked_bindings={"verb": verb, "item": item},
    )
    assert candidate.target_status == "matched"
    assert not candidate.deficiencies
    assert candidate.context_before[0].endswith(f"with {item}.")


@pytest.mark.parametrize(
    "subject, verb, item",
    [
        ("Tova", "planted", "pencils"),
        ("Tova", "ate", "pencils"),
        ("The cupboard", "planted", "plants"),
        ("Tova", "had", "plants"),  # No declared actor/theme frame.
    ],
)
def test_attribute_class_frame_requires_one_compatible_actor_theme_frame(
    registry, subject, verb, item
) -> None:
    result = solve(
        f"Tova has a storeroom with {item}. "
        f"{subject} {verb} {item} of three different colors in it. "
        f"How many {item} are in Tova's storeroom?",
        registry,
    )
    matched = {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }
    assert "arithmetic/collection-attribute-class-frame" not in matched
    assert not result.answer.committed


@pytest.mark.parametrize("verb", ["planted", "ate", "had"])
def test_attribute_class_generator_does_not_relax_verb_object_requirements(
    project, verb
) -> None:
    with pytest.raises(GenerationError):
        generate_candidate(
            project,
            rule_id="arithmetic/collection-attribute-class-frame",
            seed=19,
            max_attempts=2,
            locked_bindings={"verb": verb, "item": "pencils"},
        )


def test_attribute_class_rule_maps_roles_without_lexical_frame_filters(registry) -> None:
    rule = next(
        rule for rule in registry.rules
        if rule.id == "arithmetic/collection-attribute-class-frame"
    )
    tokens = {token.slot: token for token in rule.match["sentence"] if token.slot}
    assert tokens["verb"].cat == "quantity_ask_verb"
    assert tokens["verb"].finite_form
    assert tokens["item"].type == "plural"
    assert tokens["item"].cat is None
    roles = next(
        predicate.verb_roles_compatible for predicate in rule.where
        if predicate.verb_roles_compatible is not None
    )
    assert roles.roles == {"actor": ["who"], "theme": ["item"]}
    assert not roles.frame_categories
    assert roles.require_declared_frame


@pytest.mark.parametrize("verb", ["ate", "sold"])
def test_uncounted_attribute_class_activity_does_not_preserve_a_stale_holding(
    registry, verb
) -> None:
    result = solve(
        "Tova has a pantry with cookies. Tova has 10 cookies. "
        f"Tova {verb} cookies of three different colors in it. "
        "How many cookies does Tova have?",
        registry,
    )
    assert not result.deficiencies()
    assert not result.answer.committed


def test_uncounted_attribute_class_activity_does_not_allow_a_partial_event_total(
    registry,
) -> None:
    result = solve(
        "Tova has a pantry with cookies. Tova ate 2 cookies. "
        "Tova ate cookies of three different colors in it. "
        "How many cookies did Tova eat?",
        registry,
    )
    assert not result.deficiencies()
    assert not result.answer.committed


def test_earlier_predicate_cannot_erase_attribute_class_amount_uncertainty(
    registry,
) -> None:
    result = solve(
        "Tova has a pantry with cookies. Tova ate cookies. Tova has 10 cookies. "
        "Tova ate cookies of three different colors in it. "
        "How many cookies does Tova have?",
        registry,
    )
    assert not result.deficiencies()
    assert not result.answer.committed
    assert any(p.dobj_unquantified for p in result.store.by_kind(Predication))


@pytest.mark.parametrize(
    "premise, question, expected",
    [
        ("Mira has 8 cookies.", "How many cookies does Mira have?", 8),
        ("Tova has 6 pencils.", "How many pencils does Tova have?", 6),
        ("Tova sold 2 cookies.", "How many cookies did Tova sell?", 2),
    ],
)
def test_uncounted_activity_does_not_block_an_independent_answer(
    registry, premise, question, expected
) -> None:
    result = solve(
        "Tova has a pantry with cookies. "
        f"{premise} Tova ate cookies of three different colors in it. "
        f"{question}",
        registry,
    )
    assert (result.answer.kind, result.answer.value) == ("number", expected)
