"""Mining increment 41: combined how-much totals — the how-much sibling
of ask/how-many-combined ("how many X do they have altogether?"). Same
shape, 'much' in place of 'many', routed to the same 'combined' consumer
(answer.py) that sums N entities' totals for a measure. Disjoint from the
name-subject how-much asks (how-much-noun-entity, how-much-bare-entity)
because this ask's who-slot is a PRONOUN, never a name. Synthetic only."""

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


def test_how_much_money_combined_in_total(full_registry):
    r = solve(
        "Priya earns 10 dollars. Salim earns 4 dollars. "
        "How much money do they have in total?",
        full_registry,
    )
    assert r.answer.value == 14


def test_how_much_money_combined_altogether_three_entities(full_registry):
    r = solve(
        "Wendy has 20 dollars. Farid has 5 dollars. Tobias has 8 dollars. "
        "How much money do they have altogether?",
        full_registry,
    )
    assert r.answer.value == 33


def test_how_much_combined_over_event_verb(full_registry):
    r = solve(
        "Nadia earned 12 dollars. Corin earned 6 dollars. "
        "How much money did they earn in total?",
        full_registry,
    )
    assert r.answer.value == 18


def test_how_much_combined_singular_subject_folds_the_one_holder(full_registry):
    # A SINGULAR subject ("does SHE have in total") sums that ONE holder's own
    # holdings — the aggregate marker is not a multi-holder combination there.
    # (Was an over-conservative decline; the subject-gapping work surfaced real
    # single-holder cases where the lone-holder answer is correct — see the
    # combined consumer's `subject_number` branch.) A PLURAL subject still needs
    # two holders (test_how_much_combined_declines_mixed_currency below).
    r = solve(
        "Priya earns 10 dollars. How much money does she have in total?",
        full_registry,
    )
    assert r.answer.value == 10


def test_how_much_combined_declines_mixed_currency(full_registry):
    # mixed currencies are genuinely ambiguous — measure resolution must
    # decline, not silently pick one
    r = solve(
        "Priya earns 10 dollars. Salim earns 4 pounds. "
        "How much money do they have in total?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_how_much_noun_entity_still_wins_for_a_named_subject(full_registry):
    # a NAME subject with a trailing 'in total' must still route to the
    # single-entity ask (ask/how-much-noun-entity), never get hijacked by
    # the new pronoun-gated combined ask
    r = solve(
        "Tobias has 10 dollars. How much money does Tobias have in total?",
        full_registry,
    )
    assert r.answer.value == 10
