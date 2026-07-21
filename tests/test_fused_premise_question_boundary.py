"""A fully read premise and ask can prove their omitted sentence boundary."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import solve, split_question


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def logic_reg():
    return compile_registry(
        load_packs([
            ROOT / "packs/core-english",
            ROOT / "packs/arithmetic",
            ROOT / "packs/difg-mined",
            ROOT / "projects/scratch/packs/logic",
        ])
    )


def test_exact_readers_recover_the_missing_boundary(logic_reg):
    premises, question = split_question(
        "Rex is a dog Is it true that Rex is a dog?",
        logic_reg,
    )

    assert premises == ["Rex is a dog."]
    assert question == "Is it true that Rex is a dog?"


def test_recovered_boundary_solves_end_to_end(logic_reg):
    result = solve(
        "Rex is a dog Is it true that Rex is a dog?",
        logic_reg,
        tracing=False,
    )

    assert result.answer.kind == "verdict"
    assert result.answer.value == "yes"


def test_negative_premise_keeps_its_polarity(logic_reg):
    result = solve(
        "Rex is not a dog Is it true that Rex is a dog?",
        logic_reg,
        tracing=False,
    )

    assert result.answer.kind == "verdict"
    assert result.answer.value == "no"


def test_exact_disjunction_is_promoted_without_asserting_a_branch(logic_reg):
    result = solve(
        "Rex is a dog or a cat Is it true that Rex is a dog?",
        logic_reg,
        tracing=False,
    )

    assert [reading.text for reading in result.premises] == [
        "Rex is a dog or a cat.",
    ]
    assert result.answer.kind == "verdict"
    assert result.answer.value == "undetermined"


def test_partially_read_left_fragment_does_not_create_a_boundary(logic_reg):
    text = "Yesterday Rex is a dog Is it true that Rex is a dog?"

    assert split_question(text, logic_reg) == ([], text)


def test_unknown_left_fragment_does_not_create_a_boundary(logic_reg):
    text = "Rex glimmers brightly Is it true that Rex is a dog?"

    assert split_question(text, logic_reg) == ([], text)


def test_lowercase_token_cannot_replace_terminal_punctuation(logic_reg):
    text = "Rex is a dog is it true that Rex is a dog?"

    assert split_question(text, logic_reg) == ([], text)


def test_existing_punctuated_boundary_is_unchanged(logic_reg):
    text = "Rex is a dog. Is it true that Rex is a dog?"

    assert split_question(text, logic_reg) == (
        ["Rex is a dog."],
        "Is it true that Rex is a dog?",
    )
