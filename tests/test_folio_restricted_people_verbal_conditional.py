"""Reader 40: restricted ``people`` verbal-to-verbal conditionals."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Conditional


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/conditional-people-restricted-verbal-then-they-verbal"


def _facts(text: str) -> list[Conditional]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Conditional)
        if fact.provenance.source == SOURCE
    ]


def test_emits_exact_restriction_event_and_consequence() -> None:
    facts = _facts("If people at Harbor buy books, then they sell magazines.")
    assert [(f.cls, f.pred, f.then_pred, f.polarity) for f in facts] == [
        ("at harbor", "buy book", "sell magazine", True),
    ]


def test_composes_with_existing_conditional_instantiation() -> None:
    result = solve(
        "If people at Harbor buy books, then they sell magazines. "
        "Mia is at Harbor. Mia buys books. "
        "Is it true that Mia sells magazines?",
        REGISTRY,
    )
    assert result.value == "yes"


def test_composition_requires_both_antecedent_properties() -> None:
    result = solve(
        "If people at Harbor buy books, then they sell magazines. "
        "Mia is at Harbor. Is it true that Mia sells magazines?",
        REGISTRY,
    )
    assert result.value == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "If people buy books, then they sell magazines.",
        "If a person at Harbor buys books, then they sell magazines.",
        "If people at Harbor are buyers, then they sell magazines.",
        "If people at Harbor do not buy books, then they sell magazines.",
        "If people at Harbor buy books and maps, then they sell magazines.",
        "If people at Harbor buy books, they sell magazines.",
        "If people at Harbor buy books, then they do not sell magazines.",
        "If people at Harbor buy books, then they will sell magazines.",
        "If people at Harbor buy books, then they are merchants.",
        "If people at Harbor buy books, then they sell magazines and maps.",
        "If people at Harbor buy books, then they sell and trade magazines.",
        "If people at Harbor bought books, then they sell magazines.",
        "If people at Harbor buy books, then they sell two magazines.",
        "If people at Harbor buy books, then they sell magazines",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
