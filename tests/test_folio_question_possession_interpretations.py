"""Existential possession agreement and explicit indefinite clarification."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.patterns import match_ask
from rulekit.server.api import _clarification_json, _semantic_json


REGISTRY = load_project(Path("projects/scratch")).registry
PLURAL_SOURCE = "ask/logic-existential-some-have"
AMBIGUOUS_SOURCE = "ask/logic-ambiguous-indefinite-has"
TEXT = (
    "Nadia is an otter. Nadia has a badge. "
    "Is it true that an otter has a badge?"
)


def _matched(text: str, interpretation: str | None = None):
    result = solve(
        text,
        REGISTRY,
        tracing=False,
        interpretation=interpretation,
    )
    assert result.question is not None
    return result, match_ask(result.question, REGISTRY)


def test_plural_some_possession_is_an_explicit_existential() -> None:
    result, matched = _matched(
        "Nadia is an otter. Nadia has a badge. "
        "Is it true that some otters have badges?"
    )
    assert matched is not None
    assert matched[0].id == PLURAL_SOURCE
    assert result.answer.value == "yes"
    assert result.answer.clarification is None
    assert result.answer.proof is not None
    assert dict(result.answer.proof.query.fields) == {
        "cls": "otter",
        "pred": "have badge",
        "polarity": True,
    }


def test_plural_some_still_requires_both_witness_properties() -> None:
    result, matched = _matched(
        "Nadia is an otter. "
        "Is it true that some otters have badges?"
    )
    assert matched is not None
    assert matched[0].id == PLURAL_SOURCE
    assert result.answer.value == "undetermined"
    assert result.answer.proof is not None
    assert result.answer.proof.steps == ()


def test_indefinite_subject_pauses_with_two_normalized_readings() -> None:
    result, matched = _matched(TEXT)
    assert matched is not None
    assert matched[0].id == AMBIGUOUS_SOURCE
    assert result.answer.kind == "decline"
    assert result.answer.value is None

    clarification = result.answer.clarification
    assert clarification is not None
    assert clarification.selected is None
    assert [option.id for option in clarification.options] == [
        "existential",
        "class-wide",
    ]
    assert [option.query.kind for option in clarification.options] == [
        "Existential",
        "Universal",
    ]
    assert all(
        dict(option.query.fields) == {
            "cls": "otter",
            "pred": "have badge",
            "polarity": True,
        }
        for option in clarification.options
    )


def test_confirmed_existential_reruns_the_existing_witness_consumer() -> None:
    result, _ = _matched(TEXT, interpretation="existential")
    assert result.answer.value == "yes"
    assert result.answer.proof is not None
    assert result.answer.proof.steps[0].rule == "existential-introduction"
    assert result.answer.clarification is not None
    assert result.answer.clarification.selected == "existential"


def test_confirmed_class_wide_reading_requires_a_universal_fact() -> None:
    witness_only, _ = _matched(TEXT, interpretation="class-wide")
    asserted_universal, _ = _matched(
        "Every otter has a badge. "
        "Is it true that an otter has a badge?",
        interpretation="class-wide",
    )
    assert witness_only.answer.value == "undetermined"
    assert asserted_universal.answer.value == "yes"
    assert asserted_universal.answer.clarification is not None
    assert asserted_universal.answer.clarification.selected == "class-wide"


def test_unknown_confirmation_does_not_guess() -> None:
    result, _ = _matched(TEXT, interpretation="generic")
    assert result.answer.kind == "decline"
    assert result.answer.value is None
    assert result.answer.clarification is not None
    assert result.answer.clarification.selected is None
    assert "unknown interpretation" in result.answer.reason


def test_semantic_api_exposes_candidates_then_the_confirmed_query() -> None:
    paused, matched = _matched(TEXT)
    assert matched is not None
    clarification = _clarification_json(paused.answer.clarification)
    assert clarification is not None
    assert clarification["selected"] is None
    assert [option["id"] for option in clarification["options"]] == [
        "existential",
        "class-wide",
    ]
    assert _semantic_json(paused, matched)["query"] == {
        "kind": "Ambiguous",
        "fields": {"interpretations": 2},
    }

    confirmed, _ = _matched(TEXT, interpretation="existential")
    assert _semantic_json(confirmed, matched)["query"] == {
        "kind": "Existential",
        "fields": {
            "cls": "otter",
            "pred": "have badge",
            "polarity": True,
        },
    }


@pytest.mark.parametrize(
    "question",
    [
        "Is it true that the otter has a badge?",
        "Is it true that an otter has badges?",
        "Is it true that an otter had a badge?",
        "Is it true that an otter may have a badge?",
        "Is it true that an otter does not have a badge?",
        "Is it true that an otter has a badge or a ribbon?",
        "Is it true that an otter has a badge and a ribbon?",
        "Is it true that an otter has 3 badges?",
    ],
)
def test_neighboring_surfaces_do_not_enter_the_ambiguity_family(
    question: str,
) -> None:
    _, matched = _matched(question)
    assert matched is None or matched[0].id != AMBIGUOUS_SOURCE


def test_designer_can_elicit_and_submit_an_interpretation() -> None:
    root = Path("src/rulekit/server/static")
    html = (root / "index.html").read_text()
    js = (root / "app.js").read_text()
    assert 'id="clarification"' in html
    assert "renderClarification(t)" in js
    assert "runTrace(option.id)" in js
    assert "REASONING PAUSED" in js
