"""Reader 50: modal-passive verbal existentials preserve possibility."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Existential


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/existential-some-modal-passive"


def _facts(text: str) -> list[Existential]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Existential)
        if fact.provenance.source == SOURCE
    ]


def test_preserves_modal_and_complete_passive_property() -> None:
    facts = _facts("Some cards can be used near gates.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("card", "can be use near gates", True),
    ]


def test_exact_question_twin_composes() -> None:
    result = solve(
        "Some cards can be used near gates. "
        "Is it true that some cards can be used near gates?",
        REGISTRY,
    )
    assert result.value == "yes"


def test_modal_fact_does_not_assert_actual_use() -> None:
    result = solve(
        "Some cards can be used near gates. "
        "Is it true that some cards are used near gates?",
        REGISTRY,
    )
    assert result.value == "undetermined"


def test_changed_property_remains_undetermined() -> None:
    result = solve(
        "Some cards can be used near gates. "
        "Is it true that some cards can be used near homes?",
        REGISTRY,
    )
    assert result.value == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "A card can be used near gates.",
        "Some card can be used near gates.",
        "Some durable payment cards can be used near gates.",
        "Some cards are used near gates.",
        "Some cards will be used near gates.",
        "Some cards cannot be used near gates.",
        "Some cards can not be used near gates.",
        "Some cards can use gates.",
        "Some cards can be use near gates.",
        "Some cards and passes can be used near gates.",
        "Some two cards can be used near gates.",
        "Some cards can be used.",
        "Some cards can be used near gates and homes.",
        "Some cards can be used near gates",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
