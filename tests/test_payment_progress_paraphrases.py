"""Service quotations, supplemental receipts and projected payment grammar."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def project():
    return load_project(Path("projects/curated"))


def number(project, text, expected):
    result = solve(text, project.registry)
    assert result.answer.committed, result.answer
    assert result.value == pytest.approx(expected)
    assert not result.deficiencies()
    return result


@pytest.mark.parametrize("activity,past,gerund,item", [
    ("washes", "washed", "washing", "car"),
    ("paints", "painted", "painting", "gate"),
])
@pytest.mark.parametrize("price", [
    "{activity} one {item} for $12",
    "{activity} three {item}s for $36",
    "charges $12 to {bare} one {item}",
])
def test_service_price_word_order_and_bundle_denominators(project, activity, past, gerund, item, price):
    quote = price.format(activity=activity, bare=gerund.removesuffix("ing"), item=item)
    number(project, f"Paige {quote}. Last week she {past} 8 {item}s. "
           f"Two clients each gave her a $3 gratuity. How much did Paige earn {gerund} {item}s last week?", 102)


@pytest.mark.parametrize("receipt,value,assumption", [
    ("Two customers each gave her a $3 tip.", 102, None),
    ("Two customers gave her a $3 tip.", 102, "per-client-supplement"),
    ("Two of her customers each gave her a $3 tip.", 102, None),
    ("Two of her clients each gave her a $3 gratuity.", 102, None),
    ("All of her customers each gave her a $3 tip.", 120, "one-client-per-service"),
    ("For each car she got a $3 tip.", 120, None),
    ("For every car she received a $3 gratuity.", 120, None),
    ("For 5 cars she received an additional $3 tip.", 111, "per-service-supplement"),
])
def test_service_supplements_preserve_distribution_and_report_defaults(project, receipt, value, assumption):
    result = number(project, "Paige washes one car and charges $12. Last week she washed 8 cars. "
                    + receipt + " How much did Paige earn washing cars last week?", value)
    ids = {a.id for a in result.answer.assumptions}
    assert ids == ({assumption} if assumption else set())
    if assumption:
        assert all(a.sentences for a in result.answer.assumptions)


def test_implicit_per_client_receipt_also_works_in_a_coordinated_clause(project):
    result = number(project,
        "Paige washes one car for $12. Last week she washed 8 cars and two customers gave her a $3 tip. "
        "How many dollars did Paige earn washing cars last week?", 102)
    assert [a.id for a in result.answer.assumptions] == ["per-client-supplement"]


@pytest.mark.parametrize("amount", ["additional 3 dollars", "3 extra dollars", "extra 300 cents"])
def test_word_currency_supplements_preserve_monetary_value(project, amount):
    number(project, "Paige washes one car for $12. Last week she washed 8 cars. "
           f"For 5 cars she received {amount} tip. "
           "How much did Paige earn washing cars last week?", 111)


def test_currency_descriptions_of_counted_objects_remain_nominal(project):
    result = solve("Paige collected 3 dollar coins.", project.registry)
    assert any(u.features.get("lemma") == "coin" and u.features.get("value") == 3
               for r in result.premises for u in r.units)


@pytest.mark.parametrize("receipt,extra", [
    ("For 9 cars she received an additional $3 tip.", ""),
    ("For each gate she got a $3 tip.", ""),
    ("Two customers each gave Ezra a $3 tip.", ""),
    ("Two customers gave her a $3 tip in total.", ""),
    ("All of her customers each gave her a $3 tip.", "Some customers had two cars. "),
    ("For each car she got a $3 tip.", "She spent $5 on a book. "),
])
def test_supplements_do_not_erase_competing_scope_or_work_evidence(project, receipt, extra):
    text = "Paige washes one car for $12. Last week she washed 8 cars. " + receipt + " " + extra
    result = solve(text + "How much did Paige earn washing cars last week?", project.registry)
    assert not result.answer.committed
    assert not result.answer.assumptions


def financing(policy="provided that a 15% deposit is made", schedule="in instalments ", extra="wants to pay an extra $10 for the deposit", question="How much will her balance be after paying for 3 months?"):
    return ("Paige planned to buy a laptop for $400. A shop accepts payment " + schedule +
            "of $25 per month " + policy + ". If Paige " + extra + ", " + question)


@pytest.mark.parametrize("policy", [
    "provided that a 15% deposit is made", "if a 15% down payment is made",
    "provided that a 15% upfront payment is made", "with a 15% down payment",
    "with a 15% up-front payment", "if a 15% initial payment is made",
])
@pytest.mark.parametrize("schedule", ["in installments ", ""])
def test_payment_policy_paraphrases_share_the_same_projection(project, policy, schedule):
    number(project, financing(policy=policy, schedule=schedule), 255)


@pytest.mark.parametrize("extra", [
    "pays an additional $10 for the deposit", "adds an extra $10 for the deposit",
    "does an additional $10 down payment", "makes an extra $10 deposit",
    "wants to pay an extra $10 for the down payment",
])
def test_planned_actual_and_nominal_initial_payment_forms(project, extra):
    result = number(project, financing(extra=extra), 255)
    assert sum(getattr(f, "kind", "") == "initial-payment-supplement" for f in result.store.facts) == 1


@pytest.mark.parametrize("question", [
    "What will her balance be after 3 months of payments?",
    "How much will her balance be after 3 months of instalments?",
])
def test_payment_duration_nominals(project, question):
    number(project, financing(question=question), 255)


def test_noncomputer_purchase_uses_the_same_payment_projection(project):
    number(project, financing().replace("laptop", "book").replace("shop", "company"), 255)


@pytest.mark.parametrize("before,after", [
    ("15%", "115%"), ("provided that", "unless"), ("3 months", "3 days"),
    ("an extra $10", "$10"), ("her balance", "Ezra's balance"),
    ("If Paige", "If Ezra"), ("How much", "The shop charges interest. How much"),
])
def test_new_payment_grammar_keeps_existing_projection_boundaries(project, before, after):
    result = solve(financing().replace(before, after), project.registry)
    assert not result.answer.committed
    assert not result.answer.assumptions


@pytest.mark.parametrize("participation", ["competing", "taking part", "participating"])
@pytest.mark.parametrize("deadline", ["one week", "a week"])
@pytest.mark.parametrize("average", ["(3/2)", "three halves"])
def test_completion_participation_and_period_paraphrases(project, participation, deadline, average):
    result = number(project,
        f"Paige and Quinn are {participation} in a week long race. They have {deadline} to run 42 miles. "
        f"On the first two days Paige averages {average} of a mile. On the third day she runs 9 miles. "
        "Quinn averages 4 miles each day over the first 3 days. "
        "What is the average of their average that they have to run over the final four days?", 7.5)
    assert {a.id for a in result.answer.assumptions} == {
        "individual-competition-goal", "prefix-average-per-period",
    }


def test_explicit_reading_goals_do_not_gain_an_individual_goal_default(project):
    result = number(project,
        "Paige and Quinn each have one week to read 42 pages. "
        "On the first two days Paige averages 1.5 pages per day. On the third day she reads 9 pages. "
        "Quinn averages 4 pages each day over the first 3 days. "
        "What is the average of their average that they have to read over the final four days?", 7.5)
    assert not result.answer.assumptions


@pytest.mark.parametrize("before,after", [
    ("a week to", "a weeks to"), ("third day", "fourth day"),
    ("each day", "each hour"), ("taking part", "taking"),
])
def test_completion_paraphrases_keep_duration_and_prefix_boundaries(project, before, after):
    text = ("Paige and Quinn are taking part in a week long race. They have a week to run 42 miles. "
            "On the first two days Paige averages 1.5 miles per day. On the third day she runs 9 miles. "
            "Quinn averages 4 miles each day over the first 3 days. "
            "What is the average of their average that they have to run over the final four days?")
    assert not solve(text.replace(before, after), project.registry).answer.committed


@pytest.mark.parametrize("rule_id", [
    "arithmetic/service-unit-price-for", "arithmetic/service-tariff-counted",
    "arithmetic/distributed-supplemental-receipt-implicit-each",
    "arithmetic/completed-service-with-supplement-implicit-each",
    "arithmetic/partitive-distributed-supplemental-receipt",
    "arithmetic/supplement-per-completed-service", "arithmetic/supplement-for-counted-services",
    "arithmetic/supplement-from-all-service-clients",
    "arithmetic/installment-payment-policy-if", "arithmetic/installment-payment-policy-with",
    "arithmetic/additional-initial-payment", "arithmetic/additional-initial-payment-light-auxiliary",
    "arithmetic/additional-initial-payment-light-verb",
    "arithmetic/shared-completion-deadline-single-period", "arithmetic/average-each-initial-period",
])
def test_new_generatable_grammar_round_trips_through_the_reader(project, rule_id):
    from rulekit.generation import generate_candidate

    candidate = generate_candidate(project, rule_id=rule_id, seed=73)
    assert candidate.target_status == "matched"
    assert not candidate.grammar_deficiencies
