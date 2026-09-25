"""Invented credit-account analogues: permission, usage and actual repayment."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import AccountEntry


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/curated")).registry


def story(payments="Mira repaid $18 on Tuesday and $27 on Thursday.",
          opening="Mira has a credit limit of $120.",
          draw="Mira used the full credit limit.",
          ask="How much does Mira still owe?"):
    return " ".join((opening, draw, payments, ask))


@pytest.mark.parametrize("payments", [
    "Mira repaid $18 on Tuesday and $27 on Thursday.",
    "Mira repaid $18 and $27.",
    "Mira repaid $18. Mira repaid $27.",
    "She repaid $18 on Thursday and $27 on Tuesday.",
    "She paid $18 of it on Tuesday and $27 of it on Thursday.",
    "She paid $18 of it. She paid $27 of it.",
    "Mira repaid $18 and repaid $27.",
])
@pytest.mark.parametrize("ask", [
    "How much does Mira still owe?",
    "How much does she owe?",
    "How much does Mira need to repay?",
    "How much credit will Mira need to pay?",
    "How much credit does Mira owe?",
    "How much does Mira still need to pay?",
])
def test_repayment_paraphrases(reg, payments, ask):
    result = solve(story(payments, ask=ask), reg)
    assert result.answer.value == 75, result.answer


def test_granted_credit_with_explicit_deadline(reg):
    result = solve(
        "Mira does her grocery shopping on Monday. She does her shopping only at a store "
        "where she is allowed a credit of $120, which must be paid in full before her next shopping trip. "
        "That week she spent the entire credit limit and paid $18 of it on Tuesday and $27 of it on Friday. "
        "How much credit will Mira need to pay before her next shopping trip?", reg)
    assert result.answer.value == 75, result.answer
    entries = result.store.by_kind(AccountEntry)
    assert {e.time for e in entries if e.value in (18, 27)} == {"tuesday", "friday"}
    settlement, = [e for e in entries if e.kind == "settlement"]
    assert (settlement.owner, settlement.deadline) == ("mira", "next shopping trip")
    assert result.answer.proof


@pytest.mark.parametrize("opening", [
    "Mira went shopping on Monday. She shops at a store where she has a credit of $120.",
    "Mira went shopping on Monday. She shops at a store where she is allowed a credit of $120.",
    "Mira has a credit limit of $120.",
    "Mira owes $120.",
])
def test_standalone_settlement_links_to_adjacent_account(reg, opening):
    draw = "" if "owes" in opening else "That week she spent the full credit limit."
    result = solve(story(
        opening=opening + " It must be paid in full before her next shopping trip.",
        draw=draw,
        ask="How much credit will Mira need to pay before her next shopping trip?",
    ), reg)
    assert result.answer.value == 75, result.answer
    settlement, = [e for e in result.store.by_kind(AccountEntry) if e.kind == "settlement"]
    assert settlement.attachment == "adjacent"
    assert (settlement.owner, settlement.deadline) == ("mira", "next shopping trip")


@pytest.mark.parametrize("opening,term", [
    ("Mira has a credit limit of $120. Mira has a coat.", "It"),
    ("Mira has a credit limit of $120 and a coat.", "It"),
    ("Mira has a credit limit of $120. Tova has a debt of $80.", "It"),
    ("Mira has a credit limit of $120.", "Which"),
    ("Mira has a credit limit of $120,", "it"),
    ("Mira has a credit limit of $120.", "Her coat"),
])
def test_settlement_does_not_skip_or_invent_an_antecedent(reg, opening, term):
    result = solve(story(
        opening=opening + f" {term} must be paid in full before her next shopping trip.",
        ask="How much credit will Mira need to pay before her next shopping trip?",
    ), reg)
    assert not result.answer.committed, result.answer


def test_finite_shops_preserves_plural_shop_reading(reg):
    from rulekit.kernel.model import Predication

    result = solve("Mira shops at a store.", reg)
    assert any(p.subject == "mira" and p.verb == "shop"
               for p in result.store.by_kind(Predication))
    plural = solve("Mira has two shops. How many shops does Mira have?", reg)
    assert plural.answer.value == 2, plural.answer


@pytest.mark.parametrize("prefix,period", [
    ("That week", "week"), ("In that week", "week"),
    ("In that week,", "week"), ("In that month", "month"),
    ("That day", "day"), ("In that day", "day"),
    ("In that particular week", "week"),
    ("In that particular week,", "week"),
    ("That particular month", "month"),
    ("In that specific day", "day"),
])
def test_full_draw_demonstrative_time_adjunct(reg, prefix, period):
    result = solve(story(
        opening="Mira has a credit of $120. It must be paid in full before her next shopping trip.",
        draw=f"{prefix} she spent the full credit limit and paid $18 of it on Tuesday and $27 of it on Thursday.",
        payments="",
        ask="How much credit will Mira need to pay before her next shopping trip?",
    ), reg)
    assert result.answer.value == 75, result.answer
    draw, = [e for e in result.store.by_kind(AccountEntry) if e.kind == "full-draw"]
    assert draw.time == period


@pytest.mark.parametrize("draw", [
    "In that store Mira spent the full credit limit.",
    "In Mira spent the full credit limit.",
    "In two weeks Mira spent the full credit limit.",
    "In that week Mira might spend the full credit limit.",
    "In that week Mira did not spend the full credit limit.",
    "In that week if Mira spent the full credit limit.",
    "In that particular week Mira might spend the full credit limit.",
    "In that particular week Mira did not spend the full credit limit.",
    "In that particular week if Mira spent the full credit limit.",
    "In that particular week Mira spent half the credit limit.",
    "In that particular store Mira spent the full credit limit.",
])
def test_time_adjunct_does_not_hide_an_unread_restriction(reg, draw):
    result = solve(story(draw=draw), reg)
    assert not result.answer.committed, result.answer


@pytest.mark.parametrize("payments,expected", [
    ("Mira repaid $10 and $10 and $10.", 90),
    ("Mira repaid $120.", 0),
    ("Mira repaid $0.", 120),
    ("", 120),
])
def test_each_source_occurrence_counts_once(reg, payments, expected):
    result = solve(story(payments), reg)
    assert result.answer.value == expected, result.answer


def test_stated_liability_does_not_need_a_limit(reg):
    result = solve(story(opening="Mira owes $120.", draw=""), reg)
    assert result.answer.value == 75, result.answer
    combined = solve("Mira owed $120 and paid $18 of it on Monday and $27 of it on Tuesday. "
                     "How much does Mira owe?", reg)
    assert combined.answer.value == 75, combined.answer


@pytest.mark.parametrize("changes", [
    {"draw": ""},
    {"draw": "Mira used some credit."},
    {"draw": "Mira might use the full credit limit."},
    {"draw": "Mira did not use the full credit limit."},
    {"draw": "Tova used the full credit limit."},
    {"draw": "Mira used Tova's full credit limit."},
    {"draw": "Mira used the full clothing credit limit."},
    {"payments": "Tova repaid $18 and $27."},
    {"payments": "Mira will repay $18 and $27."},
    {"payments": "Mira did not repay $18."},
    {"payments": "Mira repaid $18 and $127."},
    {"payments": "Mira repaid 18 euros."},
    {"payments": "Mira paid $18 for a hat."},
    {"payments": "Mira repaid $18 and paid a fee."},
    {"payments": "Mira repaid $18. There is a fee of $5."},
    {"payments": "Mira repaid $18. Mira got a refund."},
    {"payments": "Mira repaid half of it."},
    {"ask": "How much credit will Mira need to pay before her next shopping trip?"},
    {"opening": "If Mira has a credit limit of $120.", "draw": "Mira used the full credit limit."},
    {"opening": "Mira owes some money. Mira has a credit limit of $120."},
    {"opening": "Mira has a credit limit of $120. Tova has a credit limit of $120."},
    {"opening": "Mira has a clothing credit limit of $120."},
])
def test_uncertain_or_unaccounted_changes_decline(reg, changes):
    result = solve(story(**changes), reg)
    assert not result.answer.committed, result.answer


def test_repayment_before_draw_is_not_subtracted_from_new_debt(reg):
    result = solve("Mira has a credit limit of $120. Mira repaid $18. "
                   "Mira used the full credit limit. How much does Mira owe?", reg)
    assert not result.answer.committed


def test_possessive_limit_reference_keeps_its_owner(reg):
    result = solve(story(draw="Mira used her full credit limit."), reg)
    assert result.answer.value == 75, result.answer


def test_deadline_owner_mismatch_declines(reg):
    result = solve("Mira is allowed a credit of $120, which must be paid in full before her next shopping trip. "
                   "Mira used the full credit limit. Mira repaid $18. "
                   "How much credit will Mira need to pay before his next shopping trip?", reg)
    assert not result.answer.committed


def test_other_consumers_cannot_drop_liability_evidence(reg):
    result = solve("Mira owes $120. Tova has 8 apples. How many apples does Tova have?", reg)
    assert not result.answer.committed


@pytest.mark.parametrize("text", [
    "Mira spent $18 on a hat and $27 on a coat.",
    "Mira paid $18 for a hat and $27 for a coat.",
    "Mira received $18 and $27.",
    "Mira repaid $18 but Tova spent $27 and $10 on a coat.",
])
def test_bare_amounts_are_not_automatically_repayments(reg, text):
    result = solve(text, reg)
    assert not any(e.kind == "continued-repayment" for e in result.store.by_kind(AccountEntry))


def test_nominal_activity_does_not_become_a_spurious_predicate(reg):
    from rulekit.kernel.model import Predication

    result = solve("Mira does her grocery shopping on Monday.", reg)
    assert not any(p.subject == "grocery" for p in result.store.by_kind(Predication))
    progressive = solve("Mira is shopping.", reg)
    assert any(p.subject == "mira" and p.verb == "shop"
               for p in progressive.store.by_kind(Predication))


def test_optional_string_emission_does_not_relax_required_bindings(reg):
    from rulekit.kernel.evaluate import EvaluationError
    from rulekit.kernel.patterns import _resolve_field

    assert _resolve_field("{day.optional}", {}, reg, False, None, "synthetic") == ""
    with pytest.raises(EvaluationError, match="unbound slot"):
        _resolve_field("{day}", {}, reg, False, None, "synthetic")


@pytest.mark.parametrize("change", ["unknown-optional", "unknown-slot", "noun-gate", "unknown-gate"])
def test_new_structural_contracts_are_compile_checked(change, tmp_path):
    from dataclasses import replace
    from rulekit.data.registry import CompileError, compile_registry
    from rulekit.data.schemas import RulesDoc

    project = load_project(Path("projects/curated"))
    fields = {"fact": "account_entry", "kind": "repayment", "position": "{amount.span_start}"}
    guards = []
    if change == "unknown-optional":
        fields["time"] = "{missing.optional}"
    else:
        guards = [{"preceding_verb_category": {
            "slot": "missing" if change == "unknown-slot" else "amount",
            "cat": "noun" if change == "noun-gate" else
                   "missing" if change == "unknown-gate" else "repayment_verb",
        }}]
    doc = RulesDoc.model_validate({"format": "rulekit/rules@1", "rules": [{
        "id": "invented/account-contract", "match": {"sentence": [
            {"slot": "amount", "cat": "currency_measure", "counted": True}]},
        "where": guards, "emits": [fields],
    }]})
    first, *rest = project.packs
    with pytest.raises(CompileError):
        # A synthetic pack path bypasses the repository-fixture cache.
        compile_registry([replace(first, root=tmp_path, rules=[*first.rules, doc]), *rest])


@pytest.mark.parametrize("rule", [
    "arithmetic/account-credit-grant", "arithmetic/account-credit-limit",
    "arithmetic/account-stated-liability", "arithmetic/account-full-draw",
    "arithmetic/account-repayment",
])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_complete_account_premises_are_generatable(rule, seed):
    from rulekit.generation import generate_candidate

    candidate = generate_candidate(load_project(Path("projects/curated")), rule_id=rule, seed=seed)
    assert candidate.target_status == "matched"
