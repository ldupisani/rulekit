"""A word keeps its diacritics: _TOKEN's letter class is Unicode.

The ASCII-only class shredded a word at its first non-ASCII letter —
'Sūduva' became 's' + 'duva' and 'Léa' became 'L' + 'a', and the
FRAGMENTS could be KNOWN words (that 'a' annotated as an ARTICLE, a
phantom unit in every downstream pass). Real names carry diacritics in
three DEV corpora (gsm8k, scibench, folio — measured 2026-07-17).
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.tokenize import tokenize
from rulekit.kernel.model import Unit, Word

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def contractions():
    # the clitic table is PACK DATA now (rulekit/contractions@1), so a caller
    # that wants "Léa's" split has to supply it — `engine` always does. These
    # cases assert the possessive split, so they pass it too.
    return load_project(ROOT / "projects" / "gsm8k").registry.contractions


def _surfaces(sentence, contractions=()):
    return [u.surface for u in tokenize(sentence, tracing=False,
                                        contractions=contractions).units]


def test_diacritic_word_is_one_token():
    assert _surfaces("Sūduva Marijampolė is a soccer team.") == [
        "Sūduva", "Marijampolė", "is", "a", "soccer", "team", ".",
    ]


def test_accented_common_word_is_one_token():
    assert _surfaces("Sam visited a café.") == [
        "Sam", "visited", "a", "café", ".",
    ]


def test_diacritic_name_takes_the_possessive_clitic(contractions):
    assert _surfaces("Léa's dog barked.", contractions) == [
        "Léa", "'s", "dog", "barked", ".",
    ]


def _folds(sentence, contractions=()):
    return [u.features["fold"] for u in tokenize(sentence, tracing=False,
                                                 contractions=contractions).units]


def test_curly_possessive_matches_straight(contractions):
    # U+2019 outside the apostrophe class was DROPPED between tokens:
    # "Rex’s" read as 'Rex' + 's' (fold 's'), so the same phrase minted a
    # different fact key than its straight-quote spelling one sentence
    # over. The stem keeps its written surface; the clitic piece surfaces
    # as the TABLE's expansion (the same replacement "isn't" -> "not"
    # already performs), and the fold normalizes.
    curly = tokenize("Rex’s dog barked.", tracing=False,
                     contractions=contractions).units
    assert [u.surface for u in curly] == ["Rex", "'s", "dog", "barked", "."]
    assert [u.features["fold"] for u in curly] == _folds(
        "Rex's dog barked.", contractions)


def test_curly_contraction_matches_straight(contractions):
    # "isn’t" shredded to 'isn' + 't' under the old class; now it splits
    # through the clitic table exactly like "isn't"
    assert _folds("It isn’t red.", contractions) == _folds(
        "It isn't red.", contractions)


def test_ascii_tokenization_unchanged(contractions):
    # the incidental-behaviors-are-contract pin: plain ASCII text must
    # tokenize byte-identically to the old class
    assert _surfaces("John's 3 dogs ate 1/4 of the 5th cake, quickly!", contractions) == [
        "John", "'s", "3", "dogs", "ate", "1/4", "of", "the", "5th",
        "cake", ",", "quickly", "!",
    ]


@pytest.mark.parametrize("text", [
    "Aven’s surname is Reed-Park.",
    "Aven's surname is Reed\u2010Park.",
    "Aven's surname is Reed\u2011Park.",
    "Aven's surname is Reed@Park.",
    "Aven isn't reading a 100-page book.",
    "Aven’s surname is Reed-.",
    "Aven  has\t12 apples.",
])
def test_written_projection_keeps_source_spelling_separate_from_token_surfaces(contractions, text):
    reading = tokenize(text, contractions=contractions)
    words = tuple(word for unit in reading.units for word in unit.words)
    merged = Unit(999, words)
    assert merged.written == text
    assert merged.surface == " ".join(word.surface for word in words)


def test_written_projection_falls_back_for_source_free_constructed_words():
    assert Unit(0, (Word("Aven", 0), Word("Reed", 1))).written == "Aven Reed"
