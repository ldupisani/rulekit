"""mining candidate anaphoric-multiplier-standards: a DEMONSTRATIVE
multiplier standard ("twice that many", "twice this much", "three times
that amount", "twice that number", "3 times that price") — unlike every
other relation rule in packs/arithmetic/rules/core.yaml, "that"/"this"
here names no comparison ENTITY at all; it anaphorically points back at a
quantity (or price) already stated earlier in the document. The pattern
rules (arithmetic/anaphoric-multiplier-standard-much/-many/(bare, amount/
number)/-price) emit a Relation with an explicit reserved sentinel
`standard` (never a guess); saturate.py's `_relations_synth` resolves it
against the UNIQUE prior Quantity (or, for the price sibling, the UNIQUE
prior Price) known document-wide — zero or two-or-more candidates is
ambiguous and declines, never a guess. Synthetic only."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantity, Relation

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def full_registry():
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", mined])
    )


def test_anaphoric_many_resolves_and_combines(full_registry):
    r = solve(
        "Jordan lost 40 pounds. Priya lost three times that many. "
        "How many pounds did Jordan and Priya lose in total?",
        full_registry,
    )
    assert r.answer.value == 160


def test_anaphoric_much_resolves_and_combines(full_registry):
    r = solve(
        "Marcus lost 12 dollars. Devon lost twice that much. "
        "How many dollars did Marcus and Devon lose in total?",
        full_registry,
    )
    assert r.answer.value == 36


def test_anaphoric_amount_bare_category_resolves(full_registry):
    r = solve(
        "Nora lost 8 dollars. Owen lost twice that amount. "
        "How many dollars did Nora and Owen lose in total?",
        full_registry,
    )
    assert r.answer.value == 24


def test_anaphoric_number_bare_category_resolves(full_registry):
    r = solve(
        "Rosa lost 6 dollars. Tariq lost twice that number. "
        "How many dollars did Rosa and Tariq lose in total?",
        full_registry,
    )
    assert r.answer.value == 18


def test_anaphoric_this_demonstrative_also_resolves(full_registry):
    # 'this' is sensed `article` and already in SKIPPABLE_SENSES, so no
    # explicit literal token is written for it — the matcher transparently
    # skips it exactly as it would skip 'the'/'these'/'those'.
    r = solve(
        "Priya lost 5 dollars. Jordan lost three times this much. "
        "How many dollars did Priya and Jordan lose in total?",
        full_registry,
    )
    assert r.answer.value == 20


def test_anaphoric_price_standard_resolves(full_registry):
    r = solve(
        "A hat costs $5. A scarf costs three times that price. "
        "How much does the scarf cost?",
        full_registry,
    )
    assert r.answer.value == 15


def test_ambiguous_antecedent_declines_never_guesses(full_registry):
    # TWO different measures already in play for the antecedent entity
    # (apples, dollars) — zero or two-or-more candidates is ambiguous, so
    # this must decline rather than guess which one "that many" means.
    r = solve(
        "Anna has 20 apples. Anna has 5 dollars. Beth has twice that many.",
        full_registry,
    )
    beth_quantities = [
        f for f in r.store.facts
        if isinstance(f, Quantity) and f.entity == "beth"
    ]
    assert beth_quantities == []


def test_partitive_frame_noun_never_misread_as_anaphor(full_registry):
    # "double the NUMBER OF birds that Wendy has" is the UNRELATED existing
    # "the number of X that Y" frame construction (arithmetic/times-the-
    # number-of and siblings), not our demonstrative anaphor — 'of'
    # anywhere in the sentence gates the whole anaphoric family off
    # (`where: absent: {cat: partitive}`), so no anaphoric Relation is ever
    # emitted for this sentence, and the mis-set-up value-accounting
    # multiplier ('double') correctly leaves the whole answer declined
    # rather than committing a wrong derived total (dev-train look #66's
    # own regression, reverted before shipping).
    r = solve(
        "Mark has 9 goats. Mark has double the number of birds that Wendy has. "
        "How many goats does Mark have?",
        full_registry,
    )
    anaphoric_relations = [
        f for f in r.store.facts
        if isinstance(f, Relation) and f.standard.startswith("$anaphor:")
    ]
    assert anaphoric_relations == []
    assert r.answer.kind == "decline"
