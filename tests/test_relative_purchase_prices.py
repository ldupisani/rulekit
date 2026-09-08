"""Invented whole-purchase price comparisons, independent of item vocabulary."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Expenditure


@pytest.fixture(scope="module", params=["curated", "gsm8k"])
def reg(request):
    return load_project(Path("projects") / request.param).registry


def basket(*, reference="red book", tail=""):
    return ("Cato buys a red book for $18, a blue book that costs half the price of the "
            + reference + ", and a green book that costs twice the price of the red book" + tail + ". ")


def test_qualified_purchase_prices(reg):
    result = solve(basket() + "How much does Cato spend?", reg)
    assert result.answer.value == 63, result.answer
    costs = result.store.by_kind(Expenditure)
    assert len(costs) == 3
    assert [e.value for e in costs] == [18, None, None]
    assert [(e.cost_reference, e.cost_reference_qualifier) for e in costs[1:]] == [("book", "red")] * 2


@pytest.mark.parametrize("text,expected", [
    ("Dena buys 3 pounds of sugar for $16, a box of apples that costs half the price of the sugar, "
     "and a bottle of water that costs twice the price of the sugar. How much does Dena spend?", 56),
    ("Dena buys 3 red books for $16 and 2 blue books that cost half the price of the red books. "
     "How much does Dena spend?", 24),
    ("Dena buys 3 red books for $16 each and a blue book that costs half the price of the red books. "
     "How much does Dena spend?", 72),
    ("Dena buys a red book for $16. Dena buys a blue book that costs half the price of the red book. "
     "Dena buys a green book that costs twice the price of the blue book. How much does Dena spend?", 40),
    ("Dena buys a red book for $16, a blue book which costs half the price of the red book, "
     "and a green book which costs twice the price of the blue book. How much does Dena spend?", 40),
    ("Dena will serve cheese at her party. She buys 3 pounds of cream cheese for $16, "
     "a pound of cheddar cheese that costs half the price of the cream cheese, "
     "and a pack of cold cuts that costs twice the price of the cream cheese. "
     "How much does she spend on the ingredients?", 56),
])
def test_lots_unit_prices_chains_and_collectives(reg, text, expected):
    result = solve(text, reg)
    assert result.answer.value == expected, result.answer


@pytest.mark.parametrize("text", [
    basket(reference="yellow book") + "How much does Cato spend?",
    basket(reference="book") + "How much does Cato spend?",
    basket(tail=", and a hat") + "How much does Cato spend?",
    basket(tail=", and a hat with Dena") + "How much does Cato spend?",
    basket(tail=", and buys a hat") + "How much does Cato spend?",
    basket() + "Cato buys a hat. How much does Cato spend?",
    basket() + "Cato buys a red book for $18. How much does Cato spend?",
    basket() + "Cato buys a hat for £5. How much does Cato spend?",
    basket() + "Dena buys a hat for $5. How much does Cato spend?",
    basket() + "Cato has 7 apples. How much does Cato spend?",
    basket() + "Cato received money. How much does Cato spend?",
    basket() + "How much does Cato spend tomorrow?",
    basket() + "How much does Cato spend on the ingredients?",
    basket().replace("$18", "-$18") + "How much does Cato spend?",
    basket().replace("buys", "can buy") + "How much does Cato spend?",
    basket().replace("and a green", "or a green") + "How much does Cato spend?",
    "Cato buys a red book that costs twice the price of the blue book and a blue book "
    "that costs half the price of the red book. How much does Cato spend?",
])
def test_incomplete_ambiguous_or_unscoped_costs_decline(reg, text):
    result = solve(text, reg)
    assert not result.answer.committed, result.answer


def test_relative_prices_reuse_the_budget_account(reg):
    result = solve("Cato has a budget of $100. " + basket()
                   + "How much money does Cato have left?", reg)
    assert result.answer.value == 37, result.answer


def test_a_separate_nonnumeric_clause_does_not_leave_the_list_open(reg):
    result = solve(basket(tail=", but lost the receipt") + "How much does Cato spend?", reg)
    assert result.answer.value == 63, result.answer


def test_fractional_price_cannot_be_a_residual_without_its_anchor(reg):
    result = solve("Cato has a budget of $100. Cato buys a blue book that costs half the price "
                   "of the red book. Cato has $70 left from his budget. "
                   "How much did Cato pay for the blue book?", reg)
    assert not result.answer.committed, result.answer


def test_owned_buyers_cannot_share_a_bare_price_anchor(reg):
    result = solve("Cato's teacher buys a red book for $18. Dena's teacher buys a blue book "
                   "that costs half the price of the red book. How much does Dena's teacher spend?", reg)
    assert not result.answer.committed, result.answer
