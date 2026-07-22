"""Phase B reader 57: restricted someone-generic copular conditionals."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Conditional


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCES = {
    "logic/conditional-someone-restricted-is-then-they-are",
    "logic/conditional-someone-restricted-is-then-they-are-not",
}


def _facts(text: str) -> list[Conditional]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Conditional)
        if fact.provenance.source in SOURCES
    ]


@pytest.mark.parametrize(
    ("surface", "polarity"),
    [
        ("If someone in Riverton is patient, then they are welcome.", True),
        ("If someone in Riverton is patient, then they are not noisy.", False),
    ],
)
def test_emits_both_required_antecedents(surface: str, polarity: bool) -> None:
    facts = _facts(surface)
    assert [(f.cls, f.pred, f.then_pred, f.polarity) for f in facts] == [
        ("in riverton", "patient", "welcome" if polarity else "noisy", polarity),
    ]


def test_existing_two_antecedent_instantiation_path_applies() -> None:
    result = solve(
        "If someone in Riverton is patient, then they are welcome. "
        "Ari is in Riverton. Ari is patient. Is it true that Ari is welcome?",
        REGISTRY,
    )
    assert result.value == "yes"


@pytest.mark.parametrize(
    "surface",
    [
        "If someone is patient, then they are welcome.",
        "If someone in Riverton is not patient, then they are welcome.",
        "If someone in Riverton is patient or calm, then they are welcome.",
        "If someone in Riverton is patient, then she is welcome.",
        "If someone in Riverton is patient, then they work nearby.",
        "If someone in Riverton can be patient, then they are welcome.",
        "If someone in Riverton is patient, then they can be welcome.",
        "If someone in Riverton is patient, then they are welcome or calm.",
        "If someone in Riverton and Lakeside is patient, then they are welcome.",
        "If someone in Riverton is patient, they are welcome.",
        "If someone in Riverton is patient, then they are welcome",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
