"""Decomposable-whole totals and explicitly complete quantity activities.

The examples are invented analogues.  They exercise the reusable class:
qualified counted wholes, per-whole portion rates, an explicit totality event,
and a category-scoped component ask over the same discourse interval.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import (
    BoundedActivityInquiry,
    Membership,
    Predication,
    Quantity,
    TotalityEvent,
)


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/curated")).registry


def _story(ask_period: str = "day") -> str:
    return (
        "Bira is wondering how much pizza she can eat in one day. "
        "She buys 3 large pizzas and 1 small pizza. "
        "A large pizza has 12 slices and a small pizza has 6 slices. "
        "If she eats it all, "
        f"how many pieces does she eat that {ask_period}?"
    )


def test_qualified_portioned_wholes_answer_complete_consumption(reg) -> None:
    result = solve(_story(), reg, tracing=False)

    assert result.answer.committed, result.answer.reason
    assert result.answer.value == pytest.approx(42.0)
    assert result.deficiencies() == []
    assert len(result.store.by_kind(BoundedActivityInquiry)) == 1
    assert len(result.store.by_kind(TotalityEvent)) == 1
    assert any(
        quantity.entity == "bira"
        and quantity.measure == "slice"
        and quantity.verb == "eat"
        and quantity.time == "day"
        and quantity.value == pytest.approx(42.0)
        for quantity in result.store.by_kind(Quantity)
    )


def test_same_structure_is_not_tied_to_eating(reg) -> None:
    result = solve(
        "Bira is wondering how much pizza she can add in one day. "
        "She buys 3 large pizzas and 1 small pizza. "
        "A large pizza has 12 slices and a small pizza has 6 slices. "
        "If she adds it all, how many pieces does she add that day?",
        reg,
        tracing=False,
    )

    assert result.answer.committed, result.answer.reason
    assert result.answer.value == pytest.approx(42.0)
    assert result.deficiencies() == []
    assert any(
        quantity.entity == "bira"
        and quantity.measure == "slice"
        and quantity.verb == "add"
        and quantity.time == "day"
        and quantity.value == pytest.approx(42.0)
        for quantity in result.store.by_kind(Quantity)
    )


def test_inquiry_frame_does_not_mint_membership_or_predication(reg) -> None:
    result = solve(
        "Bira is wondering how much pizza she can eat in one day.",
        reg,
        tracing=False,
    )

    assert len(result.store.by_kind(BoundedActivityInquiry)) == 1
    assert not result.store.by_kind(Membership)
    assert not result.store.by_kind(Predication)
    assert result.deficiencies() == []


def test_complete_consumption_needs_the_explicit_totality_clause(reg) -> None:
    result = solve(
        "Bira is wondering how much pizza she can eat in one day. "
        "She buys 3 large pizzas and 1 small pizza. "
        "A large pizza has 12 slices and a small pizza has 6 slices. "
        "How many pieces does she eat that day?",
        reg,
        tracing=False,
    )

    assert not result.answer.committed
    assert not result.store.by_kind(TotalityEvent)
    assert not any(
        quantity.verb == "eat"
        for quantity in result.store.by_kind(Quantity)
    )


def test_portion_event_ask_requires_the_matching_interval(reg) -> None:
    result = solve(_story("week"), reg, tracing=False)

    assert not result.answer.committed
    assert any(
        quantity.measure == "slice" and quantity.time == "day"
        for quantity in result.store.by_kind(Quantity)
    )


def test_piece_and_slice_are_not_global_synonyms(reg) -> None:
    result = solve(
        "Bira ate 5 pieces. How many slices did Bira eat?",
        reg,
        tracing=False,
    )

    assert not result.answer.committed
    assert "no 'eat' events" in result.answer.reason


def test_pizza_is_a_decomposable_whole_not_a_container(reg) -> None:
    assert reg.word_in_category("pizza", "sized_content_bearing_whole")
    assert reg.word_in_category("pizza", "decomposable_quantity_whole")
    assert not reg.word_in_category("pizza", "quantity_container")
