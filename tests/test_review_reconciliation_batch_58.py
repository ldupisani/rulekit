"""Regressions from the validated-premise ask review batch 58."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import analyze, solve
from rulekit.kernel.patterns import match_ask


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def project():
    return load_project(ROOT / "projects" / "curated")


def test_quantity_ask_does_not_bind_timeperiod_as_owned_object(project) -> None:
    question = "How many years would Bira own?"

    reading = analyze(question, project.registry)

    assert match_ask(reading, project.registry) is None
    assert solve(question, project.registry).answer.committed is False


def test_quantity_ask_still_binds_plausible_owned_count_object(project) -> None:
    question = "How many apples would Bira own?"

    matched = match_ask(analyze(question, project.registry), project.registry)

    assert matched is not None
    assert matched[0].id == "ask/how-many-entity"
    assert matched[1]["entity"] == "bira"
    assert matched[1]["measure"] == "apple"
    assert matched[1]["verb"] == "own"
