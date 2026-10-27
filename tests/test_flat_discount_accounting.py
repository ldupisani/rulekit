"""Flat discount ellipsis accounts for amounts without inventing units."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import retest_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Discount


@pytest.fixture(scope="module")
def project():
    return load_project(Path("projects/curated"))


@pytest.mark.parametrize("amount", ["6", "six", "$6", "6 dollars"])
def test_flat_off_fragment_accounts_for_its_amount(project, amount):
    candidate = retest_candidate(
        project,
        rule_id="arithmetic/discount-flat-off",
        sentence=f"{amount} off.",
        seed=0,
        origin="reading",
    )

    assert candidate.target_status == "matched"
    assert candidate.clean_reading
    assert candidate.deficiencies == ()
    discounts = [fact for fact in candidate.facts if fact["type"] == "Discount"]
    assert len(discounts) == 1
    assert discounts[0]["fields"] == {
        "value": 6, "percent": False, "scope": "total"
    }


@pytest.mark.parametrize("item", ["book", "drum"])
@pytest.mark.parametrize("amount", ["6", "six", "$6", "6 dollars"])
def test_flat_off_inherits_the_priced_purchase_unit(project, item, amount):
    result = solve(
        f"Dena buys a {item} for $40 and gets {amount} off. "
        "How much did Dena pay?",
        project.registry,
    )

    assert result.answer.committed
    assert result.value == 34
    assert not any("needs a quantifies" in gap for gap in result.deficiencies())


@pytest.mark.parametrize("amount", ["6 apples", "6 kilograms", "6 years"])
def test_nonmonetary_count_cannot_become_a_flat_discount(project, amount):
    result = solve(f"{amount} off.", project.registry)

    assert not result.store.by_kind(Discount)


def test_flat_discount_without_a_priced_purchase_cannot_be_an_answer(project):
    result = solve("6 off. How much did Dena pay?", project.registry)

    assert not result.answer.committed
    assert len(result.store.by_kind(Discount)) == 1


def test_percent_off_keeps_its_distinct_discount_type(project):
    result = solve(
        "Dena buys a book for $40 and gets 20% off. How much did Dena pay?",
        project.registry,
    )

    assert result.answer.committed
    assert result.value == 32
    discounts = result.store.by_kind(Discount)
    assert len(discounts) == 1
    assert discounts[0].percent


def test_flat_discount_does_not_account_for_an_unrelated_number(project):
    result = solve(
        "Dena buys a book for $40. 6 off for 9. How much did Dena pay?",
        project.registry,
    )

    assert not result.answer.committed
    assert [gap for gap in result.deficiencies() if "needs a quantifies" in gap] == [
        "'9' (value) needs a quantifies and none was found."
    ]


@pytest.mark.parametrize("amount", ["6", "six", "$6", "6 dollars"])
@pytest.mark.parametrize("suffix,scope", [("", "total"), (" each", "per_unit")])
def test_discount_of_accounts_for_its_amount_and_elliptical_collection(
    project, amount, suffix, scope
):
    candidate = retest_candidate(
        project, rule_id=f"arithmetic/discount-of-flat-{'total' if not suffix else 'per-unit'}",
        sentence=f"Discount of {amount}{suffix}.", seed=0, origin="reading",
    )

    assert candidate.target_status == "matched"
    assert candidate.clean_reading
    assert candidate.deficiencies == ()
    assert [(f["type"], f["fields"]) for f in candidate.facts] == [
        ("Discount", {"value": 6, "percent": False, "scope": scope})
    ]


@pytest.mark.parametrize("amount", ["6 apples", "6 kilograms", "6 years"])
@pytest.mark.parametrize("suffix", ["", " each"])
def test_discount_of_rejects_explicit_noncurrency_measures(project, amount, suffix):
    result = solve(f"Discount of {amount}{suffix}.", project.registry)

    assert not result.store.by_kind(Discount)


@pytest.mark.parametrize("suffix", ["", " each"])
def test_complete_discount_fragment_never_invents_a_purchase(project, suffix):
    result = solve(f"Discount of 6{suffix}. How much did Fia pay?", project.registry)

    assert result.deficiencies() == []
    assert not result.answer.committed


@pytest.mark.parametrize("item", ["books", "drums"])
@pytest.mark.parametrize("suffix,expected", [("", 28), (" each", 24)])
def test_discount_of_preserves_total_versus_per_unit_arithmetic(project, item, suffix, expected):
    result = solve(
        f"Fia bought 3 {item} for $10 each. Discount of 2{suffix}. "
        "How much did Fia pay?", project.registry,
    )

    assert result.answer.committed
    assert result.value == expected
    assert result.deficiencies() == []
