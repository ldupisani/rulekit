"""Mining candidate dimension-comparatives: dimension-comparative relations
and dimension asks (height / length / weight).

Three things ship here:

1. A new `dimension_comparative` category (packs/core-english/categories/
   core.yaml, members in packs/difg-mined/categories/semantic.yaml) tagging
   the physical-dimension comparative adjectives ('taller'/'shorter',
   'longer'/'shorter', 'heavier'/'lighter', 'wider'/'larger'/'smaller',
   'higher') with a sign, via two child categories (`dimension_more`/
   `dimension_less`) that mirror `more_dir`/`less_dir`'s own polarity
   structure — but as a SIBLING of `delta`, never a member of it. Before
   this, none of these words were in `delta`, so "Jake is 12 inches taller
   than Jenny" fell through every relation rule and the general SVO fold
   misread "[12 inches]" as a bare stated Quantity — a latent confident-
   wrong once anything queried that measure, not merely a decline.
2. A new sentence rule, `arithmetic/anchored-relation-postfix-dimension`
   (packs/arithmetic/rules/core.yaml), cloned from the existing
   `arithmetic/anchored-relation-postfix` with `cat: dimension_comparative`
   in place of `cat: delta`, emitting the SAME Relation fact shape. The
   already-shipped saturate.py fixpoint and the generic fold/ask machinery
   finish the job — no consumer change, no new fact kind.
3. A new ask, `ask/how-many-unit-dimension-is` ("How many inches tall is
   Jake?"), modelled on `ask/how-old-is` but gated on a `dimension_adjective`
   category (several base-form words, not one literal like 'old'). A sibling
   BARE ask ("How tall is Jake?", no stated unit) was tried and DROPPED: it
   caught a genuine DECL->WRONG on dev-train and dev-holdout — the
   unit-less shape resolves its measure by picking the entity's UNIQUE
   in-play measure off a `who` slot that can bind a mis-resolved pronoun,
   and 'long' in particular doubles as the standard English DURATION idiom
   ("how long is their wait") as much as a physical one. The unit-qualified
   ask has no such risk: the stated unit forces an exact measure match or a
   decline, never a guess — that is the one dimension ask this file ships.

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


def test_taller_relation_forward(full_registry):
    # standard known first -> subject derived forward (standard + offset)
    r = solve(
        "Mia is 20 inches tall. Noah is 5 inches taller than Mia. "
        "How many inches tall is Noah?",
        full_registry,
    )
    assert r.answer.value == 25


def test_shorter_relation_negates_the_offset(full_registry):
    # 'shorter' flips the sign: subject = standard - offset
    r = solve(
        "Noah is 5 inches shorter than Mia. Mia is 20 inches tall. "
        "How many inches tall is Noah?",
        full_registry,
    )
    assert r.answer.value == 15


def test_taller_relation_inverse(full_registry):
    # subject known -> standard derived inverse (subject - offset)
    r = solve(
        "Noah is 5 inches taller than Mia. Noah is 25 inches tall. "
        "How many inches tall is Mia?",
        full_registry,
    )
    assert r.answer.value == 20


def test_heavier_relation_over_weight_measure(full_registry):
    # the same mechanism generalizes to a different physical dimension
    # (weight, not length) purely from the STATED unit ('pounds') — no
    # per-dimension Python mapping.
    r = solve(
        "Mia weighs 40 pounds. Noah is 8 pounds heavier than Mia. "
        "How many pounds heavy is Noah?",
        full_registry,
    )
    assert r.answer.value == 48


def test_centimeter_unit_also_resolves(full_registry):
    # the measure is read from the counted item's own unit word, not
    # hardcoded to inches/feet.
    r = solve(
        "Mia is 150 centimeters tall. Noah is 10 centimeters taller than "
        "Mia. How many centimeters tall is Noah?",
        full_registry,
    )
    assert r.answer.value == 160


def test_no_than_clause_declines_not_a_bogus_absolute_quantity(full_registry):
    # an attributive comparative with NO "than Y" anchor at all must not be
    # misread as a stated Quantity of the counted number — declines, same
    # precision-before-coverage discipline as the pre-existing 'delta'
    # family's dangling-comparative-relation rule.
    r = solve(
        "Noah has a taller building. How many inches tall is Noah?",
        full_registry,
    )
    assert not r.answer.committed


def test_bare_how_adj_is_ask_stays_declined(full_registry):
    # the BARE dimension ask (no unit named) was deliberately not shipped —
    # "How tall is Noah?" must still decline (no ask shape matches it),
    # never silently resolve off the elided-measure path this candidate
    # ruled out for precision reasons.
    r = solve(
        "Mia is 20 inches tall. Noah is 5 inches taller than Mia. "
        "How tall is Noah?",
        full_registry,
    )
    assert not r.answer.committed


def test_general_comparative_word_not_in_category_is_unaffected(full_registry):
    # 'faster' is a general comparative, not a member of
    # `dimension_comparative` — it must not be swept into the new relation
    # rule and must not disturb the ordinary fold reading of the sentence
    # it appears in.
    r = solve(
        "Mia has 20 apples. Noah has 5 apples faster than Mia. "
        "How many apples does Noah have?",
        full_registry,
    )
    assert r.answer.value == 5


def test_combined_dimension_ask_stays_out_of_scope(full_registry):
    # "what is the total height of X and Y" needs a dimension-name-to-
    # measure mapping this candidate deliberately does not add — declines
    # rather than guess, even though the underlying Relation facts are
    # now correctly extracted.
    r = solve(
        "Mia is 150 centimeters tall. Noah is 10 centimeters taller than "
        "Mia. What is the total height of Mia and Noah?",
        full_registry,
    )
    assert not r.answer.committed
