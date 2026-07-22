"""Pack-scoped morphology activates the existing verbal existential reader."""

from pathlib import Path

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Existential


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/existential-some-verbal"


def _facts(text: str) -> list[Existential]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Existential)
        if fact.provenance.source == SOURCE
    ]


def test_registered_plural_class_and_bare_verb_reach_existing_reader() -> None:
    facts = _facts("Some acts prevent accidents.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("act", "prevent accident", True),
    ]


def test_existing_question_twin_composes() -> None:
    result = solve(
        "Some acts prevent accidents. Is it true that some acts prevent accidents?",
        REGISTRY,
    )
    assert result.value == "yes"


def test_changed_object_remains_undetermined() -> None:
    result = solve(
        "Some acts prevent accidents. Is it true that some acts prevent delays?",
        REGISTRY,
    )
    assert result.value == "undetermined"


def test_singular_subject_does_not_reach_plural_agreement_reader() -> None:
    assert _facts("Some act prevents accidents.") == []
