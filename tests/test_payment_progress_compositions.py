"""Invented product accounts, financing, personal shares and deadline averages."""

from pathlib import Path
import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def project():
    return load_project(Path("projects/curated"))


@pytest.fixture(scope="module")
def reg(project):
    return project.registry


def number(reg, text, value):
    r = solve(text, reg)
    assert r.answer.committed, r.answer
    assert r.value == pytest.approx(value)
    assert not r.deficiencies()
    return r


def service():
    return (
        "Paige washes one car and charges $12. Last week she washed 8 cars and two customers "
        "each gave her a $3 tip. How many dollars did Paige earn washing cars last week?"
    )


@pytest.mark.parametrize(
    "before,after,value",
    [
        ("tip", "tip", 102),
        ("tip", "gratuity", 102),
        ("charges $12", "charges $15", 126),
        ("washes", "paints", 102),
        (
            "washed",
            "painted",
            102,
        ),  # paired changes below use the complete activity family
        ("two customers", "four customers", 108),
    ],
)
def test_work_and_distributed_receipts(reg, before, after, value):
    text = service().replace(before, after)
    if before in ("washes", "washed"):
        text = (
            service()
            .replace("washes", "paints")
            .replace("washed", "painted")
            .replace("washing", "painting")
            .replace("cars", "gates")
            .replace("car", "gate")
        )
    number(reg, text, value)


def test_independent_receipt_and_existing_tariff_grammar(reg):
    text = (
        "Paige charges $12 to wash a car. Paige washed 8 cars. Two customers each gave Paige a $3 tip. "
        "How many dollars did Paige earn washing cars?"
    )
    number(reg, text, 102)


@pytest.mark.parametrize(
    "before,after",
    [
        ("her a $3", "Ezra a $3"),
        ("8 cars", "-8 cars"),
        ("last week?", "last month?"),
        ("she washed", "she might wash"),
        ("washes one", "washed one"),
        ("a $3 tip", "a $3 fee"),
    ],
)
def test_service_earnings_do_not_invent_distribution_or_work(reg, before, after):
    assert not solve(service().replace(before, after), reg).answer.committed


def parts():
    return (
        "Paige collected 3 beetles with 6 legs each and one crab with 12 legs. "
        "How many legs do the animals Paige collected have in total?"
    )


@pytest.mark.parametrize(
    "before,after,value",
    [
        ("in total", "in total", 30),
        ("one crab", "two crabs", None),
        ("6 legs each", "6 legs", None),
        ("6 legs each", "5 legs each", 27),
        ("12 legs", "8 legs", 26),
    ],
)
def test_explicit_per_object_component_counts(reg, before, after, value):
    text = parts().replace(before, after)
    if value is None:
        assert not solve(text, reg).answer.committed
    else:
        number(reg, text, value)


def test_manufactured_objects_reuse_the_component_product_account(reg):
    text = (
        "Paige collected 3 cars with 4 wheels each and one bicycle with 2 wheels. "
        "How many wheels do the vehicles Paige collected have in total?"
    )
    number(reg, text, 14)
    number(
        reg,
        text.replace("one bicycle with 2 wheels", "two bicycles with 2 wheels each"),
        16,
    )


def financing():
    return (
        "Paige plans to buy a laptop which costs $400. A shop accepts payment in instalments "
        "of $25 per month provided that a 15% deposit is made. She wants to pay an extra $10 "
        "for the deposit. How much will her balance be after paying for 3 months?"
    )


@pytest.mark.parametrize(
    "before,after,value",
    [
        ("which", "which", 255),
        ("which", "that", 255),
        ("instalments", "installments", 255),
        ("extra", "additional", 255),
        ("a laptop", "a book", 255),
        ("plans to buy", "has been planning to buy", 255),
        ("which costs", "for", 255),
        ("How much", "What", 255),
        ("3 months", "0 months", 330),
        ("extra $10", "extra $20", 245),
    ],
)
def test_financed_purchase_projection(reg, before, after, value):
    number(reg, financing().replace(before, after), value)


@pytest.mark.parametrize(
    "before,after",
    [
        ("15%", "115%"),
        ("3 months", "30 months"),
        ("3 months", "3 meters"),
        ("extra $10", "extra $10 liters"),
        ("her balance", "his balance"),
        ("extra $10", "$10"),
        ("provided that", "unless"),
    ],
)
def test_installment_scope_and_quantity_boundaries(reg, before, after):
    assert not solve(financing().replace(before, after), reg).answer.committed


def ratios():
    return (
        "The ratio of coins that Paige has to that which Quinn has is 2:3. "
        "The total number of coins they have is 100. Quinn spends half of what she has on toys. "
        "How many coins will Quinn remain with?"
    )


@pytest.mark.parametrize(
    "before,after,value",
    [
        ("half", "half", 30),
        ("half", "one fifth", 48),
        ("2:3", "3:2", 20),
        ("coins", "dollars", 30),
        ("spends", "uses", 30),
        ("Quinn remain", "she remain", 30),
    ],
)
def test_ordered_personal_shares_before_fractional_depletion(reg, before, after, value):
    number(reg, ratios().replace(before, after), value)


def test_ratio_paraphrases_reuse_the_same_ordered_allocation_fact(reg):
    prefix = ratios().split(". ", 1)[1]
    number(reg, "The ratio of Paige's coins to Quinn's coins is 2:3. " + prefix, 30)
    number(reg, "Paige and Quinn have coins in the ratio 2:3. " + prefix, 30)
    text = ratios().replace(
        "The total number of coins they have is 100",
        "Paige and Quinn have 100 coins altogether",
    )
    number(reg, text, 30)


@pytest.mark.parametrize(
    "before,after",
    [
        ("2:3", "0:0"),
        ("100", "101"),
        ("half", "125%"),
        ("Quinn spends", "Ezra spends"),
        ("coins will Quinn", "beads will Quinn"),
        ("half of what she", "half of what they"),
        ("Paige has", "Quinn has"),
    ],
)
def test_ratio_group_order_and_discrete_boundaries(reg, before, after):
    assert not solve(ratios().replace(before, after), reg).answer.committed


def progress():
    return (
        "Paige and Quinn are competing in a week long race. They have one week to run 42 miles. "
        "On the first two days Paige averages (3/2) of a mile. On day three she runs 9 miles. "
        "Quinn averages 4 miles a day over the first 3 days. "
        "What is the average of their average that they have to run over the final four days?"
    )


@pytest.mark.parametrize(
    "before,after,value",
    [
        ("4 miles a day", "4 miles a day", 7.5),
        ("4 miles a day", "5 miles a day", 7.125),
        ("day three", "the third day", 7.5),
        ("she runs", "Paige runs", 7.5),
        ("(3/2) of a mile", "1.5 miles", 7.5),
    ],
)
def test_average_of_individually_required_deadline_rates(reg, before, after, value):
    number(reg, progress().replace(before, after), value)


def test_noncompetitive_reading_goals_use_the_same_progress_account(reg):
    text = progress().replace(
        "Paige and Quinn are competing in a week long race. They have",
        "Paige and Quinn each have",
    )
    text = text.replace("run", "read").replace("miles", "pages").replace("mile", "page")
    number(reg, text, 7.5)


@pytest.mark.parametrize(
    "before,after",
    [
        ("day three", "day four"),
        ("day three", "a day"),
        ("first two days", "first three days"),
        ("final four days", "final three days"),
        ("3 days", "2 days"),
        ("she runs", "they run"),
        ("42 miles", "42 liters"),
        ("9 miles", "90 miles"),
        ("one week", "two weeks"),
    ],
)
def test_deadline_progress_requires_disjoint_complete_individual_prefixes(
    reg, before, after
):
    assert not solve(progress().replace(before, after), reg).answer.committed


def test_bundle_quote_preserves_its_service_denominator(reg):
    text = service().replace("one car and charges $12", "three cars and charges $36")
    number(reg, text, 102)


def test_explicit_reference_paradigms_must_agree_in_a_share_followup(reg):
    text = ratios().replace("Quinn remain", "he remain")
    assert not solve(text, reg).answer.committed


def test_scope_restrictions_are_not_lost_inside_owned_resource_descriptions(reg):
    text = ratios().replace(
        "The ratio of coins that Paige has to that which Quinn has",
        "The ratio of Paige's red coins to Quinn's red coins",
    )
    assert not solve(text, reg).answer.committed


def test_an_unindexed_pronoun_does_not_acquire_the_latest_person_by_recency(reg):
    text = progress().replace("On day three she runs 9 miles", "She runs 9 miles")
    assert not solve(text, reg).answer.committed


def test_perfect_auxiliary_cannot_absorb_a_finite_relative_clause_boundary(reg):
    r = number(reg, ratios(), 30)
    assert not any(
        u.surface.casefold() == "has is"
        for reading in r.premises
        for u in reading.units
    )
    r = solve("Paige has read 13 books. How many books did Paige read?", reg)
    assert any(
        d.kind == "merge-perfect" for reading in r.premises for d in reading.decisions
    )


def test_projected_payments_do_not_ignore_interest_or_competing_quotes(reg):
    for extra in [
        "The shop charges interest. ",
        "Paige plans to buy a book which costs $60. ",
    ]:
        text = financing().replace("How much", extra + "How much")
        assert not solve(text, reg).answer.committed


def test_unbounded_work_and_supplement_do_not_need_a_reporting_window(reg):
    text = service().replace("Last week ", "").replace(" last week?", "?")
    number(reg, text, 102)


@pytest.mark.parametrize("auxiliary", ["be", "been"])
def test_a_nonfinite_auxiliary_cannot_state_a_planning_predicate(reg, auxiliary):
    text = financing().replace("plans to buy", auxiliary + " planning to buy")
    assert not solve(text, reg).answer.committed


def test_a_plural_named_group_cannot_take_a_singular_possession_predicate(reg):
    text = ratios().replace(
        "The total number of coins they have is 100",
        "Paige and Quinn has 100 coins altogether",
    )
    assert not solve(text, reg).answer.committed


@pytest.mark.parametrize(
    "rule_id",
    [
        "arithmetic/service-unit-price",
        "arithmetic/completed-service-with-supplement",
        "arithmetic/collected-components-each-single",
        "arithmetic/installment-payment-policy",
        "arithmetic/possessed-holder-ratio",
        "arithmetic/prefix-average-counted",
        "arithmetic/indexed-completion-amount-ordinal",
    ],
)
def test_reusable_premises_generate_and_match(project, rule_id):
    from rulekit.generation import generate_candidate

    candidate = generate_candidate(project, rule_id=rule_id, seed=581)
    assert candidate.target_status == "matched"
    assert not candidate.grammar_deficiencies


def test_service_tariffs_convert_compatible_currency_units(reg):
    number(reg, service().replace("charges $12", "charges 1200 cents"), 102)


def test_additional_deposits_reuse_monetary_conversion(reg):
    number(reg, financing().replace("extra $10", "extra 1000 cents"), 255)


def test_completed_work_remains_available_to_existing_quantity_questions(reg):
    number(
        reg,
        "Last week Paige washed 8 cars. How many cars did Paige wash last week?",
        8,
    )
    number(
        reg,
        "Paige washes one car and charges $12. Last week Paige washed 8 cars. "
        "How many dollars did Paige earn washing cars last week?",
        96,
    )


def test_named_joint_totals_remain_available_to_comparison_equations(reg):
    number(
        reg,
        "Paige and Quinn have 40 marbles together. Paige has 6 more marbles than Quinn. "
        "How many marbles does Quinn have?",
        17,
    )
