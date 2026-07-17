"""Tokenization: text -> sentences -> Reading with one Unit per token.

Keeps every surface exactly as written (annotate, don't transform); the only
normalizations are case-folding for lookup (stored as feature "fold") and
digit-comma stripping handled later by numbers.py reading the raw surface.
"""

from __future__ import annotations

import re

from .model import Reading, Word

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_TOKEN = re.compile(
    # `[^\W\d_]` = any Unicode LETTER: an ASCII-only class SHREDS a word at
    # its first diacritic ('Sūduva' -> 's' + 'duva', 'Léa' -> 'L' + 'a' —
    # and the fragments can be KNOWN words: that 'a' annotated as an
    # ARTICLE). Real names carry diacritics in three DEV corpora (gsm8k 9
    # items, scibench 7, folio 17 — measured 2026-07-17; all 9 gsm8k items
    # decline before and after, the fix can only join what was shredded).
    r"\d+/\d+"                                  # slash fraction ("1/4")
    r"|\d[\d,]*(?:st|nd|rd|th)(?![^\W\d_])"     # fused ordinal ("5th", "21st")
    r"|\$?\d[\d,]*(?:\.\d+)?%?"                 # numbers/currency/percent
    r"|[^\W\d_]+(?:'[^\W\d_]+)?"                 # words (with contractions)
    r"|'s"                                       # bare possessive clitic
    r"|[.,!?;:]"
)

_CONTRACTIONS = {
    "n't": "not",
    "'s": "'s",  # kept as its own token (possessive/copula resolved later)
    "'re": "are",
    "'ll": "will",
    "'ve": "have",
}


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENT_SPLIT.split(text.strip())]
    return [p for p in parts if p]


def tokenize(sentence: str, sentence_index: int = 0, tracing: bool = True) -> Reading:
    reading = Reading(sentence, sentence_index, tracing=tracing)
    index = 0
    for match in _TOKEN.finditer(sentence):
        surface = match.group()
        # split contractions ("isn't" -> "is" + "not")
        pieces = [surface]
        for suffix, expansion in _CONTRACTIONS.items():
            if surface.lower().endswith(suffix) and len(surface) > len(suffix):
                stem = surface[: -len(suffix)]
                pieces = [stem, expansion]
                break
        for piece in pieces:
            unit = reading.new_unit((Word(piece, index),))
            unit.features["fold"] = piece.lower()
            reading.units.append(unit)
            index += 1
    return reading
