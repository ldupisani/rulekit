"""Ordered container contents observed through a measurement instrument.

All prose is synthetic.  The class is a resulting aggregate anchor followed
by multiplicative and additive content changes, applied in narration order.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.generation.ask_generation import generate_ask_scenario
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


def _paraphrased_story() -> str:
    return (
        "Mira created a care package to send to her brother, who was away at boarding school. "
        "Mira placed a jar on a scale, and then she poured into the jar enough "
        "jelly beans to bring the weight to 5 pounds. "
        "Then, she added enough brownies to cause the weight to triple. "
        "Next, she added another 4 pounds of jelly beans. "
        "And finally, she added enough gummy worms to double the weight once again. "
        "What was the final weight of the jar of goodies, in pounds?"
    )


def test_moved_goal_causative_and_repetition_keep_one_ordered_stream(registry):
    result = solve(_paraphrased_story(), registry)
    assert (result.answer.kind, result.answer.value) == ("number", 38.0)
    assert [
        (fact.content, fact.operation, fact.value)
        for fact in result.store.by_kind(MeasuredContentChange)
    ] == [
        ("jelly bean", "set_total", 5.0),
        ("brownie", "multiply_total", 3.0),
        ("jelly bean", "add_quantity", 4.0),
        ("gummy worm", "multiply_total", 2.0),
    ]
    assert not any(p.deficiencies() for p in result.premises[1:])


@pytest.mark.parametrize("ending", [
    "What is the final weight of the jar?",
    "What was the final weight of the jar in pounds?",
    "What was the final weight of the jar of contents, in pounds?",
    "What is the final weight measured on the scale?",
])
def test_container_and_instrument_asks_select_the_same_stream(registry, ending):
    text = _paraphrased_story().rsplit("What", 1)[0] + ending
    result = solve(text, registry)
    assert (result.answer.kind, result.answer.value) == ("number", 38.0)


@pytest.mark.parametrize("ending", [
    "What was the final weight of the bucket in pounds?",
    "What was the final weight of the jar in kilograms?",
    "What was the final weight of the jar in liters?",
    "What was the final weight of the jar of brownies in pounds?",
])
def test_container_ask_does_not_ignore_identity_contents_or_output_unit(registry, ending):
    text = _paraphrased_story().rsplit("What", 1)[0] + ending
    assert not solve(text, registry).answer.committed


def test_explicit_output_unit_uses_declared_mass_conversion(registry):
    text = _story().rsplit("What", 1)[0] + "What is the final weight of the box in grams?"
    assert solve(text, registry).answer.value == 14000.0


@pytest.mark.parametrize("old,new", [
    ("Mira placed a jar on a scale, and then she ", "Mira "),
    ("cause the weight to triple", "cause the weight to halve"),
    ("another 4 pounds", "another 4 liters"),
])
def test_unread_or_unanchored_updates_do_not_return_a_partial_total(registry, old, new):
    assert not solve(_paraphrased_story().replace(old, new), registry).answer.committed


@pytest.mark.parametrize("content,expected", [("clay", 10.0), ("sugar", 19.0)])
def test_causative_and_repeated_scalings_retain_content_contributions(registry, content, expected):
    text = _paraphrased_story().rsplit("What", 1)[0].replace(
        "brownies", "clay"
    ).replace("gummy worms", "sugar")
    result = solve(text + f"How much {content} is in the jar?", registry)
    assert result.answer.value == expected


def test_repeated_material_needs_tare_and_accumulates_later_additions(registry):
    text = _paraphrased_story().rsplit("What", 1)[0].replace("jelly beans", "water")
    ask = "How much water is in the jar?"
    assert not solve(text + ask, registry).answer.committed
    result = solve(text + "The jar weighs 1 pound. " + ask, registry)
    assert result.answer.value == 8.0


@pytest.mark.parametrize("rule_id", [
    "arithmetic/measured-content-resulting-total-preposed-goal",
    "arithmetic/measured-content-causative-multiply-total",
])
def test_measurement_paraphrases_generate_and_round_trip(project, rule_id):
    candidate = generate_candidate(
        project, rule_id=rule_id, seed=281,
        locked_bindings={"content": "enough jelly beans"},
    )
    assert candidate.target_status == "matched"
    assert "jelly beans" in candidate.sentence


def test_generated_container_ask_preserves_singular_dimension(project):
    candidate = generate_ask_scenario(
        project, ask_id="ask/final-container-measurement-reading", seed=281,
    )
    assert candidate.target_ask == "ask/final-container-measurement-reading"
    assert "final weight " in candidate.question
    assert "final weights" not in candidate.question
    assert match_ask(analyze(candidate.question, project.registry), project.registry)[0].id == candidate.target_ask


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
