"""Existing compound-rate evidence already supports inverse time-unit asks."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Rate


@pytest.mark.parametrize("project", ["curated", "gsm8k"])
@pytest.mark.parametrize("pages,minutes,target,hours", [(6, 15, 96, 4), (9, 18, 135, 4.5)])
def test_compound_reading_rate_converts_inverse_duration(project, pages, minutes, target, hours):
    reg = load_project(Path("projects") / project).registry
    result = solve(f"Dena can read {pages} pages of a book in {minutes} minutes. "
                   f"How many hours will it take her to read {target} pages?", reg)
    assert result.answer.value == hours, result.answer
    rates = result.store.by_kind(Rate)
    assert len(rates) == 1
    assert (rates[0].numerator, rates[0].denominator) == (pages, minutes)
