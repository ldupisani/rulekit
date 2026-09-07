"""Synthetic compositions of existing prices, accounts, and rate evidence."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Expenditure


@pytest.fixture(scope="module", params=["curated", "gsm8k"])
def reg(request):
    return load_project(Path("projects") / request.param).registry


def residual(purchase):
    return ("Mira has a budget of $180. " + purchase + " Mira bought shoes. "
            "Mira has $35 left from her budget. How much did Mira pay for the shoes?")


@pytest.mark.parametrize("purchase,expected", [
    ("Mira buys 3 toys at $10 each.", 115),
    ("Mira buys 3 toys for $10 each.", 115),
    ("Mira buys 3 toys at $10 each and 2 hats at $15 each.", 85),
    ("Mira buys 3 toys at $10 each. Mira spent $20 on a hat.", 95),
    ("Mira buys 3 toys from Tova at $10 each.", 115),
    ("Mira buys 3 toys at $10 each from Tova online.", 115),
    ("Mira buys 3 toys at $3 each and 3 hats at $3 each.", 127),
])
def test_unit_prices_feed_closed_accounts(reg, purchase, expected):
    result = solve(residual(purchase), reg)
    assert result.answer.value == expected, result.answer
    expenses = result.store.by_kind(Expenditure)
    priced = [e for e in expenses if e.unit_price is not None]
    assert priced and all(e.quantity is not None and e.value is None for e in priced)


@pytest.mark.parametrize("purchase", [
    "Mira buys 3 toys at $10.",
    "Mira buys 3 toys near $10 each.",
    "Mira buys 3 toys at $10 each for Tova.",
    "Mira buys 3 toys at $10 each or 2 hats at $15 each.",
    "Mira buys 3 toys at $10 each and 2 hats.",
    "Mira buys 3 toys at $10 each. Mira paid $30 for the toys.",
    "Mira buys -3 toys at $10 each.",
    "Mira buys 3 toys at -$10 each.",
    "Tova buys 3 toys at $10 each.",
    "Mira buys 3 toys at £10 each.",
    "Mira buys 3 toys at $10 each with Tova's budget.",
    "Mira buys 3 toys at $10 each. Mira has 3 apples.",
])
def test_incomplete_or_mismatched_priced_accounts_decline(reg, purchase):
    result = solve(residual(purchase), reg)
    assert not result.answer.committed, result.answer


def test_old_unit_price_total_still_works(reg):
    result = solve("Mira buys 3 toys at $10 each. How much did Mira spend?", reg)
    assert result.answer.value == 30, result.answer


@pytest.mark.parametrize("text,expected", [
    ("Mira has a budget of $180. Mira bought a hat for $30. How much money does Mira have left?", 150),
    ("Mira has a budget of $180. Mira buys 3 toys at $10 each. How much money does Mira have left?", 150),
    ("Mira has a budget of $180. Mira spent $30 on a hat and $40 on a coat. How much money does Mira have left?", 110),
    ("Mira has a budget of $180. Hats cost $30 each. How many hats can Mira buy?", 6),
    ("Mira has a budget of $180. Mira buys 3 toys at $10 each. Hats cost $30 each. How many hats can Mira buy?", 5),
    ("Mira has a budget of $180. Mira bought a coat for $50. Hats cost $30 each. How many hats can Mira buy?", 4),
    ("Mira has a budget of $180. Mira bought a coat for $50. Mira has $130 left from her budget. How much money does Mira have left?", 130),
])
def test_existing_asks_reuse_scoped_account_totals(reg, text, expected):
    result = solve(text, reg)
    assert result.answer.value == expected, result.answer
    assert "budget" in result.answer.reason


@pytest.mark.parametrize("text", [
    "Mira has a budget of $180. Mira bought shoes. How much money does Mira have left?",
    "Mira has a budget of $180. Mira bought a hat for $30. Mira has $140 left from her budget. How much money does Mira have left?",
    "Mira has a budget of $180. How much money in pounds does Mira have left?",
    "Mira has a budget of $180. Mira has $50. How much money does Mira have left?",
    "Mira has a budget of $180. How much money does Mira have?",
    "Mira has a budget of $180. How much money does Mira have left tomorrow?",
    "Mira has a budget of $180. Hats cost £30 each. How many hats can Mira buy?",
    "Mira has a budget of $180. Hats cost $0 each. How many hats can Mira buy?",
    "Mira has a budget of $180. Hats cost $30 each. How many hats can Mira buy with $90?",
    "Mira has a budget of $180. Hats cost $30 each for Tova. How many hats can Mira buy?",
    "Mira has a budget of $180. Red hats cost $30 each. How many hats can Mira buy?",
    "Mira has a budget of $180. Mira bought a hat for $30. How many hats can Mira buy?",
    "Mira has a budget of $180. Mira bought shoes. Hats cost $30 each. How many hats can Mira buy?",
])
def test_account_reuse_keeps_scope_and_completeness_guards(reg, text):
    result = solve(text, reg)
    assert not result.answer.committed, result.answer


@pytest.mark.parametrize("text,expected", [
    ("Mira earns $40 in 2 hours. Mira works 3 hours every day for 4 days. How much money does Mira earn?", 240),
    ("Mira earns $40 in 120 minutes. Mira works 3 hours every day for 4 days. How much money does Mira earn?", 240),
    ("Mira earns $20 an hour for tutoring. Mira does 3 hours of tutoring every day for 4 days. How much money does Mira earn?", 240),
    ("Mira earns $20 an hour for gardening. Mira does 90 minutes of gardening every day for 4 days. How much money does Mira earn?", 120),
    ("Mira earns $20 an hour for babysitting. Mira does 3 hours of babysitting every shift for 4 shifts. How much money does Mira earn?", 240),
])
def test_shared_rates_accept_compound_and_matching_activity_evidence(reg, text, expected):
    result = solve(text, reg)
    assert result.answer.value == expected, result.answer


@pytest.mark.parametrize("replacement", [
    "Mira does 3 hours of gardening every day for 4 days.",
    "Mira works 3 hours every day for 4 days.",
    "Tova does 3 hours of tutoring every day for 4 days.",
    "Mira does 3 hours of tutoring every day for 4 shifts.",
    "Mira does 3 hours of tutoring every day for 4 days without Tova.",
])
def test_repeated_activity_cannot_borrow_another_scope(reg, replacement):
    result = solve("Mira earns $20 an hour for tutoring. " + replacement
                   + " How much money does Mira earn?", reg)
    assert not result.answer.committed, result.answer


def test_compound_rate_reuses_per_session_premium_arithmetic(reg):
    result = solve(
        "Mira earns $40 in 2 hours. If she works more than 6 hours per shift, "
        "she is eligible for overtime, which is paid by your hourly wage + 1/4 your hourly wage. "
        "Mira works 9 hours every shift for 4 shifts. How much money does Mira earn?", reg,
    )
    assert result.answer.value == 780, result.answer


@pytest.mark.parametrize("project_name", ["curated", "gsm8k"])
def test_scoped_schedule_generates_and_round_trips(project_name):
    from rulekit.generation import generate_candidate
    project = load_project(Path("projects") / project_name)
    result = generate_candidate(project, rule_id="arithmetic/repeated-scoped-activity-duration", seed=11)
    assert result.target_status in {"matched", "shadowed"}, result
