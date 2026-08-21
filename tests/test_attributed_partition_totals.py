"""Attributed subgroups whose stated parts determine a collection total.

All prose is synthetic. The class combines an uncounted collection context,
a cardinal subgroup, a proportional sibling, and a final subgroup sized from
the explicitly coordinated sibling total.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation.sample import generate_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import (
    CollectionContext,
    PartitionAggregateShare,
    PartitionQuantity,
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
        "arithmetic/partition-cardinal-proportional-delta",
        "arithmetic/partition-aggregate-share",
    ],
)
def test_new_partition_premises_are_generator_reachable(project, rule_id) -> None:
    candidate = generate_candidate(project, rule_id=rule_id, seed=19)

    assert candidate.target_status == "matched"
    assert candidate.target_rule == rule_id
