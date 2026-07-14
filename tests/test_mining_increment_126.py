"""Mining increment 126 (affine-nominal-relations): affine relation offsets in the
NOMINAL and AMOUNT-OF-MONEY frames — the "N more/less than K times the
number/amount of X (that) WHO has" nominal bare-relative-clause frame, the
"$N more/less than K times as much as WHO" amount-of-money elided-item
frame, and the "N more/less than K times WHO's NOUN" affine possessive-
standard frame — plus the "what is the number of WHO's NOUN?" nominal
single-entity ask that cashes the possessive-standard relations in.
Synthetic only."""

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


# --- arithmetic/affine-frame-relation-clause: nominal bare relative clause ---


def test_affine_frame_relation_clause_more(full_registry):
    r = solve(
        "Jordan has 7 more than twice the number of stamps Priya has. "
        "Priya has 9 stamps. How many stamps does Jordan have?",
        full_registry,
    )
    assert r.answer.value == 25  # 2*9 + 7


def test_affine_frame_relation_clause_fewer(full_registry):
    r = solve(
        "Marcus has 4 fewer than three times the number of badges Wren has. "
        "Wren has 5 badges. How many badges does Marcus have?",
        full_registry,
    )
    assert r.answer.value == 11  # 3*5 - 4


def test_affine_frame_relation_clause_still_defers_to_that_complementizer(full_registry):
    # a text WITH an explicit 'that' must still route to the pre-existing
    # arithmetic/affine-frame-relation rule (mandatory complementizer),
    # not silently double-emit or misfire through the new bare-clause rule.
    r = solve(
        "Jordan has 7 more than twice the number of stamps that Priya has. "
        "Priya has 9 stamps. How many stamps does Jordan have?",
        full_registry,
    )
    assert r.answer.value == 25


# --- arithmetic/affine-times-as-much-elided: amount-of-money elided item ---


def test_affine_times_as_much_elided_less(full_registry):
    r = solve(
        "Priya has 400 dollars. Omar has 150 dollars less than twice as much as Priya. "
        "How much money does Omar have?",
        full_registry,
    )
    assert r.answer.value == 650  # 2*400 - 150


def test_affine_times_as_much_elided_more(full_registry):
    r = solve(
        "Priya has 400 dollars. Omar has 25 dollars more than three times as much as Priya. "
        "How much money does Omar have?",
        full_registry,
    )
    assert r.answer.value == 1225  # 3*400 + 25


def test_affine_times_as_much_elided_still_defers_when_item_present(full_registry):
    # a text WITH an explicit item noun after 'much' must still route to
    # the pre-existing arithmetic/affine-times-as-much rule, not this one.
    r = solve(
        "Priya has 400 dollars. Omar has 150 dollars less than twice as much money as Priya. "
        "How much money does Omar have?",
        full_registry,
    )
    assert r.answer.value == 650


# --- arithmetic/affine-times-as-many-possessive-standard ---


def test_affine_times_as_many_possessive_standard(full_registry):
    r = solve(
        "Priya has 400 dollars. Omar has 30 more than twice Priya's money. "
        "How much money does Omar have?",
        full_registry,
    )
    assert r.answer.value == 830  # 2*400 + 30


# --- ask/what-is-the-number-of-possessed, feeding the possessive relations ---


def test_what_is_the_number_of_possessed_ask(full_registry):
    r = solve(
        "Jordan has 10 pets. Jordan has 2 fewer than twice the number of pets Priya has. "
        "What is the number of Priya's pets?",
        full_registry,
    )
    assert r.answer.value == 6  # (10 + 2) / 2


def test_what_is_the_number_of_possessed_ask_no_relation_declines(full_registry):
    # no relation or direct statement of Priya's cats anywhere -> decline,
    # never a guess (decline-safety).
    r = solve(
        "Jordan has 10 pets. What is the number of Priya's cats?",
        full_registry,
    )
    assert r.answer.kind == "decline"


# --- combined ask over three affine-nominal-relation holders ---


def test_combined_ask_over_three_affine_relations(full_registry):
    r = solve(
        "Amara has 500 dollars. Beto has 200 dollars less than twice as much as Amara. "
        "Chidi has 40 more than twice Amara's money. "
        "How much money do they have altogether?",
        full_registry,
    )
    assert r.answer.value == 2340  # 500 + (1000-200) + (1000+40)
