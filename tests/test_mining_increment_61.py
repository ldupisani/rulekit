"""Mining increment 61: cross-sentence item/measure inheritance for elided
event conjuncts ("sold 5 last week and 7 this week").

An event verb's dobj obligation only binds the FIRST conjunct in a
sentence (the pre-existing, general conjunction-handling gap named in
docs/methodology.md). Increments 11/35/45 recovered NOUN-bearing siblings for
purchase/state/event verbs. This candidate is the sibling for a conjunct
whose item noun is fully ELIDED: a bare, unmerged count value, optionally
trailing a bare temporal modifier ("this week", "last month" — the
`timeperiod` category, structure only). Such a conjunct states no item
because none IS stated, so it inherits the verb's bound dobj's own
entity/measure — recovering the stated number into the fold (a
value-accounting decline is no longer the reason it's unaccounted for),
never fabricating a measure it never named. Two same-key fold facts
collide (the pre-existing fact-store safety net) rather than silently
combining, so this enabler alone still declines end-to-end — by design,
per the mining brief: it only becomes SOLVE-capable once paired with a
further, separate mechanism (the parked event-goal-progress candidate)
that knows what to do with repeated same-item occurrences. This test
suite verifies the enabler's own, narrow behavior only. Synthetic only.
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


def test_bare_number_conjunct_is_recovered_not_dropped(full_registry):
    # Before this candidate: the second bare number ('6') never reached any
    # fact at all ("[value-accounting] stated count '6' ... reached no fact
    # and no arithmetic"). After: it IS folded (as its own event Quantity,
    # inheriting entity/measure/verb from the verb's bound dobj) — the two
    # same-key facts then collide (decline-safe), a DIFFERENT and more
    # informative reason than "never even tried". Confirms the walker
    # actually recovered BOTH stated numbers.
    r = solve(
        "Priya has 20 marbles. She lost 4 last week and 6 this week. "
        "How many marbles does Priya have left?",
        full_registry,
    )
    assert r.answer.kind == "decline"
    assert not r.answer.committed
    assert len(r.store.collisions) == 1
    collision = r.store.collisions[0]
    assert {collision.a_value, collision.b_value} == {4.0, 6.0}


def test_untagged_event_verb_bare_conjunct_still_declines(full_registry):
    # 'keep'/'keeps' carries no polarity category (deliberately, per
    # increment 11's own test) — the outer gate this walker shares with
    # `_conjoined_purchase_items` stays CLOSED, so the second bare number
    # is exactly as unaccounted as before this candidate.
    r = solve(
        "Priya keeps 5 apples last week and 3 this week. "
        "How many apples does Priya keep?",
        full_registry,
    )
    assert r.answer.kind == "decline"
    assert not [
        fact
        for fact in r.store.facts
        if getattr(fact, "verb", None) == "keep"
        and getattr(fact, "measure", None) == "apple"
    ]


def test_positive_more_conjunct_is_recovered_for_signed_event(full_registry):
    result = solve(
        "Bira collected 3 shells on Monday and 2 more on Tuesday. "
        "How many shells did Bira collect?",
        full_registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == 5


def test_state_verb_bare_conjunct_is_unaffected(full_registry):
    # A state verb ('have') is explicitly excluded (`not is_state`) — a
    # bare-number conjunct after a STATE verb's dobj must stay exactly as
    # unaccounted as it was before this candidate; the mechanism is scoped
    # to event verbs only, never widened to holdings.
    r = solve(
        "Priya has 5 last week and 3 this week. How many weeks does Priya have?",
        full_registry,
    )
    assert r.answer.kind == "decline"
    assert "stated count '3'" in r.answer.reason
    assert "reached no fact" in r.answer.reason


def test_genuine_noun_conjunct_is_not_double_processed(full_registry):
    # The SECOND conjunct here names its OWN real item ('buttons') — not a
    # bare elided number — so this walker's gate (every noun in the segment
    # must be a bare `timeperiod` member) correctly declines to touch it,
    # leaving the pre-existing noun-bearing conjunct recovery
    # (`_conjoined_purchase_items`) as the sole producer of that fact: one
    # clean Quantity(measure='button', value=3.0), never a duplicate.
    r = solve(
        "Priya has 20 marbles. She lost 4 last week and 3 buttons this week. "
        "How many marbles does Priya have left?",
        full_registry,
    )
    button_facts = [
        f
        for f in r.store.facts
        if getattr(f, "measure", None) == "button" and getattr(f, "value", None) == 3.0
    ]
    assert len(button_facts) == 1
