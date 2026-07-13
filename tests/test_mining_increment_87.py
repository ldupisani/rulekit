"""Mining candidate elided-measure-anchors: a bare numeral stated for an
entity whose MEASURE NOUN is dropped entirely ("who caught 2", "if Kristen
has 12", "Ben has 9") — the premise-side sibling of increment 85's elided-
measure RELATIONS. learn.py's generic SVO fold always needed a counted NOUN
dobj to build a Quantity; a noun-less bare count had nowhere to go and fell
all the way to a valueless Predication (dobj holding the numeral's own
surface) that no downstream consumer could ever anchor a relation chain, a
combined total, or an ordinary "how many" ask on.

Mechanism: a NEW fact kind, `AnchorQuantity` (model.py) — deliberately
NOT a nullable `measure` field on Quantity itself (Quantity is the single
most-consumed fact kind in the engine; a `measure=None` sentinel sitting
among ~30 call sites that build bare `{q.measure for q in ...}` sets would
silently pollute every one of them). learn.py emits it whenever a state or
event verb's dobj resolves to a bare count value with no noun at all
(instead of the old Predication fallback). saturate.py's
`_anchor_quantity_synth` resolves it into a real Quantity by recovering the
measure from the UNIQUE measure already in play for that entity — a
sibling Relation naming the entity as its subject/standard, or the
entity's own other stated Quantity — the same unique-pool-in-play
discipline `_relations_synth` (increment 85) already applies to elided-
measure Relations. Zero or two-or-more candidates is ambiguous and
declines, never a guess. guards.py's `unresolved-derivation` guard vetoes
any commit where an AnchorQuantity never resolved, exactly like
Fraction/RestQuantity. Synthetic only — every name, number, and object
below is invented from scratch, none drawn from any benchmark item."""

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


def test_relative_clause_anchor_feeds_a_relation_chain(full_registry):
    # "Ola who caught 4" — the relative clause states Ola's own bare count
    # with no measure noun at all; the relation's OWN clause already spells
    # the measure ("as many FISH as Ola"), so the anchor recovers 'fish'
    # from that sibling relation and the chain multiplies through normally.
    r = solve(
        "Mia catches three times as many fish as Ola who caught 4. "
        "How many fish did Mia catch?",
        full_registry,
    )
    assert r.answer.value == 12.0


def test_trailing_conditional_anchor_feeds_a_difference_ask(full_registry):
    # "if Ruth has 6?" — a trailing conditional clause (split into its own
    # premise by the pre-existing leading/trailing-clause machinery) states
    # a bare count with no measure noun; the sibling relation's own spelled
    # measure ('coins') resolves the anchor, and the existing comparative
    # (|a - b|) consumer finishes it unchanged.
    r = solve(
        "Vance has 5 times as many coins as Ruth. "
        "How many more coins does Vance have than Ruth, if Ruth has 6?",
        full_registry,
    )
    assert r.answer.value == 24.0


def test_bare_event_anchor_inherits_the_only_measure_in_play(full_registry):
    # "She loses 4." — a bare-count EVENT clause with no item noun at all;
    # the only other measure known for the same entity ('button', from the
    # earlier purchase) is unique, so the anchor recovers it and the
    # ordinary signed fold subtracts the loss.
    r = solve(
        "Nora buys 3 dozen buttons. She loses 4. "
        "How many buttons does Nora have left?",
        full_registry,
    )
    assert r.answer.value == 32.0


def test_ambiguous_anchor_measure_declines(full_registry):
    # Priya holds a measure of her own ('marble') AND is the standard of a
    # relation naming a DIFFERENT spelled measure ('pen') — two candidate
    # measures for the SAME bare-count anchor ("who owns 6") is ambiguous,
    # so the anchor must decline rather than guess.
    r = solve(
        "Priya has 6 marbles. Wren collects twice as many pens as Priya, "
        "who owns 6. How many pens does Wren collect?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_unanchored_bare_count_declines(full_registry):
    # Xavier states a bare count with NO other quantity or relation
    # anywhere in the document to recover a measure from — zero
    # candidates, so the anchor stays unresolved and the ask (needing a
    # known 'apple' quantity for Xavier) declines rather than commit.
    r = solve(
        "Xavier has 6. How many apples does Xavier have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_negated_bare_count_never_becomes_a_holding(full_registry):
    # "She does not have 6." — a negated clause must not fold into an
    # AnchorQuantity at all (a phantom second holding of 'marble' for the
    # same entity would either silently overwrite the real count or
    # collide); the item declines on ordinary value-accounting (the
    # negated '6' reaches no fact) rather than committing around it —
    # the SAME decline reason a spelled-measure negated clause already got
    # before this candidate existed.
    r = solve(
        "Rosa has 10 marbles. She does not have 6. "
        "How many marbles does Rosa have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_spelled_measure_sibling_still_wins_when_a_noun_is_stated(full_registry):
    # an ordinary counted-noun dobj ("6 apples") must be completely
    # unaffected by this candidate — it still folds through the existing
    # dobj_is_count path to a plain Quantity, never through AnchorQuantity.
    r = solve(
        "Xavier has 6 apples. How many apples does Xavier have?",
        full_registry,
    )
    assert r.answer.value == 6.0
