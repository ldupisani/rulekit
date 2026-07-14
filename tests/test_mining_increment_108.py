"""Mining candidate conjunct-comparative-quantities: a later conjunct of a
verb's object list states "K times as many/much Z (as STANDARD)" — a shape
the general verb->dobj binding cannot reach at all (it only ever captures
the FIRST conjunct; increment 11/35 closed the same gap for purchase/state
BARE-NOUN second conjuncts only, never a comparative one), bundled with a
new bare-common-noun holder ask.

Two coordinated mechanisms:

1. Four premise rules (packs/arithmetic/rules/core.yaml) matching the
   WHOLE conjoined clause structurally, exactly like arithmetic/anchored-
   relation-conjoined-anchor already does for a relation-bearing trailing
   clause:
   - `arithmetic/times-as-many-conjunct`: "N item1 and K times as many
     item2 as STD" — emits item1's own Quantity plus an ordinary Relation
     for item2 (ties into the pre-existing relations synthesizer).
   - `arithmetic/times-as-many-conjunct-elided-standard`: "N item1 and K
     times as many item2" (no "as STD" continuation) — the standard is the
     immediately preceding conjunct's own quantity, so item2's Quantity is
     computed DIRECTLY (`k * item1`), no Relation needed.
   - `arithmetic/times-as-many-conjunct-elided-item`: "N item1 and K times
     as many" (item noun elided too) — same-measure Quantity, computed
     directly.
   - `arithmetic/anaphoric-multiplier-conjunct-many`: "N item1 and K times
     this/that many" (the demonstrative-anaphor idiom, no 'as' at all) —
     same-measure Quantity, computed directly.
   Because the match necessarily spans the verb and the first conjunct's
   own object, `pattern_consumed` (document.py) marks them consumed and the
   general fold (learn.py) skips this verb entirely — every rule above
   re-emits the first conjunct's own Quantity so nothing is lost. When the
   second conjunct's measure bare-folds to the SAME (measure,
   measure_qualifier) pair as the first (a genuine restatement, "20 parts
   ... twice as many parts"), the second fact carries `segment: 1`
   (model.py's within-sentence conjunct index, the same increment 11/35
   "conjoined-event-conjuncts" mirror) so facts.py admits both instead of
   quarantining a same-key collision — the ordinary single-entity fold
   then sums them.

2. A new bare-common-noun ask, `ask/how-many-entity-common-noun`
   (packs/arithmetic/rules/core.yaml), built on a new disjoint slot type
   `common_noun` (src/rulekit/data/schemas.py SLOT_TYPES, gated in
   src/rulekit/kernel/patterns.py's `_slot_ok`): sense noun, no `owner`
   feature, no `qualifier` feature, singular only. Structurally disjoint
   from `possessed`/`qualified`/`name`, so it can never tie-break collide
   with ask/how-many-entity-possessed or ask/how-many-entity-qualified the
   way widening `who` on ask/how-many-entity itself already tried and
   reverted (see that ask's own comment).

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


def test_cross_measure_conjunct_common_noun_holder(full_registry):
    # arithmetic/times-as-many-conjunct-elided-standard + the new bare
    # common-noun ask: a plain, unqualified holder ("the store"), item2
    # names its OWN (different-lemma) measure.
    r = solve(
        "The store has 20 large boxes and twice as many small boxes. "
        "How many boxes does the store have?",
        full_registry,
    )
    assert r.answer.value == 60


def test_qualified_variants_of_one_measure_sum(full_registry):
    # the two conjuncts bare-fold to the SAME measure lemma ('coin') with
    # DIFFERENT qualifiers — facts.py's measure_qualifier collision split
    # keys them apart, and each is independently askable.
    r = solve(
        "The jar has 6 gold coins and twice as many silver coins. "
        "How many silver coins does the jar have?",
        full_registry,
    )
    assert r.answer.value == 12
    r2 = solve(
        "The jar has 6 gold coins and twice as many silver coins. "
        "How many gold coins does the jar have?",
        full_registry,
    )
    assert r2.answer.value == 6


def test_elided_item_same_measure_conjunct_sums_via_segment(full_registry):
    # arithmetic/times-as-many-conjunct-elided-item: item2 is elided
    # entirely (nothing but a bare adjunct follows 'many'), so it reuses
    # item1's own measure — a genuine restatement, disambiguated from the
    # first conjunct via `segment` and summed by the ordinary fold.
    r = solve(
        "The vehicle has 20 parts on one side and twice as many parts "
        "on the other side. How many parts does the vehicle have?",
        full_registry,
    )
    assert r.answer.value == 60


def test_anaphoric_this_many_event_verb(full_registry):
    # arithmetic/anaphoric-multiplier-conjunct-many: the demonstrative
    # idiom ("twice THIS MANY"), no 'as' anywhere, over an EVENT verb
    # (not state) — the antecedent is the immediately preceding conjunct's
    # own bound value, not a document-wide unique prior Quantity.
    r = solve(
        "The bird found 8 fish by day and twice this many by night. "
        "How many fish did the bird find in total?",
        full_registry,
    )
    assert r.answer.value == 24


def test_anaphoric_that_many_variant(full_registry):
    r = solve(
        "The bird found 8 fish by day and twice that many by night. "
        "How many fish did the bird find in total?",
        full_registry,
    )
    assert r.answer.value == 24


def test_explicit_standard_conjunct_relation(full_registry):
    # arithmetic/times-as-many-conjunct: the full "as many ITEM as STD"
    # continuation is present, so the second conjunct is an ordinary
    # Relation resolved by the pre-existing relations synthesizer.
    r = solve(
        "Sam has 21 pens and twice as many pencils as Jamie has. "
        "Jamie has 5 pencils. How many pencils does Sam have?",
        full_registry,
    )
    assert r.answer.value == 10


def test_first_conjunct_own_quantity_still_answerable(full_registry):
    # the first conjunct's own Quantity must survive re-emission
    # (pattern_consumed skips the general fold entirely for this verb).
    r = solve(
        "Sam has 21 pens and twice as many pencils as Jamie has. "
        "Jamie has 5 pencils. How many pens does Sam have?",
        full_registry,
    )
    assert r.answer.value == 21


def test_bare_number_conjunct_unaffected(full_registry):
    # decline-safety / non-interference: an ordinary bare-number second
    # conjunct ("15 pencils", no multiplier) is NOT this candidate's
    # shape at all (`k, type: multiplier` never matches a plain count) —
    # the general fold's own existing behaviour must be untouched.
    r = solve(
        "Sam has 21 pens and 15 pencils. How many pencils does Sam have?",
        full_registry,
    )
    assert r.answer.value == 15


def test_unresolvable_standard_declines(full_registry):
    # decline-safety: the explicit standard's own quantity is never
    # stated anywhere in the document, so the Relation cannot resolve —
    # this must decline, never guess.
    r = solve(
        "Sam has 21 pens and twice as many pencils as Riley has. "
        "How many pencils does Sam have?",
        full_registry,
    )
    assert r.answer.kind == "decline"
