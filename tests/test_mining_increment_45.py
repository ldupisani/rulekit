"""Conjoined event-verb objects — the verb->dobj binding only captures the
FIRST conjunct in "found A and B" / "lost A, B, and C" (the general
conjunction-handling gap noted at increment 11, closed there for `purchase`
verbs and at increment 35 for `state` verbs; still open for every OTHER
verb). This extends increment 11's conjunct-recovery walker
(`_conjoined_purchase_items` in learn.py) to any verb tagged with a
polarity category (acquire/lose and their subcategories: produce, receive,
sell, ...): each comma/conjunction segment's own counted noun becomes an
ordinary signed event Quantity for the SAME subject and verb, exactly like
a purchase list's or a state verb's siblings.

An event verb with NO polarity category ('keep'/'retain', 'want'/'desire' —
deliberately untagged, see packs/core-english/categories/core.yaml) is
UNCHANGED: the conjunct walker still never fires for it, so a stated
sibling count stays unaccounted and the value-accounting guard declines
the whole sentence exactly as it did before this increment (the polarity
invariant).

Only a PURCHASE verb's own siblings ever emit a Price fact (increment 11's
discipline, untouched) — a polarity-tagged event verb that is not a
purchase verb (e.g. 'find'/'lose') never prices its siblings even when a
segment carries a distributive 'each' and a currency noun; that segment is
simply left unaccounted and the sentence declines rather than risk
inventing a price.

The walker's tail scan still STOPS the instant it meets another verb and
DISCARDS (does not flush) the in-progress segment when it does (increment
35's stop-on-verb-break discipline, byte-for-byte unchanged): a second
finite clause coordinated with ','/'and' is a NEW clause, not a sibling
noun phrase in the first subject's list, and must never leak its own
subject/dobj into the first entity's count.

Synthetic only."""

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


def test_conjoined_acquire_verb_first_item(full_registry):
    r = solve(
        "Malik found 6 marbles and 3 buttons. How many marbles did Malik find?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 6


def test_conjoined_acquire_verb_second_item(full_registry):
    r = solve(
        "Malik found 6 marbles and 3 buttons. How many buttons did Malik find?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 3


def test_conjoined_lose_verb_three_way_middle_item(full_registry):
    # comma-and-comma three-way list; the recovered item is the MIDDLE
    # conjunct, not first or last.
    r = solve(
        "Talia lost 5 pencils, 2 pens, and 1 eraser. How many pens did Talia lose?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 2


def test_conjoined_lose_verb_three_way_last_item(full_registry):
    r = solve(
        "Talia lost 5 pencils, 2 pens, and 1 eraser. How many erasers did Talia lose?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 1


def test_untagged_event_verb_conjunction_still_declines(full_registry):
    # 'keep'/'keeps' is the 'retain' category — a plain event verb (never
    # state, never purchase) with NO polarity tag. The walker must not
    # recover its siblings: the second count stays unaccounted and the
    # whole sentence declines, exactly as before this increment (the
    # polarity invariant this candidate is scoped by).
    r = solve(
        "Owen keeps 4 kites and 2 balloons. How many kites does Owen keep?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_non_purchase_event_sibling_never_priced(full_registry):
    # 'find' is acquire-tagged (this candidate recovers its siblings) but
    # is NOT a purchase verb — a distributive 'each' plus a currency noun
    # on a sibling segment must never be read as a price (that's the
    # purchase-only gate, increment 11). The segment is simply unbuilt, so
    # the whole sentence declines rather than invent a price or silently
    # drop the $2.
    r = solve(
        "Dana found 4 rocks and 3 shells at $2 each. How many rocks did Dana find?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_coordinated_second_clause_now_resolves_for_event_verb(full_registry):
    # the stop-on-verb-break discipline (increment 35) still guards a
    # second finite clause with no NAME subject of its own (see
    # test_mining_increment_35.py's counted-subject variant). This test
    # originally asserted decline for "Jordan lost 6 books" specifically,
    # on the theory that
    # walking into it and folding its dobj as a sibling of the first
    # entity would be a silent miscount. Mining candidate conjoined-
    # clause-holdings makes that ambiguity structurally impossible:
    # engine.py's `_split_conjoined_clauses` now splits "Jordan lost 6
    # books" into its OWN premise before this walker's tail scan ever sees
    # it, so the answer correctly resolves instead of declining.
    r = solve(
        "Priya lost 5 pens and 3 pencils, and Jordan lost 6 books. "
        "How many pens did Priya lose?",
        full_registry,
    )
    assert r.answer.value == 5
