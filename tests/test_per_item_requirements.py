"""One resource requirement across a counted population with one exception."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import BatchEvidence


@pytest.fixture(scope="module")
def registry():
    return load_project(Path("projects/curated")).registry


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "Nora has 12 parcels. Each parcel needs two labels except one parcel, "
            "which needs four. How many labels does Nora need?",
            26,
        ),
        (
            "Nora has twelve parcels. Every parcel requires two labels except for one, "
            "which requires four labels. How many labels are required in total?",
            26,
        ),
        (
            "There are 12 parcels. All parcels need two labels except one parcel, "
            "which needs four. How many labels are needed?",
            26,
        ),
        (
            "Nora has 12 parcels. How many labels does she need if everything "
            "needs 2 labels except one parcel, which needs 4?",
            26,
        ),
        (
            "Nora has eleven small parcels and one large parcel. Each parcel needs "
            "2 labels except the large parcel, which needs 4. How many labels does Nora need in total?",
            26,
        ),
        (
            "Nora has ten small parcels and two large parcels. Each parcel needs "
            "2 labels except one large parcel, which needs 4. How many labels does Nora need?",
            26,
        ),
        (
            "Nora has 6 bicycles. Each bicycle needs 2 wheels except one, which needs "
            "1 wheel. How many wheels does Nora need?",
            11,
        ),
        (
            "There are 13 small boxes and one large box. Each box needs 2 stickers "
            "except the large box, which needs 4. How many stickers are needed?",
            30,
        ),
    ],
)
def test_counted_items_use_one_overridden_requirement(registry, text, expected):
    result = solve(text, registry)
    assert result.answer.value == expected, result.answer
    assert not result.deficiencies()
    assert not result.answer.assumptions
    assert [
        fact.kind for fact in result.store.by_kind(BatchEvidence)
    ] == ["unit-plan-item-exception"]


@pytest.mark.parametrize(
    "opening, exception",
    [
        ("Nora has 12 parcels.", "the parcel"),
        ("Nora has one small parcel and one large parcel.", "the parcel"),
        ("Nora has 12 parcels.", "the large parcel"),
        ("Nora has 10 small parcels and 2 large parcels.", "the large parcel"),
        ("Nora has 12 small parcels.", "one large parcel"),
        ("Nora has 12 parcels.", "one box"),
        ("Nora has 12 parcels.", "two parcels"),
        ("Nora has 0 parcels.", "one parcel"),
    ],
)
def test_exception_must_account_for_one_item_in_the_population(registry, opening, exception):
    result = solve(
        f"{opening} Each parcel needs 2 labels except {exception}, which needs 4. "
        "How many labels does Nora need?",
        registry,
    )
    assert not result.answer.committed, result.answer


@pytest.mark.parametrize(
    "text",
    [
        "Nora has 12 parcels. Iris has 7 parcels. Each parcel needs 2 labels except one, "
        "which needs 4. How many labels does Nora need?",
        "Nora has 12 parcels and 5 boxes. Each parcel needs 2 labels except one, "
        "which needs 4. How many labels does Nora need?",
        "Nora has 12 parcels. Each parcel needs 2 labels except one, "
        "which needs 4 stamps. How many labels does Nora need?",
        "Nora has 12 parcels. Each parcel needs 2 labels except one, which needs 4. "
        "Every parcel needs 3 labels except one, which needs 6. How many labels does Nora need?",
    ],
)
def test_resource_plan_declines_ambiguous_scope_or_requirements(registry, text):
    result = solve(text, registry)
    assert not result.answer.committed, result.answer


def test_separate_bill_payments_supply_distinct_items_for_the_same_solver(registry):
    result = solve(
        "Nora has to pay the gas bill and the water bill separately. "
        "How many stamps does Nora need if everything needs 1 stamp "
        "except the gas bill, which needs 3?",
        registry,
    )
    assert result.answer.value == 4, result.answer
    assert not result.deficiencies()
    facts = result.store.by_kind(BatchEvidence)
    assert [fact.provenance.source for fact in facts].count(
        "arithmetic/separately-required-documents"
    ) == 2
    assert any(fact.kind == "unit-plan-item-exception" for fact in facts)
