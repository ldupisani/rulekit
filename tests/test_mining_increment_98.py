"""Mining increment 98: elided-comparative-standards: a multiplicative/fraction
comparative ("K times as many/much ITEM", "half as many/much ITEM") whose
STANDARD clause is elided entirely -- no "as Y" names the comparison entity
anywhere in the sentence. New sibling pattern rules (packs/arithmetic/rules/
core.yaml: arithmetic/times-as-many-elided-standard, times-as-much-elided-
standard, fraction-as-many-elided-standard, fraction-as-much-elided-standard)
emit the ordinary Relation shape with `standard` set to a reserved
`$elided:standard$` sentinel; saturate.py's `_relations_synth` recovers the
antecedent structurally -- the unique OTHER entity holding the SAME measure
in an EARLIER sentence, the same unique-pool-in-play, never-guess discipline
used throughout this file. Zero or two-or-more same-measure holders declines
rather than guessing. A repeated self-mention (no demonstrative) is excluded
from the antecedent search entirely -- that is arithmetic/anaphoric-
multiplier-standard's own shape ("twice THAT many"), not this one. Each new
rule's own `where: unbound: [std_seen]` guard rejects the whole match
whenever a trailing "as Y" continuation is grammatically present at all,
even when the sibling (mandatory-standard) rule declines that continuation
for some unrelated reason -- so this rule never mistakes a truncated prefix
of a longer, still-explicit comparative for a genuinely elided one.

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


def test_cross_sentence_elided_standard_times_as_many(full_registry):
    # the second sentence never names a standard at all; the antecedent is
    # the unique earlier same-measure holder ("Priya", 6 marbles)
    r = solve(
        "Priya has 6 marbles. Oscar has four times as many marbles in his "
        "bag. How many marbles does Oscar have?",
        full_registry,
    )
    assert r.answer.value == 24


def test_cross_sentence_elided_standard_times_as_much(full_registry):
    r = solve(
        "Deepa has 9 rice. Farid has twice as much rice. How much rice "
        "does Farid have?",
        full_registry,
    )
    assert r.answer.value == 18


def test_cross_sentence_elided_standard_fraction_as_many(full_registry):
    r = solve(
        "Vikram has 20 seashells. Noor has half as many seashells. How many "
        "seashells does Noor have?",
        full_registry,
    )
    assert r.answer.value == 10.0


def test_ambiguous_same_measure_antecedent_declines(full_registry):
    # TWO earlier holders of the same measure -- the antecedent is genuinely
    # ambiguous, must decline rather than guess which one is meant
    r = solve(
        "Priya has 6 marbles. Talia has 9 marbles. Oscar has four times as "
        "many marbles. How many marbles does Oscar have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_self_mention_excluded_from_antecedent_search(full_registry):
    # a bare repeat of the subject's own name (no "that"/"this" -- that is
    # arithmetic/anaphoric-multiplier-standard's shape, not this one) must
    # NEVER let the antecedent search treat the subject's own earlier value
    # as the standard and multiply it by itself: the relation must produce
    # no derived Quantity at all here, from either the resolved-standard or
    # same-holder-subtype branches. (The overall answer still falls back to
    # the stale pre-existing fold value, 6 -- the SAME pre-existing, already
    # -shipped tradeoff arithmetic/anaphoric-multiplier-standard-many itself
    # exhibits for the identical self-mention shape with a demonstrative
    # ["Oscar has four times THAT many marbles"], verified unaffected by
    # this candidate; not a regression this candidate introduces or owns.)
    from rulekit.kernel.model import Quantity

    r = solve(
        "Oscar has 6 marbles. Oscar has four times as many marbles. How "
        "many marbles does Oscar have now?",
        full_registry,
    )
    derived = [
        q for q in r.store.by_kind(Quantity)
        if q.provenance.source == "synth/relation"
    ]
    assert derived == []


def test_explicit_standard_still_resolves_unaffected(full_registry):
    # the ordinary, fully-explicit form must keep working byte-for-byte --
    # the new sibling rule's own where-guard rejects its truncated match
    # whenever "as Y" is present, leaving the existing rule as the sole
    # resolver exactly as before this candidate existed
    r = solve(
        "Priya has 6 marbles. Oscar has four times as many marbles as "
        "Priya. How many marbles does Oscar have?",
        full_registry,
    )
    assert r.answer.value == 24


def test_qualifier_collision_still_declines_not_wrong(full_registry):
    # "K times as many QUALIFIED-X as OTHER-QUALIFIED-X" -- the standard IS
    # named in the text ("red marbles"), so this must NOT be read as an
    # elided-standard shape at all; the whole clause stays declined exactly
    # as it did before this candidate existed (a pre-existing, separate gap
    # in the qualifier-awareness of the mandatory-standard sibling, not
    # something this candidate may paper over with a guess)
    r = solve(
        "Wanjiru has 10 blue marbles. She has 9 fewer green marbles than "
        "blue marbles. She has 4 times as many red marbles as green "
        "marbles. How many marbles does Wanjiru have in all?",
        full_registry,
    )
    assert r.answer.kind == "decline"
