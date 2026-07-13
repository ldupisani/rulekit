"""Mining increment 84: partitive-measure asks
("how many MEASURE of SUBSTANCE ...") — the `item` slot on an entity-less
"there"/"left" ask (and its totality-marked "combined" sibling) could not
consume a partitive tail at all, so any question phrasing the measure
through "MEASURE of SUBSTANCE" ("how many kilograms of meat are left?")
failed EVERY ask's match and declined with "no ask shape recognizes this
question" — before the premises, the fold, or any consumer was ever
consulted. Synthetic only.

Mechanism (two coordinated pieces, no new slot TYPE — reuses the existing
`opt` sub-sequence machinery already precedented by
ask/how-many-of-collection-are-label):

1. packs/arithmetic/rules/core.yaml — ask/how-many-there,
   ask/how-many-left-entityless and ask/how-many-there-combined each gain
   an optional `[{lit: of}, {slot: substance, type: noun}]` group right
   after their existing `item` slot. `item` still binds ONLY the bare
   measure noun ('kilogram') exactly as every existing bare-measure ask
   already does — the group exists purely so the trailing "of SUBSTANCE"
   NP is CONSUMED instead of breaking the match (SKIPPABLE_SENSES already
   auto-skips any article between 'of' and the substance noun, so no
   separate article token is needed). `ask/how-many-entity` (the single-
   entity "does WHO have" form) deliberately did NOT get this group — see
   its own comment in core.yaml for the confident-wrong that ruled it out.

2. learn.py's new `_measure_substance` (a structural mirror of the
   pre-existing `_measure_partitive_anchor`, walking the SAME `partitive`-
   category preposition's anchor/object obligations in the opposite
   direction) feeds the EXISTING `measure_qualifier` field — reused
   unchanged from mining candidate qualified-measure-keys, the SAME field
   an adjective-qualified measure ("12 white marbles") already populates —
   as a fallback at every `_qualifier(dobj)`/`_qualifier(item)` call site.
   answer.py's new `_measure_substance_guard`, wired into the
   `unique-entity` and `combined` (via `_combined_holder_totals`)
   consumers ONLY when the ask actually bound a `measure_substance` query
   field, scans the candidate Quantity facts for
   DISTINCT `measure_qualifier` values: more than one attested substance,
   or exactly one that disagrees with what was ASKED, declines rather than
   silently summing across substances (the sibling-borrow wrong the brief
   named as the central hazard). Zero distinct substances (the
   overwhelming existing case — no partitive tail anywhere) is a no-op,
   so every pre-existing bare-measure ask is byte-behaviorally unchanged.
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


def test_partitive_left_entityless_resolves(full_registry):
    # ask/how-many-left-entityless: a single holder's state anchor plus one
    # signed event, keyed on the bare measure noun ('liter'); the partitive
    # tail ('of oil') only reaches the SAME pre-existing unique-entity fold.
    r = solve(
        "Derek had 40 liters of oil. He used 15 liters of oil. "
        "How many liters of oil are left?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 25


def test_partitive_there_resolves(full_registry):
    # ask/how-many-there: single state holding, entity-less partitive ask.
    r = solve(
        "Priya has 9 bottles of oil. How many bottles of oil are there?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 9


def test_partitive_there_combined_resolves(full_registry):
    # ask/how-many-there-combined: two named holders, totality marker
    # required — routes to the SAME 'combined' consumer every other
    # totality-marked entity-less ask already uses.
    r = solve(
        "Farah has 6 sacks of flour. Idris has 9 sacks of flour. "
        "How many sacks of flour are there in total?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 15


def test_ambiguous_substances_decline_not_wrong(full_registry):
    # THE gate: two DIFFERENT substances share the same measure noun
    # ('bottle') via two EVENT quantities in different sentences (so they
    # never collide at the same fact-store key and stay bare-measure
    # 'bottle' — the exact case facts.py's own collision-time re-key can
    # never see). Without the guard the naive fold would sum BOTH (9 + 5 =
    # 14) regardless of which substance was asked — a confident wrong. With
    # it, the ask declines instead of borrowing the 'oil' quantity to
    # answer a 'sugar' question.
    r = solve(
        "Priya bought 9 bottles of oil. Priya bought 5 bottles of sugar. "
        "How many bottles of sugar are there?",
        full_registry,
    )
    assert not r.answer.committed
    assert "more than one substance" in r.answer.reason


def test_unattested_substance_declines(full_registry):
    # exactly one substance is attested for the measure ('oil') and it
    # does not match what was asked ('sugar') — zero facts about the asked
    # substance exist, so this declines too, never silently answers from
    # the unrelated substance's quantity.
    r = solve(
        "Priya has 9 bottles of oil. How many bottles of sugar are there?",
        full_registry,
    )
    assert not r.answer.committed


def test_same_substance_repeated_still_sums(full_registry):
    # decline-safety in the OTHER direction: every mention agrees with the
    # asked substance, so the guard is a no-op and the two events still
    # sum exactly as an ordinary bare-measure ask always has.
    r = solve(
        "Priya bought 9 bottles of oil. Priya bought 5 bottles of oil. "
        "How many bottles of oil are there?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 14


def test_single_entity_ask_scope_unchanged(full_registry):
    # ask/how-many-entity deliberately did NOT get the partitive tail (see
    # its own core.yaml comment for the confident-wrong that ruled it out)
    # — a partitive-measure question in the "does WHO have" shape must
    # still decline exactly as before this candidate.
    r = solve(
        "Tom has 8 kilograms of rice. How many kilograms of rice does Tom have?",
        full_registry,
    )
    assert not r.answer.committed


def test_bare_measure_ask_is_unaffected(full_registry):
    # no-regression: an ordinary bare-measure entity-less ask, no partitive
    # tail anywhere in question or premises, must resolve exactly as
    # before this candidate — `measure_substance` never binds, so
    # `_measure_substance_guard` is never even called.
    r = solve(
        "Owen has 7 shells. How many shells are there?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 7
