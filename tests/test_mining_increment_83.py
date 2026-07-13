"""Mining candidate conjoined-event-conjuncts: conjoined event-verb object
lists, where each conjunct is its own event bound to its own counted noun.

Increments 11/35/45/61 already recover a conjoined sibling item's own noun
(or, for increment 61, its elided bare value) for purchase/state/event
verbs — but every conjunct's Quantity fact keyed on
(entity, measure, verb, time, occurrence), and `occurrence` is the
SENTENCE index: two conjuncts of one sentence bound to the SAME
entity/measure ("sold 3 boxes to her aunt and 4 boxes to her uncle" — one
item noun repeated) collide at that identical key and BOTH quarantine as a
"fold and fold disagree" conflict, even though they are two genuine,
distinct events that should be SUMMED, not two disagreeing readings of one
holding.

Mechanism (two coordinated pieces):
1. `model.Quantity.segment` — a new, optional within-sentence CONJUNCT
   INDEX. NOT part of `key()` or `value_part()`: every fact predating this
   field is byte-identical. Stamped by learn.py's conjunct-recovery loops
   (1, 2, 3, ... for each conjunct after the first) only for NON-STATE,
   polarity-tagged verbs (`_has_event_polarity` — the category is the
   gate, no word list) whose dobj is not itself a `timeperiod`-category
   noun (a guard against a pre-existing, unrelated dobj mis-binding —
   see the "she lost 4 last week" test below). The first/only conjunct in
   a sentence always keeps `segment=None`.
2. `facts.FactStore.admit` — a FIFTH collision-time mirror (after the
   pre-existing owner/qualifier/measure_qualifier/label mirrors): when a
   same-key VALUE conflict's two Quantity facts carry different `segment`
   values (`None` reads as conjunct position 0 for this comparison only),
   both admit as-is with NO rename — downstream consumers (the Sigma-
   events fold) already iterate `store.by_kind(Quantity)` and filter by
   attribute, not by a unique key lookup, so summing needs no consumer
   change. This mirror is tried LAST so a genuinely qualifier-
   differentiated conjunct pair ("1 red hat" / "3 blue hats") still takes
   the pre-existing measure_qualifier path unchanged, keeping its paired
   Price facts (which carry no `segment`) in lockstep. It is also checked
   AHEAD of the ordinary same-VALUE agreement-dedupe, so a same-value
   conjunct pair ("4 marbles to his cousin ... 4 marbles to his
   neighbor") is never silently deduped into an undercount.

A collateral fix travels with the enabler: `saturate._rest_synth` computed
a "kept the rest" pool as the signed sum of STRICTLY EARLIER sentences —
sound when the depleting events are their own sentence, but a same-
sentence "gave X, gave Y, and kept the rest" (all one coordinated
sentence) has its depleting events invisible to that scan. Before this
candidate, such an item safely declined (its conjuncts quarantined at the
old fold collision); this candidate's conjunct fix would otherwise let it
resolve — and silently return the pool BEFORE the gifts, not the
remainder, a confident wrong. `_rest_synth` now declines whenever a
RestQuantity shares its own sentence with a non-state Quantity, keeping
this shape exactly as safe as it always was; a rewritten, later-sentence
"He kept the rest" is untouched and still resolves.

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


def test_two_conjuncts_same_measure_are_summed(full_registry):
    # "sold 3 boxes to her aunt and 4 boxes to her uncle" shape: both
    # conjuncts fold to the SAME bare entity/measure with no owner/
    # qualifier/label to split on — before this candidate this quarantined
    # as a fold/fold conflict; now the Sigma-events fold sums them.
    r = solve(
        "Kira sold 5 boxes to her cousin and 2 boxes to her neighbor. "
        "How many boxes did Kira sell?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 7


def test_three_conjuncts_same_measure_are_summed(full_registry):
    r = solve(
        "Nia sold 6 pencils to her cousin, 3 pencils to her neighbor "
        "and 2 pencils to her uncle. How many pencils did Nia sell?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 11


def test_same_value_conjuncts_are_not_undercounted(full_registry):
    # the trap explicitly named in the mining brief: relaxing the VALUE
    # collision check (rather than keying on conjunct POSITION) would let
    # two same-value conjuncts silently dedupe into one occurrence
    # (4 + 4 folding to 4 instead of 8). Both facts must survive and sum.
    r = solve(
        "Ravi gave 4 marbles to his cousin and 4 marbles to his neighbor. "
        "How many marbles did Ravi give?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 8


def test_untagged_event_verb_conjuncts_still_decline(full_registry):
    # 'keep'/'keeps' carries no polarity category (deliberately, per
    # increment 11's own test) — the conjunct-recovery gate this candidate
    # shares with increments 11/35/45/61 stays CLOSED, so the second
    # conjunct is exactly as unaccounted as it was before this candidate.
    r = solve(
        "Nia keeps 5 pencils on Monday and 3 pencils on Tuesday. "
        "How many pencils does Nia keep?",
        full_registry,
    )
    assert not r.answer.committed


def test_state_verb_same_key_conflict_still_quarantines(full_registry):
    # a STATE verb ('have') is explicitly excluded from segment
    # differentiation: a same-key value disagreement between two holdings
    # is a genuine conflict (contradictory statements), not a list of
    # distinct events to sum, and must keep quarantining unchanged.
    r = solve(
        "Kennedy has 12 apples and 9 apples. How many apples does "
        "Kennedy have?",
        full_registry,
    )
    assert not r.answer.committed
    assert r.store.collisions
    collision = r.store.collisions[0]
    assert {collision.a_value, collision.b_value} == {12.0, 9.0}


def test_timeperiod_misbound_dobj_conjuncts_still_quarantine(full_registry):
    # "lost 4 last week and 6 this week" — a pre-existing, unrelated
    # parse gap can bind a TIMEPERIOD noun ('week') as the counted dobj
    # instead of an elided real item. Inheriting that as a real item
    # measure would be unsound, so segment differentiation stays off for
    # this shape: the conjuncts keep colliding exactly as they did before
    # this candidate (decline-safe), rather than this candidate turning a
    # pre-existing mis-parse's safety-net collision into a confident
    # wrong.
    r = solve(
        "Farid has 15 buttons. He lost 3 last week and 5 this week. "
        "How many buttons does Farid have left?",
        full_registry,
    )
    assert not r.answer.committed


def test_qualified_conjuncts_still_take_the_measure_qualifier_path(full_registry):
    # a genuinely qualifier-differentiated conjunct pair ("1 red hat" /
    # "3 blue hats") must still resolve via the pre-existing
    # measure_qualifier collision mirror (mining candidate
    # qualified-measure-keys), unaffected by the new segment mirror being
    # tried after it — otherwise the paired Price facts (which carry no
    # `segment`) would fall out of lockstep with their Quantity facts.
    r = solve(
        "Theo buys one red hat for $12 and three blue hats at $5 each. "
        "How much does Theo spend in total?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 27


def test_same_sentence_rest_of_conjoined_events_declines_not_wrong(full_registry):
    # the collateral saturate.py fix: "gave X, gave Y, and kept the rest"
    # packed into ONE coordinated sentence. Before this candidate the
    # conjoined gifts quarantined outright (safe decline via the fold
    # conflict this candidate removes); after the conjunct fix alone, the
    # gifts would cleanly resolve but `_rest_synth`'s pool-before-sentence
    # scan cannot see them (they share ITS OWN sentence) and would
    # silently return the pool BEFORE the gifts (30, not the remainder,
    # 14) — a confident wrong. The same-sentence guard keeps this shape
    # declining instead.
    r = solve(
        "Malik had 30 pencils. He gave six pencils to his brother, "
        "ten pencils to his sister, and he kept the rest. "
        "How many pencils did Malik keep?",
        full_registry,
    )
    assert not r.answer.committed
    assert r.answer.value != 30


def test_rewritten_later_sentence_rest_still_resolves(full_registry):
    # the mirror-image check for the saturate.py guard: when the "kept
    # the rest" clause is genuinely in a LATER sentence than the events
    # depleting the pool, `_pool_before`'s prior-sentence scan sees them
    # exactly as before this candidate, and the answer still resolves.
    r = solve(
        "Malik had 30 pencils. He gave six pencils to his brother and "
        "ten pencils to his sister. He kept the rest. "
        "How many pencils did Malik keep?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 14
