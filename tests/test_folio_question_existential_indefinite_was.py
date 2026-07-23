"""Buyer-backed semantic projection for ``A CLS was PRED`` questions."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.answer import AnswerProof
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Atom
from rulekit.kernel.patterns import match_ask


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "ask/logic-existential-indefinite-was"


def _matched(text: str):
    result = solve(text, REGISTRY, tracing=False)
    assert result.question is not None
    return result, match_ask(result.question, REGISTRY)


def test_named_witness_answers_the_indefinite_passive_query() -> None:
    result, matched = _matched(
        "Orion is a patient navigator. Orion was praised by Lyra. "
        "Is it true that A patient navigator was praised by Lyra?"
    )
    assert matched is not None
    assert matched[0].id == SOURCE
    assert result.answer.value == "yes"

    proof = result.answer.proof
    assert isinstance(proof, AnswerProof)
    assert proof.query.kind == "Existential"
    assert dict(proof.query.fields) == {
        "cls": "patient navigator",
        "pred": "praised by lyra",
        "polarity": True,
    }
    assert len(proof.steps) == 1
    assert proof.steps[0].rule == "existential-introduction"
    evidence = proof.steps[0].evidence
    assert [(f.entity, f.pred) for f in evidence if isinstance(f, Atom)] == [
        ("orion", "patient navigator"),
        ("orion", "praised by lyra"),
    ]


def test_both_exact_properties_are_required() -> None:
    missing_class, _ = _matched(
        "Orion was praised by Lyra. "
        "Is it true that A patient navigator was praised by Lyra?"
    )
    missing_predicate, _ = _matched(
        "Orion is a patient navigator. "
        "Is it true that A patient navigator was praised by Lyra?"
    )
    assert missing_class.answer.value == "undetermined"
    assert missing_predicate.answer.value == "undetermined"
    assert missing_class.answer.proof is not None
    assert missing_class.answer.proof.steps == ()


def test_changed_class_or_predicate_does_not_loosen() -> None:
    changed_class, _ = _matched(
        "Orion is a patient navigator. Orion was praised by Lyra. "
        "Is it true that A patient cartographer was praised by Lyra?"
    )
    changed_predicate, _ = _matched(
        "Orion is a patient navigator. Orion was praised by Lyra. "
        "Is it true that A patient navigator was praised by Vega?"
    )
    assert changed_class.answer.value == "undetermined"
    assert changed_predicate.answer.value == "undetermined"


@pytest.mark.parametrize(
    "question",
    [
        "Is it true that The patient navigator was praised by Lyra?",
        "Is it true that Some patient navigators were praised by Lyra?",
        "Is it true that A patient navigator was not praised by Lyra?",
        "Is it true that No patient navigator was praised by Lyra?",
        "Is it true that A patient navigator might have been praised by Lyra?",
        "Is it true that A patient navigator was praised by Lyra or Vega?",
    ],
)
def test_definite_plural_signed_quantified_modal_and_disjunctive_neighbors_refuse(
    question: str,
) -> None:
    _, matched = _matched(question)
    assert matched is None or matched[0].id != SOURCE
