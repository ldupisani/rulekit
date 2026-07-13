"""Increment 99 — a relation anchors on the standard's FULL TOTAL, not its state fact.

THE BUG (a CONFIDENT WRONG, live on main until this increment). `_relations_synth`
resolved a same-holder subtype relation by reading a single raw Quantity's `.value`
— the STATE fact — and silently ignored any later EVENT on the same
(subject, standard) pair:

    "Sam has 2 dogs. Sam buys 4 dogs. Sam has three times as many cats as dogs."
      -> anchored on 2, committed 3 x 2 = 6.   The truth is 3 x (2+4) = 18.

Not a decline. A wrong answer, confidently given — the one thing the constitution
ranks worse than everything else (rule 4).

THE FIX: route the anchor through `_entity_total`, the exact same fold the
single-entity ASK consumer already uses, so a relation's notion of "how much X has"
agrees with the engine's everywhere else. It is strictly MORE conservative than the
raw peek — `_entity_total` returns None on ambiguity it cannot safely resolve, and we
decline rather than commit a stale anchor.

Found by the failed `existential-relation-binding` candidate (batch 43), which could
not crack its own target item but proved this fix out on the way. Synthetic strings
only (NEVER benchmark items).
"""

import pytest

from rulekit.kernel.engine import solve


def _value(text, registry):
    return solve(text, registry).answer.value


def test_relation_anchors_on_the_total_after_an_acquire_event(registry):
    """THE BUG. Anchoring on the state fact (2) instead of the total (6) gave 6, not 18."""
    text = (
        "Sam has 2 dogs. Sam buys 4 dogs. "
        "Sam has three times as many cats as dogs. How many cats does Sam have?"
    )
    assert _value(text, registry) == 18


def test_relation_anchors_on_the_total_after_a_lose_event(registry):
    """The same fold must subtract, not just add."""
    text = (
        "Sam has 10 dogs. Sam sold 4 dogs. "
        "Sam has two times as many cats as dogs. How many cats does Sam have?"
    )
    assert _value(text, registry) == 12


def test_relation_anchors_on_the_total_across_several_events(registry):
    text = (
        "Sam has 5 dogs. Sam buys 3 dogs. Sam sold 2 dogs. "
        "Sam has four times as many cats as dogs. How many cats does Sam have?"
    )
    assert _value(text, registry) == 24


def test_a_pure_state_anchor_is_unchanged(registry):
    """No events -> `_entity_total` returns exactly what the raw lookup always did.

    This is the regression guard for every relation that already worked: the
    overwhelming majority have no event on the standard, and they must be untouched.
    """
    text = "Sam has 6 dogs. Sam has three times as many cats as dogs. How many cats does Sam have?"
    assert _value(text, registry) == 18


def test_offset_relations_use_the_total_too(registry):
    """'more than' relations anchor the same way."""
    text = (
        "Sam has 4 dogs. Sam buys 3 dogs. "
        "Sam has 5 more cats than dogs. How many cats does Sam have?"
    )
    assert _value(text, registry) == 12


def test_a_standard_with_no_quantity_at_all_declines(registry):
    """No anchor to total -> decline. `_entity_total` returning None must not commit."""
    result = solve(
        "Sam has three times as many cats as dogs. How many cats does Sam have?", registry
    )
    assert result.answer.kind != "number", "committed a relation with no anchor at all"
