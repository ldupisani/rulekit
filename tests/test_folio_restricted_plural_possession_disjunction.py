"""Reader 44: restricted plural-generic possession disjunctions."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Disjunction, QuantifiedDisjunction


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/qdisj-bare-plural-appositive-have-either"


def _facts(text: str) -> list[QuantifiedDisjunction]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(
            QuantifiedDisjunction
        )
        if fact.provenance.source == SOURCE
    ]


def test_emits_the_exact_restricted_possession_disjunction() -> None:
    facts = _facts(
        "Teachers near Harbor, evening staff have either a velvet badge or a satin flower."
    )
    assert [
        (fact.cls, fact.left, fact.right, fact.exclusive) for fact in facts
    ] == [
        (
            "teacher near harbor evening staff",
            "have velvet badge",
            "have satin flower",
            True,
        ),
    ]


def test_composes_with_membership_by_disjunction_instantiation() -> None:
    result = solve(
        "Teachers near Harbor, evening staff have either a velvet badge or a satin flower. "
        "Mia is a teacher near Harbor evening staff.",
        REGISTRY,
    )
    assert [
        (fact.entity, fact.left, fact.right, fact.exclusive)
        for fact in result.store.by_kind(Disjunction)
    ] == [("mia", "have velvet badge", "have satin flower", True)]


def test_composition_requires_the_exact_restriction() -> None:
    result = solve(
        "Teachers near Harbor, evening staff have either a velvet badge or a satin flower. "
        "Mia is a teacher near Station evening staff.",
        REGISTRY,
    )
    assert list(result.store.by_kind(Disjunction)) == []


@pytest.mark.parametrize(
    "surface",
    [
        "Teachers near Harbor have either a velvet badge or a satin flower.",
        "Teachers near Harbor, have either a velvet badge or a satin flower.",
        "Every teacher near Harbor, evening staff has either a velvet badge or a satin flower.",
        "Teachers near Harbor, evening staff do not have either a velvet badge or a satin flower.",
        "Teachers near Harbor, evening staff will have either a velvet badge or a satin flower.",
        "Teachers near Harbor, evening staff have a velvet badge or a satin flower.",
        "Teachers near Harbor, evening staff have either red badges or blue seals.",
        "Teachers near Harbor, evening staff have either a velvet badge and pin or a satin flower.",
        "Teachers near Harbor, evening staff have either a velvet badge or a satin flower or a pin.",
        "Teachers near Harbor, evening staff have either no velvet badge or a satin flower.",
        "Teachers near Harbor, evening staff have either two red badges or a satin flower.",
        "Teachers near Harbor, evening staff have either a velvet badge or two blue seals.",
        "Teachers near Harbor, evening staff have either a velvet badge sings or a satin flower.",
        "Teachers near Harbor, staff who glow have either a velvet badge or a satin flower.",
        "Teachers near Harbor and Station, evening staff have either a velvet badge or a satin flower.",
        "Teachers near Harbor, evening staff have either a velvet badge or a satin flower",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
