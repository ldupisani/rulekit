"""Sequential percentages taken from a shrinking remainder pool."""

from __future__ import annotations

import pytest

from rulekit.kernel.engine import solve
from rulekit.kernel.model import (
    PartitionQuantity,
    SequentialPartitionInitialShare,
    SequentialPartitionPrefix,
    SequentialPartitionRemainingShare,
    SequentialPartitionRemainder,
)


def test_second_share_is_taken_from_the_remainder(registry):
    result = solve(
        "In a university with 800 students, 25% enrolled in science courses, "
        "20% of the remaining enrolled in business courses, and the rest "
        "enrolled in humanities courses. What percentage of the students "
        "enrolled in humanities courses?",
        registry,
    )

    assert result.answer.value == pytest.approx(60)
    partitions = {
        fact.attribute: fact.value
        for fact in result.store.by_kind(PartitionQuantity)
    }
    assert partitions == {
        "science course": pytest.approx(200),
        "business course": pytest.approx(120),
        "humanities course": pytest.approx(480),
    }


def test_sequential_percentages_are_not_both_taken_from_the_original(registry):
    result = solve(
        "In a university with 500 students, 10% enrolled in science courses, "
        "50% of the remaining enrolled in business courses, and the rest "
        "enrolled in humanities courses. What percentage of the students "
        "enrolled in business courses?",
        registry,
    )

    assert result.answer.value == pytest.approx(45)


def test_sequential_partition_can_answer_a_destination_count(registry):
    result = solve(
        "In a university with 800 students, 25% enrolled in science courses, "
        "20% of the remaining enrolled in business courses, and the rest "
        "enrolled in humanities courses. How many of the students enrolled "
        "in humanities courses?",
        registry,
    )

    assert result.answer.value == pytest.approx(480)


def test_sequential_partition_count_accepts_no_partitive_prefix(registry):
    result = solve(
        "In a university with 800 students, 25% enrolled in science courses, "
        "20% of the remaining enrolled in business courses, and the rest "
        "enrolled in humanities courses. How many students enrolled in "
        "humanities courses?",
        registry,
    )

    assert result.answer.value == pytest.approx(480)


def test_sequential_partition_count_requires_a_named_destination(registry):
    result = solve(
        "In a university with 800 students, 25% enrolled in science courses, "
        "20% of the remaining enrolled in business courses, and the rest "
        "enrolled in humanities courses. How many of the students enrolled "
        "in courses?",
        registry,
    )

    assert result.answer.kind == "decline"


def test_sequential_partition_resolves_an_implicit_prior_collection(registry):
    result = solve(
        "A university has 800 students. 25% enrolled in science courses, "
        "20% of the remaining enrolled in business courses, and the rest "
        "enrolled in humanities courses. How many students enrolled in "
        "humanities courses?",
        registry,
    )

    assert result.answer.value == pytest.approx(480)
    partitions = {
        fact.attribute: fact.value
        for fact in result.store.by_kind(PartitionQuantity)
    }
    assert partitions == {
        "science course": pytest.approx(200),
        "business course": pytest.approx(120),
        "humanities course": pytest.approx(480),
    }


def test_implicit_partition_second_share_uses_the_remainder(registry):
    result = solve(
        "A university has 500 students. 10% enrolled in science courses, "
        "50% of the remaining enrolled in business courses, and the rest "
        "enrolled in humanities courses. How many students enrolled in "
        "business courses?",
        registry,
    )

    assert result.answer.value == pytest.approx(225)


def test_implicit_partition_accepts_a_separate_rest_sentence(registry):
    result = solve(
        "A university has 800 students. 25% enrolled in science courses, "
        "20% of the remaining enrolled in business courses. The rest "
        "enrolled in humanities courses. How many students enrolled in "
        "humanities courses?",
        registry,
    )

    assert result.answer.value == pytest.approx(480)
    assert len(result.store.by_kind(SequentialPartitionPrefix)) == 1
    assert len(result.store.by_kind(SequentialPartitionRemainder)) == 1
    partitions = {
        fact.attribute: fact.value
        for fact in result.store.by_kind(PartitionQuantity)
        if fact.provenance.source == "synth/sequential-partition"
    }
    assert partitions == {
        "science course": pytest.approx(200),
        "business course": pytest.approx(120),
        "humanities course": pytest.approx(480),
    }


def test_implicit_partition_accepts_every_stage_as_a_sentence(registry):
    result = solve(
        "A university has 800 students. 25% enrolled in science courses. "
        "20% of the remaining enrolled in business courses. The rest "
        "enrolled in humanities courses. How many students enrolled in "
        "humanities courses?",
        registry,
    )

    assert result.answer.value == pytest.approx(480)
    assert len(result.store.by_kind(SequentialPartitionInitialShare)) == 1
    assert len(result.store.by_kind(SequentialPartitionRemainingShare)) == 1
    partitions = {
        fact.attribute: fact.value
        for fact in result.store.by_kind(PartitionQuantity)
        if fact.provenance.source == "synth/sequential-partition"
    }
    assert partitions == {
        "science course": pytest.approx(200),
        "business course": pytest.approx(120),
        "humanities course": pytest.approx(480),
    }


def test_implicit_partition_accepts_a_two_way_complement(registry):
    result = solve(
        "A university has 800 students. 25% enrolled in science courses. "
        "The rest enrolled in humanities courses. How many students enrolled "
        "in humanities courses?",
        registry,
    )

    assert result.answer.value == pytest.approx(600)
    partitions = {
        fact.attribute: fact.value
        for fact in result.store.by_kind(PartitionQuantity)
        if fact.provenance.source
        == "synth/sequential-partition-complement"
    }
    assert partitions == {
        "science course": pytest.approx(200),
        "humanities course": pytest.approx(600),
    }


@pytest.mark.parametrize(
    "text",
    [
        # The percentages still require one earlier finite population.
        "25% enrolled in science courses. The rest enrolled in humanities "
        "courses. How many students enrolled in humanities courses?",
        # Competing earlier measures make the omitted population ambiguous.
        "A university has 800 students. Tom has 5 apples. 25% enrolled in "
        "science courses. The rest enrolled in humanities courses. How many "
        "students enrolled in humanities courses?",
        # The complement must name a different destination.
        "A university has 800 students. 25% enrolled in science courses. The "
        "rest enrolled in science courses. How many students enrolled in "
        "science courses?",
    ],
)
def test_two_way_complement_requires_one_distinct_anchored_pair(registry, text):
    assert solve(text, registry).answer.kind == "decline"


@pytest.mark.parametrize(
    "text",
    [
        # The completion cannot guess an allocation prefix.
        "A university has 800 students. The rest enrolled in humanities "
        "courses. How many students enrolled in humanities courses?",
        # The rest clause must complete the immediately preceding sentence.
        "A university has 800 students. 25% enrolled in science courses, "
        "20% of the remaining enrolled in business courses. Tom arrived. "
        "The rest enrolled in humanities courses. How many students enrolled "
        "in humanities courses?",
        # The final destination must be distinct from both earlier shares.
        "A university has 800 students. 25% enrolled in science courses, "
        "20% of the remaining enrolled in business courses. The rest enrolled "
        "in science courses. How many students enrolled in science courses?",
    ],
)
def test_split_partition_requires_one_adjacent_compatible_pair(registry, text):
    assert solve(text, registry).answer.kind == "decline"


@pytest.mark.parametrize(
    "text",
    [
        # A remaining-pool percentage cannot invent its missing first share.
        "A university has 800 students. 20% of the remaining enrolled in "
        "business courses. The rest enrolled in humanities courses. How many "
        "students enrolled in humanities courses?",
        # The second stage must immediately follow its first stage.
        "A university has 800 students. 25% enrolled in science courses. "
        "Tom arrived. 20% of the remaining enrolled in business courses. The "
        "rest enrolled in humanities courses. How many students enrolled in "
        "humanities courses?",
        # The first and second stages must name different destinations.
        "A university has 800 students. 25% enrolled in science courses. "
        "20% of the remaining enrolled in science courses. The rest enrolled "
        "in humanities courses. How many students enrolled in humanities "
        "courses?",
    ],
)
def test_fully_split_partition_requires_adjacent_distinct_stages(registry, text):
    assert solve(text, registry).answer.kind == "decline"


@pytest.mark.parametrize(
    "text",
    [
        # No prior finite population exists to supply the omitted collection.
        "25% enrolled in science courses, 20% of the remaining enrolled in "
        "business courses, and the rest enrolled in humanities courses. How "
        "many students enrolled in humanities courses?",
        # Two prior measures make the omitted collection genuinely ambiguous.
        "A university has 800 students. Tom has 5 apples. 25% enrolled in "
        "science courses, 20% of the remaining enrolled in business courses, "
        "and the rest enrolled in humanities courses. How many students "
        "enrolled in humanities courses?",
    ],
)
def test_implicit_partition_declines_without_one_prior_collection(registry, text):
    assert solve(text, registry).answer.kind == "decline"


@pytest.mark.parametrize(
    "text",
    [
        # Without the remainder marker, both percentages describe shares of
        # the original pool; this rule must not silently impose sequencing.
        "In a university with 500 students, 10% enrolled in science courses, "
        "50% enrolled in business courses, and the rest enrolled in humanities "
        "courses. What percentage of the students enrolled in humanities courses?",
        # The destinations must be genuinely distinct partitions.
        "In a university with 500 students, 10% enrolled in science courses, "
        "50% of the remaining enrolled in science courses, and the rest enrolled "
        "in humanities courses. What percentage of the students enrolled in "
        "humanities courses?",
        # A share of one finite pool cannot exceed the whole.
        "In a university with 500 students, 110% enrolled in science courses, "
        "50% of the remaining enrolled in business courses, and the rest enrolled "
        "in humanities courses. What percentage of the students enrolled in "
        "humanities courses?",
    ],
)
def test_sequential_partition_overreach_declines(registry, text):
    assert solve(text, registry).answer.kind == "decline"
