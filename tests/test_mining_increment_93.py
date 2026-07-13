"""mining candidate cross-measure-relation-fixes: same-holder cross-measure
relations reached through three surface widenings, all layered on top of
increment 78's existing same-holder subtype-anchor branch in saturate.py's
`_relations_synth`:

(1) a locative prepositional phrase interrupting the measure noun and the
    'as'/'than' that introduces the standard ("twice as many WIDGETS IN THE
    CRATE as GADGETS") — every relation rule whose measure noun sits
    directly before that literal gains a skippable
    `{prep} {det?} {noun}` prefix (packs/arithmetic/rules/core.yaml).
(2) a conjoined trailing clause restating the standard's own quantity
    ("... N more WIDGETS than GADGETS and currently has M GADGETS") — a new
    rule, `arithmetic/anchored-relation-conjoined-anchor`, matches the
    whole sentence and emits both the Relation and a same-holder Quantity
    for the standard.
(3) INVERSE same-holder subtype resolution in saturate.py: when the
    relation's OWN measure is already known for the subject but its
    STANDARD (a subtype, not a separate holder) is not, solve
    standard = (subject - offset) / factor, guarded by `is_subtype_standard`
    so an ordinary cross-entity relation (a standard shared by two
    different subjects, or a labeled standard, or a bare name) is never
    misread as a subtype.

Synthetic only — every name, noun, and number below is invented; none is
copied or paraphrased from any GSM8K item.
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


# -- (1) PP-interrupted measure NP --------------------------------------------


def test_pp_interrupted_times_as_many(full_registry):
    r = solve(
        "Priya has twice as many stickers in her binder as buttons. "
        "She has 9 buttons. How many stickers does Priya have?",
        full_registry,
    )
    assert r.answer.value == 18


def test_pp_interrupted_matches_plain_form_identically(full_registry):
    # the no-PP case must stay byte-identical: same numbers, same answer
    plain = solve(
        "Priya has twice as many stickers as buttons. "
        "She has 9 buttons. How many stickers does Priya have?",
        full_registry,
    )
    pp = solve(
        "Priya has twice as many stickers in her binder as buttons. "
        "She has 9 buttons. How many stickers does Priya have?",
        full_registry,
    )
    assert plain.answer.value == pp.answer.value == 18


# -- (2) conjoined-clause trailing anchor -------------------------------------


def test_conjoined_trailing_anchor_quantity(full_registry):
    r = solve(
        "Marcus has 3 more ribbons than candles and currently has 7 candles. "
        "How many ribbons does Marcus have?",
        full_registry,
    )
    assert r.answer.value == 10


def test_conjoined_trailing_anchor_without_adverb(full_registry):
    r = solve(
        "Dana has 8 birthday cows. Dana has 3 more ribbons than candles and has "
        "7 candles. How many ribbons does Dana have?",
        full_registry,
    )
    assert r.answer.value == 10


def test_conjoined_trailing_anchor_declines_on_mismatched_noun(full_registry):
    # the trailing clause restates a DIFFERENT noun than the relation's own
    # standard -- the repeated-lemma check must block this, not mis-anchor
    r = solve(
        "Marcus has 3 more ribbons than candles and currently has 7 baskets. "
        "How many ribbons does Marcus have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


# -- (3) same-holder subtype INVERSE ------------------------------------------


def test_same_holder_subtype_inverse(full_registry):
    r = solve(
        "Oskar has 8 crayons. He has 3 times as many badges as crayons. "
        "He has 4 times as many badges as stamps. How many stamps does Oskar have?",
        full_registry,
    )
    assert r.answer.value == 6


def test_cross_entity_inverse_still_resolves(full_registry):
    # decline-safety / no-regression: an ORDINARY cross-entity relation
    # (a real second holder, not a subtype) must still resolve via the
    # pre-existing cross-entity inverse branch, unaffected by the new
    # same-holder gate.
    r = solve(
        "Petra has three times as many seashells as Ollie. Petra has 21 "
        "seashells. How many seashells does Ollie have?",
        full_registry,
    )
    assert r.answer.value == 7


def test_shared_standard_across_subjects_stays_cross_entity(full_registry):
    # 'wanda' is compared against by TWO different subjects (Karl and
    # Renata) -- a shared third-party holder, never a same-holder subtype
    # of either one -- so the ordinary cross-entity path (not the new
    # subtype-inverse branch) must be what resolves this, and it must
    # still land on the right entity.
    r = solve(
        "Karl has 4 more kites than Wanda. Renata has twice as many kites as "
        "Wanda. If Renata has 10 kites, how many kites does Karl have?",
        full_registry,
    )
    assert r.answer.value == 9


def test_labeled_standard_stays_cross_entity(full_registry):
    # a labeled standard ("Box A") is always a genuine distinguishable
    # holder -- the same-holder subtype branch must never claim it, so the
    # combined total across both boxes must still fold correctly.
    r = solve(
        "Box A has 15 marbles. Box B has 5 more marbles than box A. "
        "How many marbles are there in total?",
        full_registry,
    )
    assert r.answer.value == 35
