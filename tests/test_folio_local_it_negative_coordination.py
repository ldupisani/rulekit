"""Phase B reader 53: comma-bound local ``and it`` coordination."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Atom


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/ground-copular-local-it-negative"


def _facts(text: str) -> list[Atom]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Atom)
        if fact.provenance.source == SOURCE
    ]


def test_emits_positive_class_and_exact_negative_property() -> None:
    facts = _facts(
        "Nova is a mobile application, and it is not suitable for children."
    )
    assert [(f.entity, f.pred, f.polarity) for f in facts] == [
        ("nova", "mobile application", True),
        ("nova", "suitable for child", False),
    ]


def test_both_emitted_facts_compose_with_exact_questions() -> None:
    result = solve(
        "Nova is a mobile application, and it is not suitable for children. "
        "Is it true that Nova is suitable for children?",
        REGISTRY,
    )
    assert result.value == "no"


@pytest.mark.parametrize(
    "surface",
    [
        "A nova is a mobile application, and it is not suitable for children.",
        "Nova is mobile application, and it is not suitable for children.",
        "Nova is a mobile application and it is not suitable for children.",
        "Nova is a mobile application, but it is not suitable for children.",
        "Nova is a mobile application, and she is not suitable for children.",
        "Nova is a mobile application, and it is suitable for children.",
        "Nova can be a mobile application, and it is not suitable for children.",
        "Nova is used by artists, and it is not suitable for children.",
        "Nova is a mobile application, and it is not suitable for children and adults.",
        "Nova is a mobile application, and it is not suitable for children",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
