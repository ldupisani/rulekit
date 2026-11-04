"""Tokenization: text -> sentences -> Reading with one Unit per token.

Keeps every surface exactly as written (annotate, don't transform); the only
normalizations are case-folding for lookup (stored as feature "fold") and
digit-comma stripping handled later by numbers.py reading the raw surface.
"""

from __future__ import annotations

import re
from functools import lru_cache
from collections.abc import Sequence

from .model import Reading, Word

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_TOKEN = re.compile(
    # `[^\W\d_]` = any Unicode LETTER: an ASCII-only class SHREDS a word at
    # its first diacritic ('Sūduva' -> 's' + 'duva', 'Léa' -> 'L' + 'a' —
    # and the fragments can be KNOWN words: that 'a' annotated as an
    # ARTICLE). Real names carry diacritics in three DEV corpora (gsm8k 9
    # items, scibench 7, folio 17 — measured 2026-07-17; all 9 gsm8k items
    # decline before and after, the fix can only join what was shredded).
    # An ISO DATE is ONE token, and it must lead the alternation: the number
    # branch below would otherwise take "2024" and leave "-01-01" behind, which
    # is how "2024-01-01" read as the three counts 2024, 1, 1. Fully anchored
    # (4-2-2 digits, and `(?!\d)` so a longer digit run cannot masquerade), so
    # a hyphenated NUMBER RANGE ("5-10") and a negative number are untouched.
    r"\d{4}-\d{2}-\d{2}(?!\d)"                   # ISO date ("2024-01-01")
    r"|\d+/\d+"                                 # slash fraction ("1/4")
    r"|\d[\d,]*(?:st|nd|rd|th)(?![^\W\d_])"     # fused ordinal ("5th", "21st")
    r"|(?:(?<!\w)-)?\$?(?:\d[\d,]*(?:\.\d+)?|\.\d+)%?"  # signed numbers/currency/percent
    # A compound scientific unit is ONE token. This alternative must precede
    # the ordinary word branch: otherwise "m/s^2" becomes 'm', 's', '2' and
    # the exponent masquerades as a stated scalar. Requiring either an
    # exponent or a unit separator keeps ordinary ASCII words on the existing
    # Unicode-aware branch below. Whether the resulting surface is a KNOWN
    # unit remains lexicon data; tokenization only preserves its structure.
    r"|[A-Za-z]+(?:\^\d+|(?:[/·][A-Za-z]+(?:\^\d+)?)+)"
    # the apostrophe class admits U+2019 (the typographic right single
    # quote) beside ASCII: corpora mix them freely ("Gould’s" in one
    # sentence, "Gould's" in the next), and a curly one outside the class
    # is DROPPED between tokens — "Gould’s" tokenized as 'Gould' + 's' and
    # "isn’t" shredded to 'isn' + 't', so the same phrase minted two
    # different fact keys depending on which quote its sentence used. The
    # SURFACE keeps whichever character was written (annotate, don't
    # transform); only the fold normalizes, below.
    r"|[^\W\d_]+(?:['’][^\W\d_]+)?"              # words (with contractions)
    r"|['’]s"                                    # bare possessive clitic
    r"|[.,!?;:]"
    # Arithmetic signs are semantic boundaries, not disposable whitespace.
    # Keep isolated minus too, without splitting lexical/numeric hyphens.
    r"|[+*=×÷−]|(?<!\w)-"
)

# fold-layer normalization (with .lower()): the typographic apostrophe reads
# as the ASCII one, so clitic-table suffix matching and every downstream fold
# comparison see ONE spelling
_FOLD_APOSTROPHE = str.maketrans("’", "'")


@lru_cache(maxsize=32)
def _token_pattern(currency_symbols: tuple[str, ...]):
    if not currency_symbols:
        return _TOKEN
    prefix = '(?:' + '|'.join(re.escape(symbol) for symbol in currency_symbols) + ')?'
    return re.compile(_TOKEN.pattern.replace(r'\$?', prefix, 1))

def split_sentences(text: str, nonterminal_abbreviations=()) -> list[str]:
    parts = [p.strip() for p in _SENT_SPLIT.split(text.strip())]
    sentences = []
    abbreviations = {word.casefold().rstrip(".") for word in nonterminal_abbreviations}
    for part in parts:
        if not part:
            continue
        if sentences and sentences[-1].split()[-1].casefold().rstrip(".") in abbreviations:
            sentences[-1] += " " + part
        else:
            sentences.append(part)
    return sentences


def tokenize(
    sentence: str,
    sentence_index: int = 0,
    tracing: bool = True,
    contractions: Sequence[tuple[str, str]] = (),
    assumption: bool = False,
    currency_symbols: Sequence[str] = (),
) -> Reading:
    """Text -> one Unit per token.

    `contractions` is the clitic table (`rulekit/contractions@1`, reached as
    `reg.contractions`), passed in rather than read from a Registry so this
    stage stays what it is: pure text -> tokens with no lexicon lookups. It
    used to be a dict in this module, which made it the one place the kernel
    enumerated WORDS.

    It must arrive sorted LONGEST CLITIC FIRST — `compile_registry` guarantees
    that — because matching is by suffix and a shorter clitic could otherwise
    shadow a longer one.

    Passing nothing means no expansion, which is deliberate and visible in the
    call: `engine` always supplies the table, and a caller that wants raw
    tokenization says so by omitting it.
    """
    reading = Reading(
        sentence,
        sentence_index,
        tracing=tracing,
        assumption=assumption,
    )
    index = 0
    previous_end: int | None = None
    pattern = _token_pattern(tuple(sorted(currency_symbols, key=lambda symbol: (-len(symbol), symbol))))
    matches = list(pattern.finditer(sentence))
    for match_no, match in enumerate(matches):
        surface = match.group()
        # split contractions ("isn't" -> "is" + "not"); matching runs on the
        # FOLD so a curly-apostrophe surface finds its straight-quote table
        # entry (U+2019 and ASCII "'" are both one char, so the suffix
        # length slices the raw surface correctly)
        folded = surface.lower().translate(_FOLD_APOSTROPHE)
        pieces = [surface]
        for suffix, expansion in contractions:
            if folded.endswith(suffix) and len(surface) > len(suffix):
                stem = surface[: -len(suffix)]
                pieces = [stem, expansion]
                break
        next_start = (
            matches[match_no + 1].start()
            if match_no + 1 < len(matches) else len(sentence)
        )
        for piece_no, piece in enumerate(pieces):
            before = (
                sentence[previous_end : match.start()]
                if piece_no == 0 and previous_end is not None else ""
            )
            source = piece
            if len(pieces) > 1:
                source = surface[:len(piece)] if piece_no == 0 else surface[len(pieces[0]):]
            after = (
                sentence[match.end():next_start]
                if piece_no == len(pieces) - 1 else ""
            )
            # Whitespace at the outer boundary is not part of a literal.
            # Non-tokenized punctuation must remain visible, not silently
            # repair a malformed literal into a valid one.
            after = after if after.strip() else ""
            unit = reading.new_unit((Word(piece, index, source, before, after),))
            unit.features["fold"] = piece.lower().translate(_FOLD_APOSTROPHE)
            # Keep the one piece of punctuation that changes the internal
            # structure of a numeric compound.  The tokenizer still does not
            # create a punctuation unit for a hyphen, but condensation can now
            # distinguish "a 100-page book" (100 describes pages) from
            # "100 page books" (100 describes books).  Only an immediately
            # adjacent source hyphen counts; spaced dashes remain ordinary
            # clause punctuation, and contraction expansions after the first
            # piece cannot inherit the source boundary.
            if (
                piece_no == 0
                and previous_end is not None
                and sentence[previous_end : match.start()] == "-"
            ):
                unit.features["joined_left_by_hyphen"] = True
            reading.units.append(unit)
            index += 1
        previous_end = match.end()
    return reading
