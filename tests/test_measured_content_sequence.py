"""Ordered container contents observed through a measurement instrument.

All prose is synthetic.  The class is a resulting aggregate anchor followed
by multiplicative and additive content changes, applied in narration order.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import analyze, solve
from rulekit.kernel.model import (
    ContainerContent,
    MeasuredContentChange,
    Quantity,
    SpatialPlacement,
)
from rulekit.kernel.patterns import match_ask


@pytest.fixture(scope="module")
def project():
    return load_project(Path("projects/gsm8k"))


@pytest.fixture(scope="module")
def registry(project):
    return project.registry


def _story(*, include_placement: bool = True, added_unit: str = "kilograms") -> str:
    placement = "She placed a box on a scale, and " if include_placement else "She "
    return (
        "Mira is conducting an experiment. "
        f"{placement}poured enough milk into the box to bring the weight to 4 kg. "
        "Then she added enough sand to triple the weight. "
        f"Finally, she added 2 {added_unit} of flour. "
        "What is the final weight measured on the scale?"
    )


def test_ordered_content_changes_derive_the_final_instrument_reading(registry) -> None:
    result = solve(_story(), registry)

    assert (result.answer.kind, result.answer.value) == ("number", 14.0)
    assert [
        (fact.entity, fact.reference, fact.relation, fact.occurrence)
        for fact in result.store.by_kind(SpatialPlacement)
    ] == [("box", "scale", "on", 1)]
    assert [
        (
            fact.container,
            fact.content,
            fact.operation,
            fact.value,
            fact.dimension,
            fact.measure,
            fact.occurrence,
        )
        for fact in result.store.by_kind(MeasuredContentChange)
    ] == [
        ("box", "milk", "set_total", 4.0, "weight", "kilogram", 1),
        (
            "$active:measured-container$",
            "sand",
            "multiply_total",
            3.0,
            "weight",
            None,
            2,
        ),
        (
            "$active:measured-container$",
            "flour",
            "add_quantity",
            2.0,
            None,
            "kilogram",
            3,
        ),
    ]
    assert [
        (fact.container, fact.content, fact.operation, fact.occurrence)
        for fact in result.store.by_kind(ContainerContent)
    ] == [
        ("box", "milk", "set_total", 1),
        ("box", "sand", "multiply_total", 2),
        ("box", "flour", "add_quantity", 3),
    ]


def test_resulting_total_is_not_misattributed_to_content_or_instrument(registry) -> None:
    result = solve(_story(), registry)
    quantities = result.store.by_kind(Quantity)

    assert not any(
        fact.entity in {"milk", "sand", "flour", "scale"}
        for fact in quantities
    )
    assert not any(
        fact.measure == "kilogram" and fact.value in {2.0, 4.0}
        for fact in quantities
    )


def test_final_reading_requires_the_container_instrument_placement(registry) -> None:
    result = solve(_story(include_placement=False), registry)

    assert not result.answer.committed
    assert "placement" in result.answer.reason


def test_incompatible_added_dimension_declines_instead_of_being_ignored(registry) -> None:
    result = solve(_story(added_unit="liters"), registry)

    assert not result.answer.committed
    assert "outside the measured-content stream" in result.answer.reason


def test_unread_numeric_clause_cannot_be_dropped_from_the_final_reading(registry) -> None:
    result = solve(
        "Nia placed a bucket on a scale, and poured enough water into the bucket "
        "to bring the weight to 5 kilograms. Nia added enough clay to double "
        "the weight. Nia found 3 coins. "
        "What is the final weight measured on the scale?",
        registry,
    )

    assert not result.answer.committed
    assert "outside the measured-content stream" in result.answer.reason


def test_narration_order_is_multiply_then_add_not_add_then_multiply(registry) -> None:
    result = solve(
        "Nia placed a bucket on a scale, and poured enough water into the bucket "
        "to bring the weight to 5 kilograms. Nia added enough clay to double "
        "the weight. Nia added 3 kilograms of sugar. "
        "What is the final weight measured on the scale?",
        registry,
    )

    assert (result.answer.kind, result.answer.value) == ("number", 13.0)


def test_two_prior_measurement_streams_make_an_elided_update_ambiguous(registry) -> None:
    result = solve(
        "Nia placed a bucket on a scale, and poured enough water into the bucket "
        "to bring the weight to 5 kilograms. Mira poured enough milk into a box "
        "to bring the weight to 4 kilograms. Nia added enough clay to double "
        "the weight. What is the final weight measured on the scale?",
        registry,
    )

    assert not result.answer.committed
    assert "unique prior stream" in result.answer.reason


def test_specific_measurement_ask_outranks_the_generic_physics_prefix(registry) -> None:
    question = analyze(
        "What is the final weight measured on the scale?", registry
    )
    matched = match_ask(question, registry)

    assert matched is not None
    assert matched[0].id == "ask/final-instrument-measurement-reading"
    assert matched[1]["consumer"] == "measurement-reading"
