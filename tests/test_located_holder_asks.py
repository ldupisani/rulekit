"""Located-holder ``how many ... are there in ...`` questions.

Synthetic only.  These tests specify the reusable question class rather than
copying either benchmark item that exposed it.

The trailing location is referential, not decorative.  A possessed,
pack-declared location names its explicit owner as the holder.  This stays
separate from the older entity-less ``how many ... are there`` ask, which must
still decline when several holders exist and no supported location identifies
one.  A bare proper-name location remains unsupported: capitalization alone
does not prove that a named place denotes the requested holder total.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.patterns import match_ask


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/gsm8k")).registry


def _solve_with_ask(text, reg):
    result = solve(text, reg, tracing=False)
    matched = match_ask(result.question, reg) if result.question else None
    return result, matched[0].id if matched else None


def test_bare_named_location_remains_entityless_and_declines(reg):
    result, ask_id = _solve_with_ask(
        "Arden has 9 apples. Briar has 14 apples. "
        "How many apples are there in Arden?",
        reg,
    )

    assert ask_id == "ask/how-many-there"
    assert not result.answer.committed
    assert "2 entities hold 'apple'" in result.answer.reason


def test_possessed_location_selects_its_explicit_owner(reg):
    result, ask_id = _solve_with_ask(
        "Mira has 11 pens. Tova has 19 pens. "
        "How many pens are there in Mira's box?",
        reg,
    )

    assert ask_id == "ask/how-many-there-in-possessed-place"
    assert result.answer.value == 11.0


def test_possessed_location_consumes_a_derived_relation_total(reg):
    result, ask_id = _solve_with_ask(
        "Mira has 4 times as many pens as Tova. Tova has 6 pens. "
        "How many pens are there in Mira's box?",
        reg,
    )

    assert ask_id == "ask/how-many-there-in-possessed-place"
    assert result.answer.value == 24.0


def test_possessed_location_never_falls_back_to_another_holder(reg):
    result, ask_id = _solve_with_ask(
        "Mira has 11 pens. Tova has 19 pens. "
        "How many pens are there in Sela's box?",
        reg,
    )

    assert ask_id == "ask/how-many-there-in-possessed-place"
    assert not result.answer.committed
    assert "no quantity known for 'sela'" in result.answer.reason


@pytest.mark.parametrize(
    "question",
    [
        "How many pens are there in the box?",
        "How many pens are there in Mira's dog?",
        "How many pens are there from Mira?",
    ],
)
def test_unsupported_locations_remain_entityless_and_decline(reg, question):
    result, ask_id = _solve_with_ask(
        f"Mira has 11 pens. Tova has 19 pens. {question}",
        reg,
    )

    assert ask_id == "ask/how-many-there"
    assert not result.answer.committed
    assert "2 entities hold 'pen'" in result.answer.reason


def test_nonstate_verb_does_not_turn_location_into_a_holder(reg):
    result, ask_id = _solve_with_ask(
        "Arden has 9 apples. Briar has 14 apples. "
        "How many apples grow there in Arden?",
        reg,
    )

    assert ask_id == "ask/how-many-there"
    assert not result.answer.committed


def test_possessed_location_preserves_measure_qualifiers(reg):
    result, ask_id = _solve_with_ask(
        "Mira has 4 red apples. Mira has 7 green apples. Tova has 9 apples. "
        "How many red apples are there in Mira's garden?",
        reg,
    )

    assert ask_id == "ask/how-many-there-in-possessed-place"
    assert result.answer.value == 4.0


def test_bare_measure_can_sum_compatible_variants_for_possessed_location(reg):
    result, ask_id = _solve_with_ask(
        "Mira has 4 red apples. Mira has 7 green apples. Tova has 9 apples. "
        "How many apples are there in Mira's garden?",
        reg,
    )

    assert ask_id == "ask/how-many-there-in-possessed-place"
    assert result.answer.value == 11.0
