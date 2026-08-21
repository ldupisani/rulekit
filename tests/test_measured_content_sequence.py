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
    return load_project(Path("projects/curated"))


@pytest.fixture(scope="module")
def registry(project):
    return project.registry


def _story(*, include_placement: bool = True, added_unit: str = "kilograms") -> str:
    placement = "She placed a box on a scale, and " if include_placement else "She "
    return (
        "Mira is conducting an experiment. "
        f"{placement}poured enough water into the box to bring the weight to 4 kg. "
        "Then she added enough clay to triple the weight. "
        f"Finally, she added 2 {added_unit} of sugar. "
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
        ("box", "water", "set_total", 4.0, "weight", "kilogram", 1),
        (
            "$active:measured-container$",
            "clay",
            "multiply_total",
            3.0,
            "weight",
            None,
            2,
        ),
        (
            "$active:measured-container$",
            "sugar",
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
        ("box", "water", "set_total", 1),
        ("box", "clay", "multiply_total", 2),
        ("box", "sugar", "add_quantity", 3),
    ]


def test_put_is_a_measured_content_transfer_paraphrase(registry) -> None:
    result = solve(_story().replace("poured enough", "put enough"), registry)

    assert (result.answer.kind, result.answer.value) == ("number", 14.0)
    assert any(
        fact.operation == "set_total"
        and fact.container == "box"
        and fact.content == "water"
        for fact in result.store.by_kind(MeasuredContentChange)
    )


def test_clause_medial_sequence_marker_preserves_the_update(registry) -> None:
    result = solve(
        _story().replace("Finally, she added", "She then added"), registry
    )

    assert (result.answer.kind, result.answer.value) == ("number", 14.0)
    assert any(
        fact.operation == "add_quantity"
        and fact.content == "sugar"
        and fact.value == 2
        for fact in result.store.by_kind(MeasuredContentChange)
    )


@pytest.mark.parametrize(
    "container",
    [
        "barrel",
        "beaker",
        "bottle",
        "bowl",
        "bucket",
        "canister",
        "container",
        "drum",
        "flask",
        "jar",
        "jug",
        "tank",
        "vessel",
        "vial",
    ],
)
def test_declared_measurement_containers_share_the_same_rules(
    registry, container
) -> None:
    result = solve(_story().replace("box", container), registry)

    assert (result.answer.kind, result.answer.value) == ("number", 14.0)
    assert any(
        fact.entity == container and fact.reference == "scale"
        for fact in result.store.by_kind(SpatialPlacement)
    )


def test_resulting_total_is_not_misattributed_to_content_or_instrument(registry) -> None:
    result = solve(_story(), registry)
    quantities = result.store.by_kind(Quantity)

    assert not any(
        fact.entity in {"water", "clay", "sugar", "scale"}
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
        "to bring the weight to 5 kilograms. Mira poured enough water into a box "
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


def _content_amount_story(*, tare: str = "500 grams", content: str = "water") -> str:
    return (
        "Rina placed a box on a scale, and poured enough water into the box "
        "to bring the weight to 4 kilograms. Rina added enough clay to double "
        "the weight. Rina added 2 kilograms of sugar. "
        f"If the box weighs {tare}, how much {content} is in the box?"
    )


def test_initial_content_amount_subtracts_the_container_tare(registry) -> None:
    result = solve(_content_amount_story(), registry)

    assert (result.answer.kind, result.answer.value) == ("number", 3.5)
    assert result.answer.reason == (
        "'water' in 'box': 4 kilogram − 0.5 kilogram"
    )
    assert any(
        fact.entity == "box"
        and fact.measure == "gram"
        and fact.value == 500
        and fact.verb == "weigh"
        for fact in result.store.by_kind(Quantity)
    )


def test_multiplicative_content_is_the_change_in_the_aggregate(registry) -> None:
    result = solve(_content_amount_story(content="clay"), registry)

    assert (result.answer.kind, result.answer.value) == ("number", 4.0)
    assert result.answer.reason == (
        "'clay' in 'box': 8 kilogram − 4 kilogram"
    )


def test_directly_added_content_preserves_its_stated_amount(registry) -> None:
    result = solve(_content_amount_story(content="sugar"), registry)

    assert (result.answer.kind, result.answer.value) == ("number", 2.0)
    assert result.answer.reason == "'sugar' in 'box': + 2 kilogram"


def test_later_content_does_not_need_the_container_tare(registry) -> None:
    result = solve(
        _content_amount_story(content="clay").replace(
            "If the box weighs 500 grams, ", ""
        ),
        registry,
    )

    assert (result.answer.kind, result.answer.value) == ("number", 4.0)


@pytest.mark.parametrize("surface", ["liters", "litres"])
def test_content_amount_uses_a_substance_scoped_volume_conversion(
    registry, surface
) -> None:
    result = solve(
        _content_amount_story().replace(
            "how much water is", f"how many {surface} of water are"
        ),
        registry,
    )

    assert (result.answer.kind, result.answer.value) == ("number", 3.5)
    assert result.answer.reason.endswith("3.5 kilogram → 3.5 liter")


def test_substance_conversion_can_follow_an_ordinary_unit_conversion(registry) -> None:
    result = solve(
        _content_amount_story()
        .replace("4 kilograms", "4000 grams")
        .replace("how much water is", "how many litres of water are"),
        registry,
    )

    assert (result.answer.kind, result.answer.value) == ("number", 3.5)
    assert result.answer.reason.endswith("3500 gram → 3.5 liter")


def test_water_density_does_not_convert_an_unrelated_substance(registry) -> None:
    result = solve(
        _content_amount_story(content="clay").replace(
            "how much clay is", "how many litres of clay are"
        ),
        registry,
    )

    assert not result.answer.committed
    assert "no known 'clay' conversion" in result.answer.reason
    assert ("kilogram", "liter") not in registry.conversions
    assert registry.substance_conversions[("water", "kilogram", "liter")] == 1


def test_container_mass_needs_a_declared_conversion_to_the_anchor_unit(registry) -> None:
    result = solve(_content_amount_story(tare="2 pounds"), registry)

    assert not result.answer.committed
    assert "no known conversion" in result.answer.reason


def test_misspelled_mass_verb_does_not_create_a_tare_fact(registry) -> None:
    result = solve(
        _content_amount_story().replace("box weighs", "box weights"),
        registry,
    )

    assert not result.answer.committed
    assert not any(
        fact.entity == "box" and fact.measure == "gram"
        for fact in result.store.by_kind(Quantity)
    )
