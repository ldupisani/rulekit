"""Bare relative periods stay adjuncts instead of becoming compound heads."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantity


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def project():
    return load_project(ROOT / "projects" / "gsm8k")


def test_trailing_relative_period_does_not_replace_object_measure(project) -> None:
    result = solve(
        "Aven bought 4 cars last month. How many cars did Aven buy?",
        project.registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == 4
    assert [
        (quantity.entity, quantity.measure, quantity.value, quantity.time)
        for quantity in result.store.by_kind(Quantity)
    ] == [("aven", "car", 4.0, "last month")]
