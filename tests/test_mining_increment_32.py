"""Mining candidate: stated-need premises as goals ("WHO needs N ITEM").

A stated NEED ('needs N item', a direct-object form with no infinitive) is a
GOAL, never a received event — the 'need_premise' category is untagged for
polarity, mirroring 'desire's want/wishes rationale but for the direct-object
phrasing (goal-need-quantity, sibling to goal-desire-quantity). This also
removes 'need'/'needed'/'needs' from the 'receive' event category (polarity
+1): they no longer fold into the ordinary signed event total, which kills a
latent confident-wrong where "Tom needs 30 apples. He has 12 apples." used to
sum to 42 via the generic SVO fold. The pre-existing goal-deficit consumer
(increment 23) is reused unchanged: it resolves a Goal fact against the
entity's single current STATE holding of the same measure. Synthetic only."""

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


def test_need_premise_goal_minus_holding(full_registry):
    r = solve(
        "Tom needs 30 apples. He has 12 apples. "
        "How many more apples does Tom need?",
        full_registry,
    )
    assert r.answer.value == 18


def test_need_premise_different_entity_and_measure(full_registry):
    r = solve(
        "Marcus needs 20 cookies. Marcus has 8 cookies. "
        "How many more cookies does Marcus need?",
        full_registry,
    )
    assert r.answer.value == 12


def test_need_premise_does_not_fold_as_a_signed_event(full_registry):
    # The pre-existing latent-wrong: 'need' used to sit in the receive(+1)
    # event category, so the generic SVO fold summed the needed quantity
    # with the stated holding (30 + 12 = 42). Now 'need' is untagged for
    # polarity via 'need_premise' and the plain holdings ask must still
    # answer from the stated holding alone, unaffected by the goal premise.
    r = solve(
        "Tom needs 30 apples. He has 12 apples. How many apples does Tom have?",
        full_registry,
    )
    assert r.answer.value == 12


def test_decline_when_no_current_holding_stated(full_registry):
    # a stated need alone, with no current holding, is genuinely
    # under-determined — decline rather than guess a deficit against zero.
    r = solve(
        "Tom needs 30 apples. How many more apples does Tom need?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_decline_when_goal_already_met(full_registry):
    # the "how many more" frame presumes the need is unmet; a holding that
    # already reaches or exceeds the stated need is a mismatch, not a
    # negative answer — decline rather than commit a confident-wrong.
    r = solve(
        "Lena needs 10 stamps. She has 12 stamps. "
        "How many more stamps does Lena need?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_decline_on_conflicting_need_statements(full_registry):
    # two disagreeing stated needs for the same entity/measure collide —
    # never silently pick one.
    r = solve(
        "Tom needs 30 apples. Tom needs 40 apples. He has 12 apples. "
        "How many more apples does Tom need?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_decline_with_no_need_events_at_all(full_registry):
    # no 'need' anywhere in the text: the deficit ask must decline safely
    # rather than route anywhere new (no goal fact to resolve against).
    r = solve("How many apples does Tom have?", full_registry)
    assert r.answer.kind == "decline"
