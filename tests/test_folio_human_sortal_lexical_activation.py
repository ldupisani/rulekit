"""Pack-local sortal morphology activates existing logic constructions."""

from pathlib import Path

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Disjunction, Quantified


REGISTRY = load_project(Path("projects/scratch")).registry


def test_plural_sortal_folds_in_copular_universal() -> None:
    facts = [
        f
        for f in solve("All humans are patient people.", REGISTRY, tracing=False).store.by_kind(Quantified)
        if f.provenance.source == "logic/universal-copular-all-are"
    ]
    assert [(f.cls, f.pred, f.polarity) for f in facts] == [
        ("human", "patient person", True),
    ]


def test_singular_sortal_remains_an_exact_disjunction_branch() -> None:
    facts = [
        f
        for f in solve("Ada is a student or a human.", REGISTRY, tracing=False).store.by_kind(Disjunction)
        if f.provenance.source == "logic/disj-ground-bare"
    ]
    assert [(f.entity, f.left, f.right, f.exclusive) for f in facts] == [
        ("ada", "student", "human", False),
    ]


def test_signed_universal_refuses_positive_reader() -> None:
    facts = solve("All humans are not patient people.", REGISTRY, tracing=False).store.by_kind(Quantified)
    assert not any(f.provenance.source == "logic/universal-copular-all-are" for f in facts)


def test_disjunctive_universal_refuses_flat_positive_reader() -> None:
    facts = solve("All humans are patient people or calm people.", REGISTRY, tracing=False).store.by_kind(Quantified)
    assert not any(f.provenance.source == "logic/universal-copular-all-are" for f in facts)


def test_existential_surface_refuses_universal_reader() -> None:
    facts = solve("Some humans are patient people.", REGISTRY, tracing=False).store.by_kind(Quantified)
    assert not any(f.provenance.source == "logic/universal-copular-all-are" for f in facts)


def test_ground_conjunction_refuses_disjunction_reader() -> None:
    facts = solve("Ada is a student and a human.", REGISTRY, tracing=False).store.by_kind(Disjunction)
    assert not any(f.provenance.source == "logic/disj-ground-bare" for f in facts)
