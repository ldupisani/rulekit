"""Cardinal partitives quantify a subset through an explicit collection."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import retest_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import PartitionQuantity


@pytest.fixture(scope="module")
def project():
    return load_project(Path("projects/curated"))


@pytest.mark.parametrize("sentence,target", [
    ("4 of the books are remaining.", "arithmetic/partition-attribute-of-noun"),
    ("Four of the books are left.", "arithmetic/partition-attribute-of-noun"),
    ("1 of the books is left.", "arithmetic/partition-attribute-of-noun"),
    ("4 of the marbles are red.", "arithmetic/partition-attribute-of-noun"),
    ("4 of the animals are dogs.", "arithmetic/partition-membership-of-noun"),
])
def test_named_subset_accounts_for_its_standalone_count(project, sentence, target):
    candidate = retest_candidate(
        project, rule_id=target, sentence=sentence, seed=0, origin="reading"
    )

    assert candidate.target_status == "matched"
    assert candidate.clean_reading
    assert candidate.deficiencies == ()


@pytest.mark.parametrize("premise,question,expected", [
    ("4 of the marbles are red.", "How many marbles are red?", 4),
    ("Four of the marbles are red.", "How many marbles are not red?", 8),
    ("4 of them are red.", "How many marbles are red?", 4),
    ("Four of them are red.", "How many marbles are not red?", 8),
])
def test_noun_and_pronoun_partitives_keep_direct_and_complement_answers(
    project, premise, question, expected
):
    result = solve(f"There are 12 marbles. {premise} {question}", project.registry)

    assert result.answer.committed
    assert result.value == expected
    assert not any("needs a quantifies" in gap for gap in result.deficiencies())


@pytest.mark.parametrize("collection", ["the animals", "them"])
def test_membership_partitives_account_for_counts_and_derive_subsets(
    project, collection
):
    result = solve(
        f"There are 12 animals. Four of {collection} are dogs. "
        "How many dogs are there?", project.registry,
    )

    assert result.answer.committed
    assert result.value == 4
    assert not any("needs a quantifies" in gap for gap in result.deficiencies())


def test_satisfying_the_count_does_not_supply_a_missing_collection(project):
    result = solve(
        "4 of them are red. How many marbles are red?", project.registry
    )

    assert not result.answer.committed
    assert not any("needs a quantifies" in gap for gap in result.deficiencies())


@pytest.mark.parametrize("sentence", [
    "4 apples of the books are left.",
    "4 dollars of the animals are dogs.",
    "4 books of them are red.",
    "4 of the years are red.",
])
def test_invalid_quantity_or_attribute_cannot_become_a_subset(project, sentence):
    result = solve(sentence, project.registry)

    assert not result.store.by_kind(PartitionQuantity)
