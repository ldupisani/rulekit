"""A POSSESSIVE determiner does not denote the pool.

`arithmetic/fraction-of-pronoun` was written for "she spent one-half OF IT" —
a pronoun that DENOTES THE POOL, which its synthesizer then sizes the fraction
against. A possessive determiner senses as 'pronoun' too, so the rule also
matched "Ben gave half of HIS marbles", where 'his' denotes nothing of the kind:
it modifies 'marbles' and names a possessor whose HOLDINGS are the intended
base. With two holders in play the synth sized Ben's half against Ben's 18 plus
John's 17 and had him give away 17.5 of his 18.

`cat: pool_pronoun` restricts the rule to the construction it was written for.
Membership was MEASURED across all six corpora (the word after "<fraction> of"):
them 100 · it 23 pool-denoting; his 78 · her 73 · its 18 · their 15 possessive
and excluded.

WHAT THIS IS NOT. It is not a fix for possessive fractions — reading those needs
a rule that BINDS THE POSSESSOR, which does not exist. The fraction now simply
goes unconsumed and the pre-existing value-accounting guard declines. That costs
nothing: all 78 GSM8K dev-train and 76 dev-holdout possessive items already
declined, so no capability was lost, only a confident-wrong.

⚠ THE CONTRACT THIS MUST NOT BREAK, and a first attempt DID break it: a DEFINITE
pool legitimately SPANS ENTITIES. "Tom found 12 eggs. Mary found 10 eggs. Tom ate
half of THE eggs" is 11 — half of everyone's, by design (test_mining_increment_5
::test_fraction_pool_spans_entities pins it). Holder count is a SYMPTOM here, not
the defect; the defect is the construction. Guarding on the pool's holder count
declined that item and was reverted.

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


def test_a_possessive_fraction_declines_rather_than_sizing_against_the_pool(full_registry):
    """The regression. Two holders, so the pool (35) is not Ben's (18) — and
    the engine must not quietly pick one."""
    r = solve(
        "Ben had 18 marbles and John had 17 marbles. "
        "Ben gave half of his marbles to John. "
        "How many more marbles did John have than Ben then?",
        full_registry,
    )
    assert r.answer.kind == "decline"
    assert "value-accounting" in r.answer.reason


def test_the_refusal_is_a_decline_not_a_fold_over_the_start_state(full_registry):
    """The subtle half. With no give-quantity, the fold would happily answer
    |17 - 18| = 1 from the untouched starting amounts — trading one confident-
    wrong for another. Leaving 'half' UNCONSUMED is what makes the pre-existing
    value-accounting guard fire and reach the answer."""
    r = solve(
        "Ben had 18 marbles and John had 17 marbles. "
        "Ben gave half of his marbles to John. "
        "How many more marbles did John have than Ben then?",
        full_registry,
    )
    assert not r.answer.committed
    assert r.answer.value != 1.0


def test_of_it_still_resolves(full_registry):
    """The class the rule exists for — 'it' DOES denote the pool."""
    r = solve(
        "Mary found 28 coins. She lost one fourth of it. How many coins are left?",
        full_registry,
    )
    assert (r.answer.kind, r.answer.value) == ("number", 21.0)


def test_of_them_still_resolves(full_registry):
    """'them' is the other measured member; a category with one member would
    have silently dropped this class."""
    r = solve(
        "Mary found 28 coins. She lost half of them. How many coins are left?",
        full_registry,
    )
    assert (r.answer.kind, r.answer.value) == ("number", 14.0)


def test_a_definite_pool_still_spans_entities(full_registry):
    """THE CONTRACT A FIRST ATTEMPT BROKE. "half of THE eggs" is the definite
    pool — everyone's — and that is correct English, not a bug. Pinned here as
    well as in test_mining_increment_5 because it is the boundary this change
    lives against: restrict by CONSTRUCTION, never by holder count."""
    r = solve(
        "Tom found 12 eggs. Mary found 10 eggs. Tom ate half of the eggs. "
        "How many eggs did Tom eat?",
        full_registry,
    )
    assert (r.answer.kind, r.answer.value) == ("number", 11.0)
