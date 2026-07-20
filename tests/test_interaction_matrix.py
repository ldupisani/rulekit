"""Pairwise construction interactions over the GSM8K project registry.

This is deliberately a small synthetic suite.  It varies four seams that are
usually tested independently -- reference form, noun qualification,
coordination, and the queried relation -- with a strength-two covering array.
The oracle is intentionally narrow: supported combinations must give the
expected number, while nearby under-specified questions must decline.  A
known capability boundary may also return that exact number or decline; it
must never produce a different confident answer.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


AXES = ("reference", "identity", "clause", "query")
AXIS_VALUES = {
    "reference": ("explicit", "pronoun"),
    "identity": ("bare", "qualified"),
    "clause": ("single", "coordinated"),
    "query": ("state", "event"),
}


@dataclass(frozen=True)
class InteractionCase:
    id: str
    profile: tuple[tuple[str, str], ...]
    text: str
    value: float
    permits_decline: bool = False

    @property
    def dimensions(self) -> dict[str, str]:
        return dict(self.profile)


# L8(2^7) projected to four columns.  Each combination of values for every
# pair of axes occurs at least once, while every case remains a short,
# unambiguous problem that exercises the real readers and consumers.
CASES = (
    InteractionCase(
        "explicit-bare-single-state",
        (("reference", "explicit"), ("identity", "bare"), ("clause", "single"), ("query", "state")),
        "Ana has 5 apples. How many apples does Ana have?",
        5.0,
    ),
    InteractionCase(
        "explicit-bare-coordinated-event",
        (("reference", "explicit"), ("identity", "bare"), ("clause", "coordinated"), ("query", "event")),
        "Ana found 5 apples and 3 oranges. How many apples did Ana find?",
        5.0,
    ),
    InteractionCase(
        "explicit-qualified-single-event",
        (("reference", "explicit"), ("identity", "qualified"), ("clause", "single"), ("query", "event")),
        "Ana found 5 red apples. How many apples did Ana find?",
        5.0,
    ),
    InteractionCase(
        "explicit-qualified-coordinated-state",
        (("reference", "explicit"), ("identity", "qualified"), ("clause", "coordinated"), ("query", "state")),
        "Ana has 5 red apples and 3 green apples. How many apples does Ana have?",
        8.0,
    ),
    InteractionCase(
        "pronoun-bare-single-event",
        (("reference", "pronoun"), ("identity", "bare"), ("clause", "single"), ("query", "event")),
        "Ana found 5 apples. How many apples did she find?",
        5.0,
    ),
    InteractionCase(
        "pronoun-bare-coordinated-state",
        (("reference", "pronoun"), ("identity", "bare"), ("clause", "coordinated"), ("query", "state")),
        "Ana has 5 apples and 3 oranges. How many apples does she have?",
        5.0,
    ),
    InteractionCase(
        "pronoun-qualified-single-state",
        (("reference", "pronoun"), ("identity", "qualified"), ("clause", "single"), ("query", "state")),
        "Ana has 5 red apples. How many apples does she have?",
        5.0,
    ),
    # Qualified sibling events have no explicitly stated event total.  Today
    # the event consumer declines; a later general account may return 8.
    InteractionCase(
        "pronoun-qualified-coordinated-event",
        (("reference", "pronoun"), ("identity", "qualified"), ("clause", "coordinated"), ("query", "event")),
        "Ana found 5 red apples and 3 green apples. How many apples did she find?",
        8.0,
        permits_decline=True,
    ),
)


@dataclass(frozen=True)
class DeclineCase:
    id: str
    text: str


# These are the unsafe neighbours of two supported cells above.  A numerical
# answer would invent a total from facts that do not establish the asked-for
# state or event.
DECLINE_CASES = (
    DeclineCase(
        "do-not-turn-qualified-parts-and-an-event-into-a-bare-state",
        "Ana had 5 blue bears and 3 green bears. Ana picked 4 bears. How many bears are left?",
    ),
    DeclineCase(
        "do-not-turn-a-state-into-an-event",
        "Ana has 5 apples. How many apples did Ana find?",
    ),
)


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/gsm8k")).registry


def _required_pairs() -> set[tuple[str, str, str, str]]:
    return {
        (left_axis, left_value, right_axis, right_value)
        for left_axis, right_axis in combinations(AXES, 2)
        for left_value in AXIS_VALUES[left_axis]
        for right_value in AXIS_VALUES[right_axis]
    }


def _observed_pairs() -> set[tuple[str, str, str, str]]:
    return {
        (left_axis, dimensions[left_axis], right_axis, dimensions[right_axis])
        for case in CASES
        for dimensions in (case.dimensions,)
        for left_axis, right_axis in combinations(AXES, 2)
    }


def test_pairwise_matrix_covers_each_declared_interaction() -> None:
    assert all(set(case.dimensions) == set(AXES) for case in CASES)
    assert _observed_pairs() == _required_pairs()


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_pairwise_interactions_honor_their_safety_contract(reg, case: InteractionCase) -> None:
    result = solve(case.text, reg)

    expected_kinds = {"number", "decline"} if case.permits_decline else {"number"}
    assert result.answer.kind in expected_kinds
    if result.answer.kind == "number":
        assert result.answer.value == pytest.approx(case.value)
    else:
        assert result.answer.value is None
    assert not result.store.collisions


@pytest.mark.parametrize("case", DECLINE_CASES, ids=lambda case: case.id)
def test_pairwise_safety_neighbours_decline(reg, case: DeclineCase) -> None:
    result = solve(case.text, reg)

    assert result.answer.kind == "decline"
