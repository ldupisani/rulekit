"""Synthetic two-person allocations, separate from personal cash totals."""

import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import AllocationRatio


@pytest.fixture(scope="module")
def registry():
    return load_project("projects/curated").registry


def story():
    return ("The profit from a business transaction is shared among 2 business partners, "
            "Mira and Cato in the ratio 3:4 respectively. If Cato got $1800, "
            "how much will Mira have after spending some of her share on a coat that costs $125?")


def test_ratio_share_less_one_explicit_cost(registry):
    r = solve(story(), registry)
    assert r.value == 1225, r.answer
    assert len(r.store.by_kind(AllocationRatio)) == 1
    assert "not a claim about total personal wealth" in r.answer.reason


@pytest.mark.parametrize("old,new,expected", [
    ("3:4", "5:4", 2125),
    ("$125", "$300", 1050),
    ("profit from a business transaction", "prize", 1225),
    ("2 business partners", "2 friends", 1225),
    ("Cato got $1800", "Cato received $1800", 1225),
    ("Cato got $1800", "Cato has $1800", None),
    ("3:4", "3:0", None),
    ("3:4", "0:4", None),
    ("2 business partners", "3 business partners", None),
    ("Mira and Cato", "Mira and Mira", None),
    ("Cato got", "Dena got", None),
    ("$125", "$2000", None),
    ("$125?", "$125 tomorrow?", None),
    ("If Cato got", "Mira received $40. If Cato got", None),
    ("in the ratio 3:4 respectively", "in the ratio 3:4", None),
    ("her share", "Cato's share", None),
])
def test_scope_and_completeness(registry, old, new, expected):
    r = solve(story().replace(old, new), registry)
    assert r.value == expected, r.answer


def test_reverse_participant_direction(registry):
    text = story().replace("If Cato got", "If Mira got").replace("will Mira", "will Cato")
    r = solve(text, registry)
    assert r.value == 2275, r.answer


def test_ratio_cannot_be_ignored_by_an_ordinary_cash_ask(registry):
    text = story().split("If Cato")[0] + "Mira has $40. How much money does Mira have?"
    assert not solve(text, registry).answer.committed


@pytest.mark.parametrize("name", ["curated", "gsm8k"])
@pytest.mark.parametrize("rule", ["ordered-two-part-allocation", "ordered-two-part-allocation-unqualified"])
def test_allocation_variants_generate(name, rule):
    from rulekit.generation import generate_candidate
    c = generate_candidate(load_project("projects/" + name), rule_id="arithmetic/" + rule, seed=11)
    assert c.target_status == "matched"
    assert c.facts


def test_possessive_partitive_and_relative_price_are_unambiguous(registry):
    r = solve(story(), registry)
    assert not any(u.features.get("ambiguous") for u in r.question.units)
    share = next(u for u in r.question.units if u.features.get("lemma") == "share")
    assert share.senses() == ["noun"]


def test_genuinely_unresolved_homographs_still_have_a_search_cap(registry):
    from rulekit.kernel.engine import analyze
    from rulekit.kernel.obligations import MAX_AMBIGUOUS_UNITS
    # Independent lexical alternatives with no grammatical evidence remain
    # bounded; no increase to the Cartesian-search cap was made.
    r = analyze(" ".join(["cost"] * (MAX_AMBIGUOUS_UNITS + 1)), registry)
    assert any(u.features.get("ambiguous") for u in r.units)


def test_new_count_noun_does_not_break_existing_purpose_infinitives():
    registry = load_project("projects/gsm8k").registry
    text = ("Mira brought 12 cookies to share in class. "
            "How many cookies did Mira bring to share in class?")
    r = solve(text, registry)
    assert r.value == 12, r.answer


def test_determined_share_remains_a_noun(registry):
    from rulekit.kernel.engine import analyze
    r = analyze("Tom has a share.", registry)
    assert next(u for u in r.units if u.features.get("lemma") == "share").senses() == ["noun"]
