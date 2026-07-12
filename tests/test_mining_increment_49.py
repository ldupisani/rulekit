"""Future-modal factual asks: "how much/many X will/would WHO VERB?" — the
same ordinary factual questions the existing auxiliary-gated asks already
answer ("does/did"), now ALSO phrased in the future/conditional tense
("will"/"would"). No new committer: a new `future_modal` slot type
(data/schemas.py SLOT_TYPES, kernel/patterns.py _slot_ok) matches an
auxiliary-sense token OR a modal-sense token whose word is in the new
`future_modal` category (packs/core-english/categories/core.yaml declares
the category against the new 'modal' root sense; its two members, will and
would, are difg-mined-only words and so live in
packs/difg-mined/categories/semantic.yaml, mirroring the 'negation'/'never'
precedent). Applied to exactly four existing ask ids (how-many-entity,
how-much-money-entity-left, how-much-noun-entity, how-many-combined) —
every other auxiliary-gated ask is untouched.

The six capacity/hypothetical modals (can/could/should/may/might/must) are
NOT in `future_modal`, so ask/how-many-capacity's own territory is
unaffected: a "how many X can WHO buy" question still only matches capacity
(never widens into a factual ask), reproducing the increment-14 kirsty
lesson (a wanted/hypothetical purchase is not a purchase). Synthetic only."""

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


def test_will_phrased_money_left_ask(full_registry):
    # the class's own primary evidence shape: an ordinary money-left
    # question, phrased in future tense
    r = solve(
        "Priya has 12 dollars. She spends 4 dollars. "
        "How much money will Priya have left?",
        full_registry,
    )
    assert r.answer.value == 8


def test_would_phrased_money_left_ask(full_registry):
    r = solve(
        "Priya has 12 dollars. She spends 4 dollars. "
        "How much money would Priya have left?",
        full_registry,
    )
    assert r.answer.value == 8


def test_will_phrased_how_much_noun_entity_ask(full_registry):
    r = solve(
        "Priya has 9 dollars. How much money will Priya have?",
        full_registry,
    )
    assert r.answer.value == 9


def test_will_phrased_how_many_combined_ask(full_registry):
    r = solve(
        "Priya has 3 marbles. Deshawn has 4 marbles. "
        "How many marbles will they have combined?",
        full_registry,
    )
    assert r.answer.value == 7


def test_ordinary_auxiliary_ask_still_matches_unchanged(full_registry):
    # the pre-existing "does/did" auxiliary form must keep matching exactly
    # as before — future_modal is an ADDITION to the aux slot, not a
    # replacement
    r = solve(
        "Priya has 12 dollars. She spends 4 dollars. "
        "How much money does Priya have left?",
        full_registry,
    )
    assert r.answer.value == 8


def test_capacity_modal_can_does_not_widen_into_future_modal(full_registry):
    # 'can' is a capacity/hypothetical modal, NOT in future_modal — a "how
    # many X can WHO buy" question must still only be reachable through
    # ask/how-many-capacity (which declines here for lack of a Price fact),
    # never through the widened factual ask machinery this candidate adds
    r = solve(
        "Priya has 5 marbles. How many marbles can Priya have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_capacity_modal_would_not_confused_with_should(full_registry):
    # 'should' is also a capacity/hypothetical modal excluded from
    # future_modal — decline-safety companion to the 'can' case above
    r = solve(
        "Priya has 5 marbles. How many marbles should Priya have?",
        full_registry,
    )
    assert r.answer.kind == "decline"
