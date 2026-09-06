"""Independent allocation phrases, transactions, and closed-account evidence."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import (
    Expenditure, ResourceAccountingIssue, ResourceAllocation, ResourceBalance, VerbalRelation,
)


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/curated")).registry


def narrative(opening="Mira has a budget of $180.", known=None, unknown="Mira bought shoes.", closing=None):
    return " ".join((
        opening,
        known or "Mira spent $30 on a hat and $40 on a coat.",
        unknown,
        closing or "Mira has $35 left from her budget.",
        "How much did Mira pay for the shoes?",
    ))


@pytest.mark.parametrize("opening", [
    "Mira has a budget of $180.",
    "Mira has a $180 budget.",
    "Mira went to a store with a budget of $180.",
    "Mira traveled with a budget of $180.",
    "Mira shopped online with a budget of $180.",
    "Mira shopped online with a $180 budget.",
    "With a budget of $180, Mira shopped online.",
    "With a $180 budget, Mira shopped online.",
])
def test_activity_independent_allocation(reg, opening):
    result = solve(narrative(opening), reg)
    assert result.answer.value == 75, result.answer
    assert len(list(result.store.by_kind(ResourceAllocation))) == 1
    assert {b.entity for b in result.store.by_kind(ResourceBalance)} == {"mira"}


def test_common_noun_account_holders_keep_the_existing_animate_boundary(reg):
    result = solve("The shopper has a budget of $180.", reg)
    balance, = result.store.by_kind(ResourceBalance)
    assert balance.entity == "shopper"


@pytest.mark.parametrize("opening", [
    "Mira went to a store that had a budget of $180.",
    "Mira went to a store whose budget was $180.",
    "Mira went to a store with its budget of $180.",
])
def test_retailer_context_cannot_assign_its_budget_to_the_customer(reg, opening):
    result = solve(narrative(opening), reg)
    assert not result.answer.committed
    assert not any(b.stage == "opening" and b.entity == "mira" for b in result.store.by_kind(ResourceBalance))


def test_nonpersonal_remainder_owner_is_not_silently_rebound(reg):
    result = solve(narrative(closing="Mira has $35 left from its budget."), reg)
    assert not result.answer.committed
    assert "owner-reference" in {f.reason for f in result.store.by_kind(ResourceAccountingIssue)}


@pytest.mark.parametrize("known", [
    "Mira bought a hat for $30. Mira bought a coat for $40.",
    "Mira bought a hat from Tova for $30. Mira bought a coat for $40 from Cato.",
    "Mira paid Tova $30 for a hat and $40 for a coat.",
    "Mira paid the retailer $30 for a hat. Mira paid the store $40 for a coat.",
    "Mira bought a hat from an online retailer for $30 and a coat for $40.",
    "Mira spent $30 on a hat online and $40 on a coat online.",
])
@pytest.mark.parametrize("unknown", [
    "Mira bought shoes from Cato.",
    "Mira bought shoes from the retailer.",
    "Mira purchased shoes online.",
    "Mira bought shoes with her budget.",
])
def test_shared_cost_records_across_transaction_forms(reg, known, unknown):
    result = solve(narrative(known=known, unknown=unknown), reg)
    assert result.answer.value == 75, result.answer


def test_allocation_inside_purchase_does_not_become_its_price(reg):
    result = solve(narrative(
        opening="Mira bought a hat for $30 with a budget of $180.",
        known="Mira bought a coat for $40.",
    ), reg)
    assert result.answer.value == 75, result.answer
    assert [e.value for e in result.store.by_kind(Expenditure)] == [30, 40, None]


def test_read_purchase_supplier_and_channel_without_any_budget(reg):
    result = solve("Mira bought shoes from Tova online.", reg)
    expense, = result.store.by_kind(Expenditure)
    assert (expense.entity, expense.item, expense.supplier, expense.channel) == ("mira", "shoe", "tova", "online")
    assert (expense.basis, expense.value) == ("purchase", None)
    assert not list(result.store.by_kind(ResourceBalance))
    assert not any(f.role.startswith("spatial-") for f in result.store.by_kind(VerbalRelation))


def test_payment_keeps_the_payee_without_asserting_a_purchase(reg):
    result = solve("Mira paid Tova $30 for a hat.", reg)
    expense, = result.store.by_kind(Expenditure)
    assert (expense.basis, expense.supplier, expense.value) == ("payment", "tova", 30)


def test_qualified_supplier_does_not_turn_its_descriptor_into_a_channel(reg):
    result = solve("Mira bought shoes from an online retailer.", reg)
    expense, = result.store.by_kind(Expenditure)
    assert (expense.supplier, expense.supplier_qualifier, expense.channel) == ("retailer", "online", "")


@pytest.mark.parametrize("opening", [
    "Mira has a clothing budget of $180.",
    "Mira has a $180 clothing budget.",
])
def test_qualified_account_scope_survives_all_records(reg, opening):
    result = solve(narrative(
        opening=opening, unknown="Mira bought shoes with her clothing budget.",
        closing="Mira has $35 left from her clothing budget.",
    ), reg)
    assert result.answer.value == 75, result.answer
    assert {b.qualifier for b in result.store.by_kind(ResourceBalance)} == {"clothing"}
    assert next(e for e in result.store.by_kind(Expenditure) if e.value is None).account_qualifier == "clothing"


@pytest.mark.parametrize("opening", [
    "A budget of $180.",
    "Mira went to a store near a budget of $180.",
    "Mira went to a store with Tova's budget of $180.",
    "Mira went to a store with Tova's $180 budget.",
    "Mira and Tova shopped with a budget of $180.",
    "Mira can shop with a budget of $180.",
    "Mira never had a budget of $180.",
    "Mira has a budget of $180. Tova has a budget of $60.",
])
def test_unattached_foreign_ambiguous_or_nonactual_allocation_declines(reg, opening):
    result = solve(narrative(opening), reg)
    assert not result.answer.committed, result.answer


@pytest.mark.parametrize("unknown", [
    "Mira ordered shoes.",
    "Mira will purchase shoes from Tova.",
    "Mira bought shoes near Tova.",
    "Mira bought shoes from Tova or Cato.",
    "Mira bought shoes from Tova and Cato.",
    "Mira bought shoes from Tova from Cato.",
    "Mira bought shoes with Tova's budget.",
    "Mira bought shoes with Tova's $180 budget.",
    "Mira bought shoes with her clothing budget.",
    "Mira bought shoes. Mira ordered a belt.",
])
def test_incomplete_or_differently_scoped_transaction_declines(reg, unknown):
    result = solve(narrative(unknown=unknown), reg)
    assert not result.answer.committed, result.answer


def test_purchase_and_payment_are_not_summed_as_two_expenses(reg):
    result = solve(narrative(known="Mira bought a hat for $30. Mira paid Tova $30 for the hat."), reg)
    assert not result.answer.committed
    assert "same transaction" in result.answer.reason


def test_account_labels_are_not_discarded(reg):
    result = solve(narrative(opening="Mira has a clothing budget of $180."), reg)
    assert not result.answer.committed
    assert {b.qualifier for b in result.store.by_kind(ResourceBalance)} == {"clothing", ""}


def test_relevant_unread_changes_are_inspectable_facts(reg):
    result = solve(narrative(unknown="Mira bought shoes. Mira lost money."), reg)
    assert not result.answer.committed
    assert "additional-change" in {f.reason for f in result.store.by_kind(ResourceAccountingIssue)}


def test_unattached_allocation_cannot_unlock_an_old_consumer(reg):
    result = solve("A budget of $180. Mira has $35. How much money does Mira have?", reg)
    assert not result.answer.committed


def test_re_admitted_clothing_does_not_imply_a_count_or_subset(reg):
    result = solve("Mira has 30 clothing items. Mira bought shoes. How many shoes does Mira have?", reg)
    assert not result.answer.committed


@pytest.mark.parametrize("text", ["Mira ordered shoes.", "Mira will buy shoes.", "Mira can buy shoes."])
@pytest.mark.parametrize("project", ["curated", "gsm8k"])
def test_requests_and_future_plans_do_not_create_actual_cost_records(text, project):
    registry = load_project(Path("projects") / project).registry
    assert not list(solve(text, registry).store.by_kind(Expenditure))


@pytest.mark.parametrize("prefix", ["", "Mira has $100. "])
def test_purchase_price_never_becomes_a_currency_acquisition(reg, prefix):
    from rulekit.kernel.model import Quantity
    result = solve(prefix + "Mira bought a hat for $30. How much money does Mira have?", reg)
    assert not result.answer.committed, result.answer
    assert not any(q.verb == "buy" and q.measure == "dollar" for q in result.store.by_kind(Quantity))
