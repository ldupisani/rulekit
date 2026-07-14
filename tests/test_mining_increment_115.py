"""mining candidate percent-change-values: a stated currency holding
scaled by a self-referential percent INCREASE/DECREASE event ("Jordan puts
10% more money into his wallet") — a new PercentChange premise fact
(model.py), USE-gated for value accounting like Discount, consumed by
`_entity_total`'s (answer.py) unconditional percent-change fold, chained
in ascending sentence order across multiple events. A new ask id
(ask/how-much-noun-entity-uninverted) additionally covers the non-inverted
"how much MEASURE WHO will have" question order alongside the existing
inverted form. Synthetic only."""

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


def test_percent_increase_self_referential(full_registry):
    r = solve(
        "Jordan has $150 in his wallet. If he adds 10% more money to his "
        "wallet, how much money will he have?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 165.0


def test_percent_decrease_self_referential(full_registry):
    r = solve(
        "Priya has $80 saved. If Priya gets 25% less money from her chores, "
        "how much money will Priya have?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 60.0


def test_chained_percent_changes_across_sentences(full_registry):
    # two SEPARATE sentences, ascending sentence order: 300 * 1.10 * 1.05
    r = solve(
        "Marco has $300 in the bank. Marco gets 10% more money into the "
        "bank. Marco gets 5% more money into the bank. How much money "
        "will Marco have?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == pytest.approx(346.5)


def test_uninverted_question_word_order(full_registry):
    # "how much money SHE WILL have" — the non-inverted embedded-question
    # order (ask/how-much-noun-entity-uninverted), sibling of the ordinary
    # subject-aux-inverted form.
    r = solve(
        "Nadia has $120. If Nadia gets 15% more money from her job, how "
        "much money she will have?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 138.0


def test_percent_comparative_is_not_captured_as_self_change(full_registry):
    # decline-safety: "20% more money THAN Farah" is the EXISTING percent-
    # COMPARATIVE Relation family (a different entity standard), never a
    # self-referential PercentChange — Elena's own money is untouched.
    r = solve(
        "Elena has $50. Farah has $40. Elena has 20% more money than "
        "Farah. How much money does Elena have?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 50.0


def test_non_currency_percent_change_does_not_contaminate_money_fold(full_registry):
    # decline-safety: a percent-more EVENT over a NON-currency dobj
    # ('marbles') must never emit a PercentChange at all (the rule's own
    # `cat: currency` dobj gate), so it can never wrongly scale an
    # unrelated currency holding for the same entity.
    r = solve(
        "Owen has $90. Owen has 20% more marbles than Dylan. How much "
        "money does Owen have?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 90.0


def test_percent_change_with_no_prior_holding_declines(full_registry):
    # decline-safety: a percent-change event naming an entity with NO
    # prior currency Quantity at all has nothing to scale — declines
    # rather than guessing a base.
    r = solve(
        "Wanda has 5 rocks. Wanda gets 10% more money from a gift. How "
        "much money will Wanda have?",
        full_registry,
    )
    assert r.answer.kind == "decline"
