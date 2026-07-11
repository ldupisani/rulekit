"""Mining candidate: goal-deficit asks ("how many more X does WHO need" —
stated goal minus current holding).

A DESIRE verb ('wants') plus an infinitive VERB ("wants to collect 30
stamps") states a GOAL quantity, never an event — a Goal fact, use-gated
for value accounting like Rate/Price (existence alone must not satisfy the
value-accounting guard; only the deficit consumer actually subtracting a
holding from it counts as use). The deficit consumer commits only when
exactly one Goal fact and exactly one current (stated, STATE) holding
resolve for the entity/measure; anything else — no holding, more than one
goal, a goal already met — declines. Synthetic only."""

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


def test_goal_minus_holding(full_registry):
    r = solve(
        "Lena wants to collect 30 stamps. She has 12 stamps. "
        "How many more stamps does Lena need?",
        full_registry,
    )
    assert r.answer.value == 18


def test_goal_deficit_different_entities_and_measure(full_registry):
    r = solve(
        "Marcus wants to bake 20 cookies. Marcus has 8 cookies. "
        "How many more cookies does Marcus need?",
        full_registry,
    )
    assert r.answer.value == 12


def test_unrelated_ask_over_goal_bearing_text_unaffected(full_registry):
    # the Goal fact must not leak into the ordinary holdings fold — "how
    # many does X have" answers from the stated holding alone, exactly as
    # if the desire sentence had never been read.
    r = solve(
        "Lena wants to collect 30 stamps. She has 12 stamps. "
        "How many stamps does Lena have?",
        full_registry,
    )
    assert r.answer.value == 12


def test_decline_when_no_current_holding_stated(full_registry):
    # a goal alone, with no stated current holding, is genuinely
    # under-determined — decline rather than guess a deficit against zero.
    r = solve(
        "Lena wants to collect 30 stamps. How many more stamps does Lena need?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_decline_when_goal_already_met(full_registry):
    # the "how many more" frame presumes the goal is unmet; a holding that
    # already reaches or exceeds the goal is a mismatch, not a negative
    # answer — decline rather than commit a confident-wrong.
    r = solve(
        "Lena wants to collect 10 stamps. She has 12 stamps. "
        "How many more stamps does Lena need?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_decline_on_conflicting_goal_statements(full_registry):
    # two disagreeing goal statements for the same entity/measure collide —
    # never silently pick one.
    r = solve(
        "Lena wants to collect 30 stamps. Lena wants to collect 40 stamps. "
        "She has 12 stamps. How many more stamps does Lena need?",
        full_registry,
    )
    assert r.answer.kind == "decline"
