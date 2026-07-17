"""A word keeps its diacritics: _TOKEN's letter class is Unicode.

The ASCII-only class shredded a word at its first non-ASCII letter —
'Sūduva' became 's' + 'duva' and 'Léa' became 'L' + 'a', and the
FRAGMENTS could be KNOWN words (that 'a' annotated as an ARTICLE, a
phantom unit in every downstream pass). Real names carry diacritics in
three DEV corpora (gsm8k, scibench, folio — measured 2026-07-17).
"""

from rulekit.kernel.tokenize import tokenize


def _surfaces(sentence):
    return [u.surface for u in tokenize(sentence, tracing=False).units]


def test_diacritic_word_is_one_token():
    assert _surfaces("Sūduva Marijampolė is a soccer team.") == [
        "Sūduva", "Marijampolė", "is", "a", "soccer", "team", ".",
    ]


def test_accented_common_word_is_one_token():
    assert _surfaces("Sam visited a café.") == [
        "Sam", "visited", "a", "café", ".",
    ]


def test_diacritic_name_takes_the_possessive_clitic():
    assert _surfaces("Léa's dog barked.") == [
        "Léa", "'s", "dog", "barked", ".",
    ]


def test_ascii_tokenization_unchanged():
    # the incidental-behaviors-are-contract pin: plain ASCII text must
    # tokenize byte-identically to the old class
    assert _surfaces("John's 3 dogs ate 1/4 of the 5th cake, quickly!") == [
        "John", "'s", "3", "dogs", "ate", "1/4", "of", "the", "5th",
        "cake", ",", "quickly", "!",
    ]
