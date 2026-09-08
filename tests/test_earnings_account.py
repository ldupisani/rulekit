"""Invented closed-savings analogues and ambiguity boundaries."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import AccumulationWindow, EarningRate, PurchaseEndpoint
from rulekit.generation import generate_candidate


@pytest.fixture(scope="module")
def registry():
    return load_project(Path("projects/curated")).registry


def story():
    return (
        "Mira is buying a new coat that costs $83. "
        "She has been saving up her money each month for the past four months. "
        "She gets a $6 allowance a month. "
        "She also washes windows and paints gates. "
        "She charges $9 to wash a window and $5 to paint. "
        "After buying the coat, she has $8 in change. "
        "If she washes 3 windows, how many gates did she paint?"
    )


def test_residual_income_inverts_the_unknown_service_rate(registry):
    result = solve(story(), registry)
    assert (result.answer.kind, result.answer.value) == ("number", 8), result.answer
    assert len(result.store.by_kind(AccumulationWindow)) == 1
    assert len(result.store.by_kind(EarningRate)) == 3
    assert len(result.store.by_kind(PurchaseEndpoint)) == 2
    assert "no initial savings" in result.answer.reason
    assert result.answer.proof.steps[0].rule == "closed-savings-interpretation"


@pytest.mark.parametrize("old,new", [
    ("coat", "hat"),
    ("$83", "$93"),
    ("each month for the past four months", "each week for the past four weeks"),
    ("saving up", "saving"),
    ("If she washes 3 windows, how many", "She washed 3 windows. How many"),
])
def test_alternative_targets_durations_and_count_positions(registry, old, new):
    text = story().replace(old, new)
    if "week" in new:
        text = text.replace("a month", "a week")
    result = solve(text, registry)
    assert result.answer.value == (10 if new == "$93" else 8), result.answer


def test_whole_pair_price_is_not_doubled(registry):
    text = story().replace("a new coat", "a new pair of socks").replace("the coat", "the socks")
    result = solve(text, registry)
    assert result.answer.value == 8, result.answer
    quote = next(e for e in result.store.by_kind(PurchaseEndpoint) if e.stage == "quoted")
    assert (quote.item, quote.unit, quote.value) == ("sock", "pair", 83)


@pytest.mark.parametrize("old,new", [
    ("She has been saving up her money each month for the past four months. ", ""),
    ("After buying the coat, she has $8 in change. ", ""),
    ("She gets a $6 allowance a month. ", "She gets a $6 allowance a month. She received money. "),
    ("She gets a $6 allowance a month. ", "She gets a $6 allowance a month. She received $6. "),
    ("She gets a $6 allowance a month. ", "She gets a $6 allowance a month. She lost money. "),
    ("She gets a $6 allowance a month. ", "She gets a $6 allowance a month. She had $6. "),
    ("the coat, she", "the hat, she"),
    ("she has $8", "Cato has $8"),
    ("her money", "Cato's money"),
    ("and paints gates", "and paints windows"),
    ("If she washes 3 windows, ", ""),
    ("$83", "$20"),
    ("$83", "$84"),
    ("$5 to paint", "$0 to paint"),
    ("3 windows", "2.5 windows"),
    ("four months", "half a month"),
    ("a month.", "a week."),
    ("washes windows and", "washes windows or"),
    ("She also washes", "She never washes"),
    ("how many gates", "how many windows"),
    ("how many gates", "how many red gates"),
    ("washes windows and", "washes red windows and"),
    ("how many gates did she paint?", "how many gates did she paint today?"),
    ("She charges $9", "Cato charges $9"),
    ("She has been saving", "She may have been saving"),
])
def test_missing_ambiguous_or_extra_evidence_declines(registry, old, new):
    result = solve(story().replace(old, new), registry)
    assert not result.answer.committed, result.answer


def test_plain_service_count_does_not_need_a_savings_account(registry):
    result = solve("Mira washed 4 windows. How many windows did Mira wash?", registry)
    assert result.answer.value == 4, result.answer


def test_independent_service_declarations_and_tariffs(registry):
    text = story().replace("She also washes windows and paints gates.",
                           "She washes windows. She paints gates.")
    text = text.replace("She charges $9 to wash a window and $5 to paint.",
                        "She charges $9 to wash a window. She charges $5 to paint a gate.")
    assert solve(text, registry).answer.value == 8


def test_three_services_reuse_the_same_conservation_equation(registry):
    text = story().replace("After buying", "She mows lawns. She charges $2 to mow a lawn. She mowed 5 lawns. After buying")
    result = solve(text, registry)
    assert result.answer.value == 6, result.answer


def test_ambiguous_elided_tariff_cannot_choose_the_asked_object(registry):
    text = story().replace("She charges", "She paints windows. She charges")
    assert not solve(text, registry).answer.committed


def test_repeated_allowance_quote_is_not_two_income_sources(registry):
    text = story().replace("She gets a $6 allowance a month.",
                           "She gets a $6 allowance a month. She gets a $6 allowance a month.")
    assert not solve(text, registry).answer.committed


def test_quoted_purchase_is_not_an_actual_expense(registry):
    result = solve("Mira is buying a new coat that costs $83. How much did Mira spend?", registry)
    assert not result.answer.committed


def test_generic_count_ask_applies_category_owned_service_roles(registry):
    result = solve("Mira mowed 4 windows. How many windows did Mira mow?", registry)
    assert not result.answer.committed


def test_service_vocabulary_changes_do_not_change_the_equation(registry):
    text = (story().replace("washes", "mows").replace("wash", "mow").replace("windows", "lawns")
            .replace("window", "lawn").replace("paint", "shovel")
            .replace("gates", "driveways"))
    result = solve(text, registry)
    assert result.answer.value == 8, result.answer


def test_uncounted_past_work_is_not_a_service_offer(registry):
    text = (story().replace("$83", "$43")
            .replace("washes windows and paints gates", "washed windows and painted gates"))
    result = solve(text, registry)
    assert not result.answer.committed


@pytest.mark.parametrize("project_name", ["curated", "gsm8k"])
@pytest.mark.parametrize("rule", [
    "purchase-intent-priced-target", "purchase-intent-priced-pair",
    "resource-accumulation-window", "periodic-income-source",
    "service-declaration", "service-tariff", "coordinated-service-declaration",
    "coordinated-service-tariffs", "purchase-cash-remainder", "counted-service-activity",
])
def test_new_premise_shapes_generate_and_round_trip(project_name, rule):
    project = load_project(Path("projects") / project_name)
    candidate = generate_candidate(project, rule_id=f"arithmetic/{rule}", seed=11)
    assert candidate.target_status == "matched"
    assert candidate.facts
