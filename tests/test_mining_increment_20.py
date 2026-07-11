"""Mining candidate ordinal-suffix-tokens: fused ordinal number tokens
(5th, 3rd, 21st). The tokenizer previously split a fused ordinal into a
digit token plus an orphan letter-token ("th"/"st"/"nd"/"rd"), which never
resolves in the lexicon and declines the whole reading as unknown-word.
This recognizes digit+ordinal-suffix as ONE token (productive grammatical
morphology, like digit parsing itself — not a lexicon fact) and gives it
its own value_kind ("ordinal"), distinct from count/multiplier/fraction:
an ordinal is an index/modifier, never an operative count, so it is
excluded from value-accounting and from every obligation slot that counts
as a quantity — it only stops being an unknown word. Synthetic only."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import solve
from rulekit.kernel.numbers import annotate_numbers
from rulekit.kernel.senses import annotate_senses
from rulekit.kernel.tokenize import tokenize

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def full_registry():
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", mined])
    )


@pytest.mark.parametrize(
    "surface",
    ["5th", "21st", "3rd", "2nd", "100th"],
)
def test_fused_ordinal_is_one_token_not_unknown(full_registry, surface):
    # the tokenizer must not split "<digit><suffix>" into a digit and an
    # orphan letter-token; the fused token gets value_kind "ordinal" and is
    # never marked unknown
    reading = tokenize(f"It happened on the {surface} day.")
    reading = annotate_numbers(reading, full_registry)
    reading = annotate_senses(reading, full_registry)
    surfaces = [u.surface for u in reading.units]
    assert surface in surfaces
    assert "th" not in surfaces and "st" not in surfaces
    assert "nd" not in surfaces and "rd" not in surfaces
    ordinal_unit = next(u for u in reading.units if u.surface == surface)
    assert ordinal_unit.features.get("value_kind") == "ordinal"
    assert ordinal_unit.features.get("unknown") is not True
    assert reading.unknown_words() == []


def test_ordinal_no_longer_blocks_a_solvable_sentence(full_registry):
    # before this fix, the orphan 'th' token declined the whole reading as
    # unknown-word even though every other word was known and the sentence
    # is a plain single-event fold
    r = solve(
        "Tom read 6 books on his 21st birthday. How many books did Tom read?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 6


def test_ordinal_never_feeds_the_fold_as_a_count(full_registry):
    # decline-safety: an ordinal is an index, never an operative count —
    # "the 5th day" must not add 5 into the arithmetic. If the ordinal were
    # mistakenly typed as a "count", this would wrongly total 7 (2 + 5).
    r = solve(
        "Mia found 2 shells on the 5th day. How many shells did Mia find?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 2


def test_ordinal_does_not_satisfy_a_dobj_slot(full_registry):
    # decline-safety: an ordinal must not stand in for a counted noun
    # object. A verb whose only candidate object is an ordinal ("her 5th")
    # must still decline rather than silently reading it as a quantity.
    r = solve(
        "Mia visited grandma on her 5th. How many times did Mia visit grandma?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_unfused_ordinary_number_unaffected(full_registry):
    # a plain digit followed by an unrelated word (not glued as a suffix)
    # must still tokenize as two separate units, unchanged
    reading = tokenize("She has 5 dogs.")
    reading = annotate_numbers(reading, full_registry)
    surfaces = [u.surface for u in reading.units]
    assert surfaces == ["She", "has", "5", "dogs", "."]
    five = next(u for u in reading.units if u.surface == "5")
    assert five.features.get("value_kind") == "count"
