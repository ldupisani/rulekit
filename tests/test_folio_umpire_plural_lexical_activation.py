"""Pack-local role morphology activates positive and negative universals."""

from pathlib import Path

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantified


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCES = {"logic/universal-copular-all-are", "logic/universal-no-are"}


def _facts(text: str) -> list[Quantified]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Quantified)
        if fact.provenance.source in SOURCES
    ]


def test_plural_role_folds_in_positive_universal() -> None:
    facts = _facts("All coastal umpires are patient people.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("coastal umpire", "patient person", True),
    ]


def test_plural_role_folds_in_negative_universal() -> None:
    facts = _facts("No coastal umpires are patient people.")
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("coastal umpire", "patient person", False),
    ]


def test_signed_all_surface_does_not_masquerade_as_either_universal() -> None:
    assert _facts("All coastal umpires are not patient people.") == []


def test_disjunctive_predicate_does_not_masquerade_as_either_universal() -> None:
    assert _facts("All coastal umpires are patient people or calm people.") == []


def test_existential_quantifier_does_not_masquerade_as_universal() -> None:
    assert _facts("Some coastal umpires are patient people.") == []


def test_singular_no_surface_does_not_use_plural_agreement_reader() -> None:
    assert _facts("No coastal umpire is a patient person.") == []
