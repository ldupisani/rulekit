"""Mining increment 85: elided-measure-relations — comparative/multiplicative
relations whose MEASURE NOUN is elided ("3 more than Tom", "twice as much
as Cecil", "half as many as Ann") — every downstream consumer (the
single-entity fold, the combined-total ask, the comparative consumer) is
already built and already correct once a Relation fact exists; the gap was
that the relation pattern rules required the measure noun INSIDE the
comparative NP, so an elided measure emitted nothing at all. Six new
pattern rules (packs/arithmetic/rules/core.yaml) emit the SAME Relation
fact shape as their spelled-measure siblings but with `measure: null` — an
explicit UNRESOLVED sentinel, never a guess. saturate.py's
`_relations_synth` recovers the sentinel from the STANDARD entity's own
unique in-play quantity (the same unique-pool-in-play discipline
synth/fraction-of-pool and synth/partition-of-collection already use):
exactly one measure known for the standard resolves; zero or two-or-more
(ambiguous) declines the relation for that round, never guesses. Scoped to
a NAMED standard only ("than Tom", "as Cecil") — a relation whose standard
is ALSO elided is out of scope for this increment. Synthetic only."""

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


def test_additive_elided_relation(full_registry):
    # "5 more than Ben" — no item noun at all between the delta word and
    # 'than'; the measure recovers from Ben's own stated 'apple' holding.
    r = solve(
        "Ben has 30 apples. Ann has 5 more than Ben. How many apples does Ann have?",
        full_registry,
    )
    assert r.answer.value == 35


def test_additive_elided_relation_chains_over_rounds(full_registry):
    # a chained pair of elided relations (Dana's standard is Cara, whose
    # own quantity is stated; Ella's standard is Dana, whose quantity is
    # only DERIVED by the first relation) — resolves over successive
    # fixpoint rounds with no extra machinery.
    r = solve(
        "Cara has 12 pencils. Dana has 3 fewer than Cara. "
        "Ella has 2 more than Dana. How many pencils does Ella have?",
        full_registry,
    )
    assert r.answer.value == 11


def test_times_as_many_elided_relation(full_registry):
    # "twice as many as Fay" — no plural item noun between 'many' and 'as'.
    r = solve(
        "Fay has 8 kites. Gus has twice as many as Fay. How many kites does Gus have?",
        full_registry,
    )
    assert r.answer.value == 16


def test_times_as_much_elided_relation(full_registry):
    # "three times as much as Hank" — no mass-noun item between 'much' and
    # 'as'; the measure recovers from Hank's own 'dollar' holding.
    r = solve(
        "Hank has 20 dollars. Ivy has three times as much as Hank. "
        "How much money does Ivy have?",
        full_registry,
    )
    assert r.answer.value == 60


def test_fraction_as_many_elided_relation(full_registry):
    # "half as many as Jill" — no plural item noun.
    r = solve(
        "Jill has 12 marbles. Kyle has half as many as Jill. "
        "How many marbles does Kyle have?",
        full_registry,
    )
    assert r.answer.value == 6


def test_fraction_as_much_elided_relation(full_registry):
    # "half as much as Liam" — no mass-noun item.
    r = solve(
        "Liam has 40 dollars. Mona has half as much as Liam. "
        "How much money does Mona have?",
        full_registry,
    )
    assert r.answer.value == 20


def test_fraction_delta_relation_elided(full_registry):
    # "20 percent more than Nora" — no item noun between the delta word and
    # 'than'.
    r = solve(
        "Nora has 50 stickers. Omar has 20 percent more than Nora. "
        "How many stickers does Omar have?",
        full_registry,
    )
    assert r.answer.value == 60


def test_ambiguous_standard_measure_declines(full_registry):
    # Paul holds TWO measures (apple, orange) — the standard's own
    # in-play quantity is not unique, so the elided relation must decline
    # rather than guess which measure "twice as many" refers to.
    r = solve(
        "Paul has 10 apples and 4 oranges. Quinn has twice as many as Paul. "
        "How many apples does Quinn have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_unknown_standard_measure_declines(full_registry):
    # Vic holds no stated quantity at all — the elided relation has
    # nothing to recover the measure from, so it must decline rather than
    # silently drop the clause.
    r = solve(
        "Uma has 5 more than Vic. How many pens does Uma have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_spelled_measure_sibling_still_wins_when_item_is_stated(full_registry):
    # the elided rule's sequence requires 'than'/'as' IMMEDIATELY after the
    # delta/quantity word — when the item noun IS present, only the
    # spelled-measure sibling rule's sequence can match at all, so ordinary
    # spelled-measure relations are completely unaffected by this increment.
    r = solve(
        "Ben has 30 apples. Ann has 5 more apples than Ben. How many apples does Ann have?",
        full_registry,
    )
    assert r.answer.value == 35
