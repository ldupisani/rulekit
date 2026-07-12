"""Conjoined state-verb holdings — the verb->dobj binding only captures the
FIRST conjunct in "has A and B" / "has A, B, and C" (the general
conjunction-handling gap noted at increment 11, left open there for every
verb outside the `purchase` category). This scopes increment 11's
conjunct-recovery walker (`_conjoined_purchase_items` in learn.py) to the
`state` verb category as well: each comma/conjunction segment's own counted
noun becomes a sibling Quantity for the SAME subject, exactly like a
purchase list's siblings. State siblings are ordinary holdings, never
priced — only a purchase verb's own siblings ever emit a Price fact, so a
distributive 'each'/flat currency price on a state-verb sibling is left for
the value-accounting guard to decline rather than folded as a purchase.

The walker's tail scan additionally STOPS the instant it meets another verb
and DISCARDS (does not flush) the in-progress segment when it does: a
second finite clause coordinated with ','/'and' ("Priya has 5 pens, and
Jordan has 3 pencils") is a NEW clause, not a sibling noun phrase in the
first subject's list, and must never leak its own subject/dobj into the
first entity's count.

Synthetic only.
"""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import solve

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def full_registry():
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", mined])
    )


def test_two_conjoined_holdings_first_item(full_registry):
    r = solve(
        "Priya has 5 pens and 3 pencils. How many pens does Priya have?",
        full_registry,
    )
    assert r.answer.value == 5


def test_two_conjoined_holdings_second_item(full_registry):
    r = solve(
        "Priya has 5 pens and 3 pencils. How many pencils does Priya have?",
        full_registry,
    )
    assert r.answer.value == 3


def test_three_conjoined_holdings_oxford_comma(full_registry):
    r = solve(
        "Jordan has 4 toys, 6 books, and 2 shirts. How many books does Jordan have?",
        full_registry,
    )
    assert r.answer.value == 6


def test_own_verb_variant(full_registry):
    r = solve(
        "Jordan owns 4 toys and 6 books. How many toys does Jordan own?",
        full_registry,
    )
    assert r.answer.value == 4


def test_spelled_out_numbers(full_registry):
    r = solve(
        "Jordan has three toys and two books. How many toys does Jordan have?",
        full_registry,
    )
    assert r.answer.value == 3


def test_coordinated_second_clause_now_resolves(full_registry):
    # a SECOND finite clause coordinated with ',/and' is a NEW clause with
    # its own subject/verb, not a sibling noun phrase in the first
    # subject's list. This test originally asserted decline (walking into
    # the second clause and folding its dobj as a sibling of the first
    # entity would have been a silent miscount). Mining candidate
    # conjoined-clause-holdings makes the ambiguity structurally
    # impossible: "Jordan has 6 books" is now split into its OWN premise
    # by engine.py's `_split_conjoined_clauses` before this walker's tail
    # scan ever sees it, so the walker's stop-on-verb-break discipline
    # (still exercised by the counted-subject variant below, which has no
    # NAME after the comma and so never splits) no longer needs to guard
    # this exact shape — the answer correctly resolves instead.
    r = solve(
        "Priya has 5 pens and 3 pencils, and Jordan has 6 books. "
        "How many pens does Priya have?",
        full_registry,
    )
    assert r.answer.value == 5


def test_coordinated_second_clause_with_counted_subject_declines(full_registry):
    # a second clause whose OWN subject noun phrase carries a count ("her 6
    # books") must not have that count misattributed to the first entity
    # either — the verb-boundary stop discards the in-progress segment.
    r = solve(
        "Priya has 5 pens and 3 pencils, and her 6 books are on the shelf. "
        "How many pens does Priya have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_negated_state_conjunction_declines(full_registry):
    r = solve(
        "Priya does not have 5 pens and 3 pencils. How many pens does Priya have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_state_sibling_never_priced(full_registry):
    # a flat currency price on a state-verb sibling is NOT a purchase — it
    # must never surface as a Price fact (only a purchase verb's own
    # siblings do); the unaccounted currency value then correctly makes
    # the whole answer decline rather than commit anything derived from it.
    r = solve(
        "Priya has 5 pens and 1 sticker for $2. How many pens does Priya have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_purchase_conjunction_unaffected(full_registry):
    # non-regression: the purchase-verb path (increment 11) is untouched —
    # a priced purchase list still folds Quantity + Price for each sibling.
    r = solve(
        "Jordan buys 3 toys at $10 each and 2 books at $5 each. "
        "How much did Jordan spend?",
        full_registry,
    )
    assert r.answer.value == 40


def test_event_verb_conjunction_still_declines(full_registry):
    # an event verb with NO polarity category (neither `state`, `purchase`,
    # nor acquire/lose) is UNCHANGED — the general conjunction gap remains
    # open for untagged event verbs. ('eat'/'ate' is 'lose'-tagged and
    # gained conjunct recovery in the event-conjunct-recovery candidate, so
    # this test now exercises 'keep' — the 'retain' category, deliberately
    # untagged for polarity — to keep documenting the still-open gap.)
    r = solve(
        "Jordan keeps 4 apples and 2 oranges. How many apples does Jordan keep?",
        full_registry,
    )
    assert r.answer.kind == "decline"
