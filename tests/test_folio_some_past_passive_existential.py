"""Reader 49: restricted past-passive verbal existentials."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Existential


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/existential-some-past-passive"


def _facts(text: str) -> list[Existential]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Existential)
        if fact.provenance.source == SOURCE
    ]


def test_preserves_restricted_class_and_complete_passive_property() -> None:
    facts = _facts("Some clubs near lakes were established in 1998.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("club near lake", "establish in 1998", True),
    ]


def test_exact_question_twin_composes() -> None:
    result = solve(
        "Some clubs near lakes were established in 1998. "
        "Is it true that some clubs near lakes were established in 1998?",
        REGISTRY,
    )
    assert result.value == "yes"


def test_changed_restriction_remains_undetermined() -> None:
    result = solve(
        "Some clubs near lakes were established in 1998. "
        "Is it true that some clubs near rivers were established in 1998?",
        REGISTRY,
    )
    assert result.value == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "A club near lakes was established in 1998.",
        "Some club near lakes was established in 1998.",
        "Some clubs near lakes are established in 1998.",
        "Some clubs near lakes established venues in 1998.",
        "Some clubs near lakes were not established in 1998.",
        "Some clubs near lakes will be established in 1998.",
        "Some clubs near lakes were either established or closed.",
        "Some clubs and societies were established in 1998.",
        "Some two clubs were established in 1998.",
        "Some clubs near lakes were establish in 1998.",
        "Some clubs near lakes were established.",
        "Some clubs near lakes were established in 1998 and expanded later.",
        "Some clubs near lakes were established in 1998",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
