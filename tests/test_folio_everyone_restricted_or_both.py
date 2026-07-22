"""Phase B reader 62: restricted everyone inclusive disjunctions."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import QuantifiedDisjunction


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/qdisj-everyone-restricted-or-they-or-both"


def _facts(text: str) -> list[QuantifiedDisjunction]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(
            QuantifiedDisjunction
        )
        if fact.provenance.source == SOURCE
    ]


def test_emits_restricted_inclusive_disjunction() -> None:
    facts = _facts(
        "Everyone in Lakeside is patient, or they are calm, or both."
    )
    assert [(f.cls, f.left, f.right, f.exclusive) for f in facts] == [
        ("in lakeside", "patient", "calm", False),
    ]


def test_union_alone_asserts_neither_branch() -> None:
    result = solve(
        "Everyone in Lakeside is patient, or they are calm, or both. "
        "Ari is in Lakeside. Is it true that Ari is patient?",
        REGISTRY,
    )
    assert result.value == "undetermined"


@pytest.mark.parametrize(
    "surface",
    [
        "Everyone is patient, or they are calm, or both.",
        "Everyone in Lakeside is either patient or calm.",
        "Everyone in Lakeside is patient or calm.",
        "Everyone in Lakeside is patient, or they are calm.",
        "Everyone in Lakeside is not patient, or they are calm, or both.",
        "Everyone in Lakeside is patient, or she is calm, or both.",
        "Everyone in Lakeside can be patient, or they are calm, or both.",
        "Everyone in Lakeside is patient and quiet, or they are calm, or both.",
        "Everyone in Lakeside is patient, or they are calm and quiet, or both.",
        "Everyone in Lakeside is patient, or they are calm, or neither.",
        "Everyone in Lakeside is patient, or they are calm, or both",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
