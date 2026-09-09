"""Invented bounded production accounts; no corpus questions."""

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import CommercialTerm


@pytest.fixture(scope="module")
def registry():
    return load_project("projects/curated").registry


def story():
    return ("Mira creates a company. She creates an album for $300. "
            "Each CD costs $4 to make. She sells it for 3 times that much. "
            "She sells 30 albums a day for 4 days a week. "
            "How much profit does she make in 6 weeks?")


def test_scheduled_sales_minus_unit_and_fixed_costs(registry):
    r = solve(story(), registry)
    assert r.value == 5460, r.answer
    assert len(r.store.by_kind(CommercialTerm)) == 3
    assert r.answer.proof.steps[0].rule == "closed-production-account"


@pytest.mark.parametrize("old,new,expected", [
    ("3 times", "2.5 times", 4020),
    ("$300", "$7000", -1240),
    ("an album", "a book", None),
    ("an album", "a film", None),
    ("4 days a week", "4 hours a week", None),
    ("6 weeks", "0 weeks", -300),
    ("Each CD costs $4 to make. ", "", None),
    ("She creates an album for $300. ", "", None),
    ("She sells it for 3 times that much. ", "", None),
    ("She sells it", "Tom sells it", None),
    ("Each CD costs $4 to make.", "Each CD costs $4 to make. Each CD costs $5 to make.", None),
    ("She sells it", "She creates a company. She sells it", None),
    ("How much profit", "She spent $7. How much profit", None),
    ("How much profit", "She spent money. How much profit", None),
    ("6 weeks?", "6 weeks after spending $3?", None),
])
def test_account_boundaries(registry, old, new, expected):
    r = solve(story().replace(old, new), registry)
    assert r.value == expected, r.answer


def test_explicit_price_and_another_product_family(registry):
    text = (story().replace("an album", "a book").replace("albums", "books")
            .replace("CD", "paperback").replace("it for 3 times that much", "each paperback for $12"))
    r = solve(text, registry)
    assert r.value == 5460, r.answer


def test_cost_quotes_cannot_be_ignored_by_a_holding_ask(registry):
    text = story().split("How much")[0] + "Mira has $20. How much money does Mira have?"
    assert not solve(text, registry).answer.committed


@pytest.mark.parametrize("rule", [
    "commercial-organization-context", "production-setup-cost",
    "unit-production-cost", "relative-unit-sale-price",
    "explicit-unit-sale-price", "nested-unit-sales-cadence",
])
def test_premise_generation_round_trips(rule):
    from rulekit.generation import generate_candidate
    candidate = generate_candidate(load_project("projects/curated"),
                                   rule_id="arithmetic/" + rule, seed=11)
    assert candidate.target_status == "matched"
    assert candidate.facts


def test_price_predicate_is_unambiguous_without_losing_nominal_costs(registry):
    from rulekit.kernel.engine import analyze
    price = analyze("Each paperback costs $7 to make.", registry)
    cost = next(u for u in price.units if u.features.get("lemma") == "cost")
    assert cost.senses() == ["verb"]
    noun = analyze("The costs are high.", registry)
    assert next(u for u in noun.units if u.features.get("lemma") == "cost").sense() == "noun"


def test_repeated_unqualified_fractional_payments_do_not_guess_the_base(registry):
    text = ("Mira earns $160. She spends half of the money on CDs. "
            "She spends one fourth of the money on books. How much does Mira have?")
    assert not solve(text, registry).answer.committed


def test_explicit_remainder_keeps_sequential_fractional_payments(registry):
    text = ("Mira earns $160. She spends half of the money on CDs. "
            "She spends one fourth of the remaining money on books. How much does Mira have?")
    r = solve(text, registry)
    assert r.value == 60, r.answer
