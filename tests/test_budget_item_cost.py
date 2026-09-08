"""Synthetic closed-allocation residual costs; never corpus prose."""

from pathlib import Path
from copy import deepcopy
from dataclasses import replace

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Expenditure, ResourceBalance, Quantity


@pytest.fixture(scope="module")
def registry():
    return load_project(Path("projects/curated")).registry


def story():
    return (
        "Mira is applying for a job. She bought business clothes "
        "to wear to an interview. "
        "She went to a department store with a budget of $150 and spent $20 on a "
        "button-up shirt, $35 on suit pants, $10 on a suit coat, $8 on socks, "
        "and $12 on a belt. "
        "Mira also purchased a pair of shoes, but lost the receipt for them. "
        "She has $25 left from her budget. How much did Mira pay for the shoes?"
    )


def simple(*, spending="Mira spent $20 on a hat and $35 on a coat.", purchase="Mira purchased shoes."):
    return (f"Mira has a budget of $150. {spending} {purchase} "
            "Mira has $25 left from her budget. How much did Mira pay for the shoes?")


def test_full_shopping_narrative_retains_item_costs(registry):
    r = solve(story(), registry)
    assert (r.answer.kind, r.answer.value) == ("number", 40.0), r.answer
    assert len(list(r.store.by_kind(ResourceBalance))) == 2
    expenses = [e for e in r.store.by_kind(Expenditure) if e.value is not None]
    assert [(e.item, e.qualifier, e.value) for e in expenses] == [
        ("shirt", "button-up", 20), ("pants", "suit", 35),
        ("coat", "suit", 10), ("sock", "", 8), ("belt", "", 12),
    ]
    assert not any(q.measure in {"coat", "belt"} and q.verb == "spend"
                   for q in r.store.by_kind(Quantity))


@pytest.mark.parametrize("spending", [
    "Mira spent $20 on a hat and $35 on a coat.",
    "Mira spent $20 on a hat, and $35 on a coat.",
    "Mira spent $20 on a hat. Mira spent $35 on a coat.",
    "Mira paid $20 for a hat and $35 for a coat.",
])
@pytest.mark.parametrize("purchase", [
    "Mira purchased shoes.", "Mira bought shoes.",
    "Mira also purchased a pair of shoes, but lost the receipt for them.",
])
def test_generic_spending_and_purchase_paraphrases(registry, spending, purchase):
    r = solve(simple(spending=spending, purchase=purchase), registry)
    assert (r.answer.kind, r.answer.value) == ("number", 70), r.answer


def test_equal_costs_are_separate_events(registry):
    r = solve(simple(spending="Mira spent $20 on a hat, $20 on a coat, and $20 on a belt."), registry)
    assert r.answer.value == 65
    assert len([e for e in r.store.by_kind(Expenditure) if e.value == 20]) == 3


def test_other_purchase_target_and_currency_word_form(registry):
    text = simple(purchase="Mira bought a book.").replace("the shoes?", "the book?")
    text = text.replace("$150", "150 dollars").replace("$25", "25 dollars")
    assert solve(text, registry).answer.value == 70


@pytest.mark.parametrize("old,new", [
    ("Mira has a budget of $150.", ""),
    ("Mira has $25 left from her budget.", ""),
    ("Mira has $25 left from her budget.", "Mira has $25 left."),
    ("Mira has a budget of $150.", "Tova has a budget of $150."),
    ("Mira has a budget of $150.", "Mira has a budget of $150 and lost money."),
    ("Mira has a budget of $150.", "Mira has a budget of $150 and received money."),
    ("from her budget", "from Tova's budget"),
    ("Mira purchased shoes.", "Mira purchased shoes. Mira purchased a belt."),
    ("Mira purchased shoes.", "Mira purchased shoes and a belt."),
    ("Mira purchased shoes.", "Mira purchased shoes or a belt."),
    ("Mira purchased shoes.", "Mira can purchase shoes."),
    ("Mira purchased shoes.", "Mira never purchased shoes."),
    ("Mira purchased shoes.", "Mira purchased 2 shoes."),
    ("Mira purchased shoes.", "Mira purchased shoes for $15."),
    ("Mira purchased shoes.", "Tova purchased shoes."),
    ("Mira spent $20 on a hat", "Tova spent $20 on a hat"),
    ("$150", "$30"),
    ("$35 on a coat", "$35 near a coat"),
    ("$35 on a coat", "$35 on a coat and spent money"),
    ("$35 on a coat", "$35 on a coat and money"),
    ("$35 on a coat", "$35 on a coat and a belt"),
    ("$35 on a coat", "$35 on a coat and lost money"),
    ("$35 on a coat", "$35 on a coat and received $20"),
    ("$35 on a coat", "$35 on a coat and $20"),
    ("$35 on a coat", "$35 on a coat. Mira received $20 and lost money"),
    ("How much did Mira", "Mira purchased a hat. How much did Mira"),
    ("the shoes?", "the shoes each?"),
    ("the shoes?", "2 shoes?"),
    ("the shoes?", "the coat?"),
])
def test_ambiguous_or_incomplete_budget_declines(registry, old, new):
    result = solve(simple().replace(old, new), registry)
    assert not result.answer.committed, result.answer


def test_zero_residual_is_valid(registry):
    assert solve(simple().replace("$150", "$80"), registry).answer.value == 0


def test_old_price_and_quantity_consumers_still_work(registry):
    r = solve("Mira buys 3 toys at $10 each. How much did Mira spend?", registry)
    assert r.answer.value == 30


def test_qualified_subgroup_cannot_borrow_the_unqualified_whole():
    reg = load_project(Path("projects/gsm8k")).registry
    r = solve("Tova has 31 socks. She has 5 pairs of socks that match. "
              "How many mismatching socks does Tova have?", reg)
    assert not r.answer.committed


def test_shared_qualified_measure_survives_relation_chains():
    reg = load_project(Path("projects/gsm8k")).registry
    r = solve("Mira has 4 more than twice as many video games as Tova. "
              "Tova has half as many video games as Cato. Cato has 10 video games. "
              "How many video games does Mira have?", reg)
    assert r.answer.value == 14


def test_fully_elided_comparison_inherits_the_same_qualified_measure(registry):
    r = solve("Mira has 12 blue shirts. Tova has 4 fewer than Mira. "
              "How many blue shirts does Tova have?", registry)
    assert r.answer.value == 8


def test_declared_hyphenated_adjective_is_not_two_unknown_words(registry):
    from rulekit.kernel.engine import analyze
    reading = analyze("A button-up shirt.", registry)
    assert not reading.unknown_words()
    assert any(u.features.get("qualifier") == "button-up" for u in reading.units)
    assert analyze("A button up shirt.", registry).unknown_words()


def test_progressive_auxiliary_does_not_create_membership(registry):
    from rulekit.kernel.model import Membership
    r = solve(story(), registry)
    assert not any(m.member == "mira" and m.collection in {"job", "new job"}
                   for m in r.store.by_kind(Membership))


BUDGET_GUARD_CASES = [
    ("missing_endpoint", "a residual cost needs one opening and one closing budget balance"),
    ("endpoint_owner", "budget endpoints disagree on participant, account, unit, or order"),
    ("later_purchase", "a later purchase is outside the closed budget interval"),
    ("conditional", "budget evidence must be asserted rather than conditional"),
    ("foreign_cost", "all costs must belong to the same participant and currency"),
    ("foreign_account", "a transaction names a different resource account"),
    ("duplicate_transaction", "a purchase and payment may describe the same transaction"),
    ("unattached_allocation", "an allocation phrase has no unique participant and account"),
    ("two_unknowns", "the requested item must be the one unknown purchase cost"),
    ("known_target", "the requested item also has a separate stated cost"),
    ("invalid_amount", "purchase operands must be finite and nonnegative"),
    ("invalid_unit_price", "purchase operands must be finite and nonnegative"),
    ("unread_ask", "the account ask has an unread condition or qualifier"),
    ("missing_cost", "a stated value lies outside the complete budget equation"),
    ("duplicate_cost", "budget evidence repeats a numeric mention"),
    ("nonactual", "budget events must be actual and affirmative"),
    ("alternative", "an alternative event cannot close a definite budget"),
    ("unread_event", "a purchase or spending event has no complete cost target"),
    ("additional_change", "an additional resource change is outside the budget equation"),
    ("negative_residual", "known spending and remainder exceed the opening budget"),
]


@pytest.mark.parametrize("case,reason", BUDGET_GUARD_CASES)
def test_budget_defensive_guards(registry, case, reason):
    from rulekit.kernel.consumers import ConsumerContext
    from rulekit.kernel.consumers.budget_item_cost import budget_item_cost
    from rulekit.kernel.evaluate import ArithmeticLog
    from rulekit.kernel.facts import FactStore
    from rulekit.kernel.patterns import match_ask

    baseline = solve(simple(), registry)
    facts = list(baseline.store.facts)
    premises = deepcopy(baseline.premises)
    start = next(f for f in facts if isinstance(f, ResourceBalance) and f.stage == "opening")
    end = next(f for f in facts if isinstance(f, ResourceBalance) and f.stage == "closing")
    known = next(f for f in facts if isinstance(f, Expenditure) and f.value is not None)
    unknown = next(f for f in facts if isinstance(f, Expenditure) and f.value is None)

    def exchange(old, new):
        facts[facts.index(old)] = new

    if case == "missing_endpoint":
        facts.remove(end)
    elif case == "endpoint_owner":
        exchange(start, replace(start, owner="other"))
    elif case == "later_purchase":
        facts.append(replace(unknown, provenance=replace(unknown.provenance, sentence=99)))
    elif case == "conditional":
        exchange(start, replace(start, provenance=replace(start.provenance, assumption=True)))
    elif case == "foreign_cost":
        exchange(known, replace(known, entity="other"))
    elif case == "foreign_account":
        exchange(known, replace(known, account="other"))
    elif case == "duplicate_transaction":
        # Same item and amount, but a different evidence basis. It cannot be
        # debited twice without an explicit transaction identity link.
        facts.append(replace(known, position=999, basis="purchase"))
    elif case == "unattached_allocation":
        from rulekit.kernel.model import ResourceAllocation
        allocation = next(f for f in facts if isinstance(f, ResourceAllocation))
        facts.append(replace(allocation, head_span="999"))
    elif case == "two_unknowns":
        facts.append(replace(unknown, item="other"))
    elif case == "known_target":
        exchange(known, replace(known, item="shoe"))
    elif case == "invalid_amount":
        exchange(known, replace(known, value=float("nan")))
    elif case == "invalid_unit_price":
        exchange(known, replace(known, value=None, quantity=3, unit_price=-10))
    elif case == "unread_ask":
        pass  # remove a required ask token from the claimed footprint below
    elif case == "missing_cost":
        facts.remove(known)
    elif case == "duplicate_cost":
        facts.append(replace(known, position=999))
    elif case == "nonactual":
        premises[1].unit(known.event).features["senses"] = ["modal"]
    elif case == "alternative":
        conjunction = next(u for u in premises[1].units if u.sense() == "conjunction")
        conjunction.features["lemma"] = "$unsupported:alternative$"
    elif case == "unread_event":
        noun = next(u for u in premises[1].units if u.features.get("lemma") == "hat")
        noun.features.update(senses=["verb"], lemma="buy")
    elif case == "additional_change":
        premises[1].unit(known.event).features["lemma"] = "give"
    elif case == "negative_residual":
        exchange(start, replace(start, value=30))
        amount = next(u for u in premises[0].units if u.features.get("value") == 150)
        amount.features["value"] = 30
    else:
        raise AssertionError(case)

    if case in {"nonactual", "alternative", "unread_event", "additional_change"}:
        # Completeness is now shared reader evidence, not a second parser in
        # this consumer. Rebuild that evidence after changing the reading.
        from rulekit.kernel.resource_accounting import compose_resource_accounts
        evidence_store = FactStore(facts=facts)
        compose_resource_accounts(evidence_store, premises, registry)
        facts = evidence_store.facts

    ask, query, match = match_ask(baseline.question, registry)
    if case == "unread_ask":
        verb = next(u for u in baseline.question.units if u.sense() == "verb")
        match = replace(match, consumed=tuple(uid for uid in match.consumed if uid != verb.uid))
    got = budget_item_cost(ConsumerContext(
        query, baseline.question, FactStore(facts=facts), registry,
        ArithmeticLog(), match, ask, tuple(premises),
    ))
    assert (got.kind, got.reason) == ("decline", reason)


def test_budget_balance_cannot_be_ignored_by_an_older_consumer(registry):
    r = solve(simple().replace("How much did Mira pay for the shoes?", "How much money does Mira have?"), registry)
    assert not r.answer.committed


@pytest.mark.parametrize("rule,kind", [
    ("resource-budget-opening", "ResourceAllocation"),
    ("resource-budget-amount-first", "ResourceAllocation"),
    ("resource-budget-remainder", "ResourceBalance"),
])
def test_budget_premises_generate_and_round_trip(rule, kind):
    from rulekit.generation import generate_candidate
    project = load_project(Path("projects/curated"))
    candidate = generate_candidate(project, rule_id=f"arithmetic/{rule}", seed=0)
    assert candidate.target_status == "matched"
    facts = [f["fields"] for f in candidate.facts if f["type"] == kind]
    assert len(facts) == 1
    if kind == "ResourceBalance":
        assert facts[0]["stage"] == "closing"
    assert facts[0]["value"] >= 0


def test_item_cost_ask_generates_but_does_not_invent_budget_evidence():
    from rulekit.generation import generate_ask_scenario
    project = load_project(Path("projects/curated"))
    candidate = generate_ask_scenario(
        project, ask_id="ask/how-much-pay-for-item", seed=0,
        scenario_mode="ask_only",
    )
    assert candidate.query["consumer"] == "budget-item-cost"
    assert not candidate.answer["committed"]
    assert "one opening and one closing" in candidate.answer["reason"]


@pytest.mark.parametrize("kwargs", [
    {"type": "counted"},
    {"cat": "currency_measure", "counted": True},
    {"type": "noun", "attributive_counted": True},
])
def test_uncounted_slot_cannot_also_require_a_count(kwargs):
    from pydantic import ValidationError
    from rulekit.data.schemas import MatchToken
    with pytest.raises(ValidationError, match="uncounted.*contradicts"):
        MatchToken(slot="item", uncounted=True, **kwargs)
