"""Existing existential witnesses lift through positive superclass edges."""

from pathlib import Path

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


REGISTRY = load_project(Path("projects/scratch")).registry


def _value(text: str) -> str | None:
    return solve(text, REGISTRY).value


def test_positive_witness_property_survives_class_lift() -> None:
    assert _value(
        "Some cats are playful. Cats are mammals. "
        "Is it true that some mammals are playful?"
    ) == "yes"


def test_negative_witness_property_survives_class_lift() -> None:
    assert _value(
        "Some cats are not pets. Cats are mammals. "
        "Is it true that some mammals are not pets?"
    ) == "yes"


def test_negative_universal_does_not_supply_superclass_membership() -> None:
    assert _value(
        "Some cats are playful. Cats are not mammals. "
        "Is it true that some mammals are playful?"
    ) == "undetermined"


def test_lift_does_not_run_downward() -> None:
    assert _value(
        "Some mammals are playful. Cats are mammals. "
        "Is it true that some cats are playful?"
    ) == "undetermined"


def test_lift_preserves_the_original_property() -> None:
    assert _value(
        "Some cats are playful. Cats are mammals. "
        "Is it true that some mammals are quiet?"
    ) == "undetermined"
