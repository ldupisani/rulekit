"""Imperative asks for one named holder's declared dimension.

These are synthetic contract examples.  A dimension noun such as ``age``
selects a compatible concrete measure from that holder's facts, then reuses
the ordinary single-entity fold.  Resolution is holder-scoped so an unrelated
dimension measure elsewhere in the passage cannot make the ask ambiguous.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.patterns import match_ask


@pytest.fixture(scope="module")
def registry():
    return load_project(Path("projects/gsm8k")).registry


def _solve_with_ask(text: str, registry):
    result = solve(text, registry, tracing=False)
    matched = match_ask(result.question, registry) if result.question else None
    return result, matched[0].id if matched else None


@pytest.mark.parametrize("cue", ["Calculate", "Compute", "Determine"])
def test_imperative_age_ask_reuses_the_single_entity_fold(
    cue: str, registry
) -> None:
    result, ask_id = _solve_with_ask(
        "Arden is 3 years older than Briar. Briar is 20 years old. "
        f"{cue} the age of Arden.",
        registry,
    )

    assert ask_id == "ask/imperative-single-dimension"
    assert result.answer.value == 23


def test_dimension_resolution_is_scoped_to_the_asked_holder(registry) -> None:
    result, ask_id = _solve_with_ask(
        "Arden is 21 years old. Briar has 4 days. "
        "Calculate the age of Arden.",
        registry,
    )

    assert ask_id == "ask/imperative-single-dimension"
    assert result.answer.value == 21


@pytest.mark.parametrize(
    ("premise", "dimension", "expected"),
    [
        ("Arden is 64 inches tall.", "height", 64),
        ("Arden is 90 pounds.", "weight", 90),
        ("Arden has 12 dollars.", "balance", 12),
    ],
)
def test_single_dimension_ask_is_generic_over_declared_dimension_nouns(
    premise: str, dimension: str, expected: int, registry
) -> None:
    result, ask_id = _solve_with_ask(
        f"{premise} Calculate the {dimension} of Arden.", registry
    )

    assert ask_id == "ask/imperative-single-dimension"
    assert result.answer.value == expected


def test_an_unstated_dimension_declines_instead_of_borrowing_another(
    registry,
) -> None:
    result, ask_id = _solve_with_ask(
        "Arden is 21 years old. Briar has 9 pounds. "
        "Calculate the weight of Arden.",
        registry,
    )

    assert ask_id == "ask/imperative-single-dimension"
    assert not result.answer.committed


@pytest.mark.parametrize(
    "question",
    [
        "Calculate the age.",
        "Calculate their combined age.",
        "Calculate the average age of the two.",
    ],
)
def test_single_dimension_ask_does_not_claim_incomplete_or_aggregate_forms(
    question: str, registry
) -> None:
    result, ask_id = _solve_with_ask(
        "Arden is 21 years old. Briar is 19 years old. " + question,
        registry,
    )

    assert ask_id != "ask/imperative-single-dimension"
    assert result.answer.value != 21


def test_coordinated_holder_tail_declines_instead_of_answering_a_prefix(
    registry,
) -> None:
    result, ask_id = _solve_with_ask(
        "Arden is 21 years old. Briar is 19 years old. "
        "Calculate the age of Arden and Briar.",
        registry,
    )

    assert ask_id == "ask/imperative-single-dimension"
    assert not result.answer.committed
    assert "exactly one entity" in result.answer.reason
