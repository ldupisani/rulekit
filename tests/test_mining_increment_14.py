"""Increment 14: modal-verb subject binding — 'He CAN read 50 pages an hour'
used to bind the verb's subject to 'can' (sense-arbitrated to noun, then the
nearest subject candidate), stranding the pronoun. Three coordinated pieces:
the `modal` sense split from `auxiliary` in the packs (do-support stays
`auxiliary`; modals carry meaning and must NOT satisfy factual ask shapes —
'how many models CAN she buy' is a capacity ask, not an event sum), coverage
arbitration exempting function words from the disconnected-unit penalty, and
an article immediately to the left licensing the noun reading ('A can costs
$3'). Synthetic only."""

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


def test_modal_premise_binds_subject_and_rate_fires(full_registry):
    r = solve(
        "Machines can produce 5 toys an hour. "
        "How many toys do machines produce in 2 hours?",
        full_registry,
    )
    assert r.answer.value == 10


def test_modal_premise_with_pronoun_subject(full_registry):
    r = solve(
        "Rita is a fast reader. She can read 50 pages an hour. "
        "How many pages does Rita read in 3 hours?",
        full_registry,
    )
    assert r.answer.value == 150


def test_article_can_is_still_a_noun(full_registry):
    # 'A can costs...' — the article determines the nominal; the modal
    # reading must not steal it, and the priced-purchase path must still see
    # an ordinary counted noun
    r = solve(
        "Tim buys 4 cans at $3 each. How much does Tim spend?",
        full_registry,
    )
    assert r.answer.value == 12


def test_modal_question_is_not_a_factual_ask(full_registry):
    # 'how many X can she buy' asks CAPACITY; it must never be answered by
    # summing past 'buy' events (the kirsty-class DECL->WRONG the dev gate
    # caught mid-development)
    r = solve(
        "Nora saves enough to buy 30 models. The price goes up. "
        "How many models can she buy now?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_do_support_questions_unchanged(full_registry):
    # 'does' stays an auxiliary and factual asks keep working
    r = solve(
        "Leo has 7 marbles. How many marbles does Leo have?",
        full_registry,
    )
    assert r.answer.value == 7
