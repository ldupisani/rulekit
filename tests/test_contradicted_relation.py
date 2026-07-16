"""An over-determined document that does not add up is not read.

A Relation whose subject AND standard BOTH already hold a stated state is
redundant — the document says the same thing twice. saturate.py DROPS it
silently ("only an existing STATE for the subject blocks resolution"), which is
right for a CONSISTENT restatement and hides a CONTRADICTION: "London is 11 and
Blair is 16. SEVERAL YEARS AGO, Blair was twice as old as London" committed
London's current 11, because 16 != 2*11 was never checked against anything.

The contradiction is real and its cause is temporal — the relation holds at some
other time, and 'several years ago' is an offset no rule can capture (it is not
a number). With no time model the engine cannot tell "inconsistent document"
from "relation at another time", and both mean it has not read what the question
turns on. So it declines.

TWO CONDITIONS, and dropping EITHER breaks correct items. Both were measured
across all five word-problem corpora before the guard was written, and with both
in place the class is EXACTLY ONE item in five corpora — the confident-wrong this
exists for. The three tests below pin the families that must survive; they are
not decoration, they are the two conditions.

Synthetic only — invented fixtures; the SHAPE is what is pinned.
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


def test_a_same_time_contradiction_declines(full_registry):
    """The regression: two stated ages and a relation that cannot hold at the
    same time as both of them. 16 != 2 * 11."""
    r = solve(
        "Ivo is 11 years old and Rune is 16 years old. "
        "Several years ago, Rune was twice as old as Ivo. How old was Ivo then?",
        full_registry,
    )
    assert r.answer.kind == "decline"
    assert "contradicted-relation" in r.answer.reason


def test_a_consistent_restatement_still_answers(full_registry):
    """A redundant-but-TRUE relation is not a contradiction. If this declines,
    the guard is firing on agreement, which would gut the whole relation family."""
    r = solve(
        "Ivo is 11 years old and Rune is 22 years old. "
        "Rune is twice as old as Ivo. How old is Rune?",
        full_registry,
    )
    assert (r.answer.kind, r.answer.value) == ("number", 22.0)


def test_a_relation_at_ANOTHER_time_still_answers(full_registry):
    """CONDITION 1 — `subject_offset`/`standard_offset`. "In 5 years, X will be
    4 times as old as Y" is VIOLATED at t=0 BY DESIGN and answered correctly
    today. Ignoring the offsets flags every member of this family (12 across
    gsm8k dev, 4 known correct) — measured before the guard was written."""
    r = solve(
        "In 5 years, Rune will be 4 times as old as Ivo. "
        "If Ivo is currently 10 years old, how old is Rune?",
        full_registry,
    )
    assert (r.answer.kind, r.answer.value) == ("number", 55.0)


def test_labeled_holders_are_not_read_as_one_entity(full_registry):
    """CONDITION 2 — LABEL-KEYED lookup. Three jars bare-fold to lemma 'jar', so
    a bare-lemma comparison reads them as one entity and sees a contradiction
    that is not there (2 more correct items). The label lives in a separate
    feature — the same trap `distinct: [who, std]` documents, and it caught my
    measurement script before it caught the guard."""
    r = solve(
        "Jar A has 28 marbles. Jar B has 12 more marbles than jar A. "
        "Jar C has twice as many marbles as jar B. How many marbles are in jar C?",
        full_registry,
    )
    assert (r.answer.kind, r.answer.value) == ("number", 80.0)


def test_a_derivable_relation_is_untouched(full_registry):
    """NOT over-determined: only the standard is stated, so saturate DERIVES the
    subject. The guard must never reach a relation that is doing real work."""
    r = solve(
        "Ivo is 11 years old. Rune is twice as old as Ivo. How old is Rune?",
        full_registry,
    )
    assert (r.answer.kind, r.answer.value) == ("number", 22.0)
