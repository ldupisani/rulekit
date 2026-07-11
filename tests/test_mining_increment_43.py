"""Mining increment 43: currency-interchangeable relation measures
("twice as much money as Cecil", anchor holds dollars).

Two coordinated, general, kernel-structural pieces (no new vocabulary):

1. `packs/arithmetic/rules/core.yaml` gains `arithmetic/times-as-much` and
   `arithmetic/fraction-as-much` — MASS-NOUN counterparts of the existing
   `times-as-many`/`fraction-as-many` Relation rules. "twice as much MONEY
   as Y" never matched before: the item slot required `type: plural`
   ("many" + a plural counted noun), and a mass noun like 'money' carries
   no plural morphology at all. The new rules swap the literal 'many' for
   'much' and the item slot for `type: noun` (any common noun) — the same
   slot type the pre-existing `times-the-number-of`/`affine-frame-relation`
   rules already use for their item slot, so this is not a new risk class.
2. `src/rulekit/kernel/saturate.py`'s `_relations_synth` (`synth/relation`)
   now resolves a Relation's stated measure against its ANCHOR entity's own
   holdings the same way `answer.py`'s `_resolve_measure` has resolved ask
   nouns since increment 26: an EXACT measure match first, else — ONLY for
   categories marked `interchangeable` in the packs (today: currency alone)
   — the anchor's own UNIQUE same-category measure. A Relation stated over
   'money' now resolves against an anchor's stated 'dollar' holding. An
   anchor holding two DIFFERENT currencies is genuinely ambiguous and
   declines, never guesses; a non-interchangeable category (e.g. two
   different animal-category nouns) never resolves this way either —
   the increment-26 sibling-borrow discipline, generalized to relations.

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


def test_times_as_much_money_resolves_to_anchor_currency(full_registry):
    # "three times as much MONEY" — a mass-noun ratio relation; the anchor
    # (Priya) only ever states a 'dollar' holding, never a 'money' one
    r = solve(
        "Priya has 50 dollars. Soren has three times as much money as Priya. "
        "How much money do they have altogether?",
        full_registry,
    )
    assert r.answer.value == 200


def test_fraction_as_much_money_resolves_to_anchor_currency(full_registry):
    # "half as much MONEY" — the fraction-ratio mass-noun counterpart
    r = solve(
        "Elke has half as much money as Tobias. If Tobias has 80 dollars, "
        "how much money does Elke have?",
        full_registry,
    )
    assert r.answer.value == 40


def test_chained_three_hop_currency_relation(full_registry):
    # a chain of mass-noun relations, each hop resolving through the SAME
    # anchor-currency fallback before the next hop can anchor on it
    r = solve(
        "Marisol has twice as much money as Dax. "
        "Dax has three times as much money as Fenwick. "
        "Fenwick has half as much money as Odalys. "
        "If Odalys has 40 dollars, how much money does Marisol have?",
        full_registry,
    )
    assert r.answer.value == 120


def test_regression_plural_dollar_relation_unaffected(full_registry):
    # the pre-existing 'many' + plural-noun path (times-as-many) must be
    # byte-for-byte unaffected by the new mass-noun sibling rule
    r = solve(
        "Priya has 50 dollars. Soren has three times as many dollars as Priya. "
        "How much money do they have altogether?",
        full_registry,
    )
    assert r.answer.value == 200


def test_ambiguous_anchor_currency_declines(full_registry):
    # the anchor holds TWO different currencies — genuinely ambiguous,
    # never guessed
    r = solve(
        "Priya has 10 dollars. Priya has 5 pounds. "
        "Soren has twice as much money as Priya. How much money does Soren have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_no_anchor_quantity_declines(full_registry):
    # the anchor never states ANY holding at all — no fallback to invent one
    r = solve(
        "Soren has three times as much money as Priya. "
        "How much money does Soren have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_non_interchangeable_sibling_relation_declines(full_registry):
    # 'cat'/'dog' share a non-interchangeable animal category — a relation
    # over 'cat' must NOT resolve against the anchor's 'dog' holding
    # (increment 26's sibling-borrow discipline, generalized to relations)
    r = solve(
        "Wendy has 5 dogs. Mia has three times as much cat as Wendy. "
        "How many cats does Mia have?",
        full_registry,
    )
    assert r.answer.kind == "decline"
