"""Existential witnesses propagate through exact universal predicates."""

from pathlib import Path

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


REGISTRY = load_project(Path("projects/scratch")).registry


def _value(text: str) -> str | None:
    return solve(text, REGISTRY).value


def test_positive_predicate_chain_composes() -> None:
    assert _value(
        "Some creatures are trees. Trees are plants. "
        "Is it true that some creatures are plants?"
    ) == "yes"


def test_negative_universal_consequence_composes() -> None:
    assert _value(
        "Some creatures are trees. Trees are not machines. "
        "Is it true that some creatures are not machines?"
    ) == "yes"


def test_chain_does_not_run_backward() -> None:
    assert _value(
        "Some creatures are plants. Trees are plants. "
        "Is it true that some creatures are trees?"
    ) == "undetermined"


def test_negative_existential_predicate_does_not_supply_antecedent() -> None:
    assert _value(
        "Some creatures are not trees. Trees are plants. "
        "Is it true that some creatures are plants?"
    ) == "undetermined"


def test_chain_preserves_the_original_witness_class() -> None:
    assert _value(
        "Some creatures are trees. Trees are plants. "
        "Is it true that some animals are plants?"
    ) == "undetermined"
