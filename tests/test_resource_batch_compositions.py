"""Invented partitions, resource plans, opening stocks and finite daily accounts."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve, analyze
from rulekit.kernel.affine_graph import AffineError
from rulekit.kernel.evaluate import ArithmeticLog
from rulekit.kernel.quantity_ratios import quantity_through_ratios


@pytest.fixture(scope="module")
def project():
    return load_project(Path("projects/curated"))


@pytest.fixture(scope="module")
def reg(project):
    return project.registry


def number(reg, text, value):
    result = solve(text, reg)
    assert result.value == pytest.approx(value), result.answer
    assert not result.deficiencies()
    return result


def test_quantity_ratios_convert_units_only_within_the_same_resource(reg):
    links = [
        (("bottle", "paint"), ("box", "paint"), 2, 1),
        (("milliliter", "paint"), ("bottle", "paint"), 250, 1),
    ]
    assert (
        quantity_through_ratios(
            4,
            ("box", "paint"),
            ("liter", "paint"),
            links,
            reg,
            ArithmeticLog(),
        )
        == 2
    )
    assert (
        quantity_through_ratios(
            2,
            ("liter", "paint"),
            ("box", "paint"),
            links,
            reg,
            ArithmeticLog(),
        )
        == 4
    )
    for target in (("liter", "glue"), ("meter", "paint")):
        with pytest.raises(AffineError):
            quantity_through_ratios(
                4, ("box", "paint"), target, links, reg, ArithmeticLog()
            )
    with pytest.raises(AffineError):
        quantity_through_ratios(
            4,
            ("box", "paint"),
            ("liter", "paint"),
            [*links, (("gram", "glue"), ("jar", "glue"), 50, 1)],
            reg,
            ArithmeticLog(),
        )


@pytest.mark.parametrize(
    "text,head,sense",
    [
        ("Leto continued writing a book.", "write", "verb"),
        ("Leto continued painting a wall.", "paint", "verb"),
        ("Leto continued the painting.", "painting", "noun"),
        ("Leto studies writing.", "writing", "noun"),
        ("The boat can transport in three days.", "transport", "verb"),
        ("The transport costs $5.", "transport", "noun"),
    ],
)
def test_governed_predicates_and_nominal_compounds_stay_distinct(
    reg, text, head, sense
):
    reading = analyze(text, reg)
    assert any(
        u.features.get("lemma") == head and u.sense() == sense for u in reading.units
    )


def scoped_sales():
    return (
        "A store makes a fifth of its sales in the book section, a quarter of its sales "
        "in the toy section, and the rest in the garden section. They made 40 sales today. "
        "How many sales were in the garden section?"
    )


def test_fractional_output_sections_and_original_basis(reg):
    number(reg, scoped_sales(), 22)
    number(reg, scoped_sales().replace(" today.", "."), 22)
    number(reg, scoped_sales().replace("garden section?", "book section?"), 8)
    number(reg, scoped_sales().replace("garden section?", "toy section?"), 10)
    number(
        reg,
        scoped_sales().replace(
            "quarter of its sales", "quarter of its remaining sales"
        ),
        24,
    )


def test_physical_stock_uses_the_same_scoped_partition(reg):
    text = (
        "Selene has a quarter of her toys in the first section, a fifth of her toys "
        "in the second section, and the rest in the third section. Selene made 80 toys. "
        "How many toys were in the third section?"
    )
    number(reg, text, 44)
    number(reg, text.replace("made 80 toys", "has 80 toys"), 44)
    for event in ("lost", "sold", "wants"):
        assert not solve(
            text.replace("made 80 toys", f"{event} 80 toys"), reg
        ).answer.committed


@pytest.mark.parametrize(
    "before,after",
    [
        ("a fifth", "four fifths"),
        ("40 sales", "41 sales"),
        ("toy section", "book section"),
        ("its sales", "its red sales"),
        ("garden section?", "fabric section?"),
        ("They made", "He made"),
    ],
)
def test_scoped_partition_does_not_erase_restrictions_or_overlap(reg, before, after):
    assert not solve(scoped_sales().replace(before, after), reg).answer.committed


def classified():
    return (
        "Selene buys 4 boxes of magic cards. Each box has 12 cards and one third of those "
        "cards are uncommon. How many uncommon cards did Selene get?"
    )


@pytest.mark.parametrize(
    "question,expected",
    [
        ("How many uncommon cards did Selene get?", 16),
        ("How many cards did Selene get?", 48),
        ("How many uncommon magic cards did Selene get?", 16),
        ("How many magic cards did Selene get?", 48),
    ],
)
def test_classification_preserves_package_basis_and_whole_queries(
    reg, question, expected
):
    number(reg, classified().rsplit("How many", 1)[0] + question, expected)


def test_package_classification_also_counts_defective_supplies(reg):
    text = classified().replace("magic cards", "stickers").replace("cards", "stickers")
    number(reg, text.replace("uncommon", "defective"), 16)


@pytest.mark.parametrize(
    "before,after",
    [
        ("12 cards", "5 cards"),
        ("uncommon cards did", "uncommon red cards did"),
        ("uncommon cards did", "Selene's uncommon cards did"),
        ("Selene get?", "Daro get?"),
        ("one third", "four thirds"),
        ("those cards", "those marbles"),
        ("magic cards.", "magic cards and 2 boxes of marbles."),
    ],
)
def test_classification_requires_integral_and_identified_item_shares(
    reg, before, after
):
    assert not solve(classified().replace(before, after), reg).answer.committed


def repeated_prices():
    return (
        "Selene took 8 pills a day for 5 days. Of these 8 pills, 3 pills cost $2 each, "
        "and the other pills each cost $4 more. "
        "How much did Selene spend in total on the pills?"
    )


def test_repeated_exhaustive_partition_prices(reg):
    r = number(reg, repeated_prices(), 180)
    assert "repeated-partition-composition" in {a.id for a in r.answer.assumptions}
    number(reg, repeated_prices().replace("8 pills", "7 pills"), 150)
    number(reg, repeated_prices().replace("a day", "per day"), 180)


def test_repeated_supply_prices_apply_across_complete_calendar_periods(reg):
    text = repeated_prices().replace("took", "used").replace("pills", "stickers")
    text = text.replace("a day for 5 days", "per month for one year")
    number(reg, text, 432)
    number(reg, text.replace("one year", "0.5 years"), 216)
    assert not solve(text.replace("used", "took"), reg).answer.committed
    assert not solve(text.replace("one year", "60 days"), reg).answer.committed


@pytest.mark.parametrize(
    "before,after",
    [
        ("Of these 8", "Of these 9"),
        ("on the pills?", "on the other pills?"),
        ("on the pills?", "on the cards?"),
        ("3 pills cost", "9 pills cost"),
        ("Selene spend", "Daro spend"),
        ("$4 more", "$4 less"),
    ],
)
def test_partition_prices_need_a_complete_matching_population(reg, before, after):
    assert not solve(repeated_prices().replace(before, after), reg).answer.committed


def supply():
    return (
        "Selene decides to bring 3 boxes of juice. Each box holds 2 bottles of juice. "
        "Each bottle of juice serves 4 people. How many people can Selene serve?"
    )


def test_nested_supply_units_support_recipient_capacity(reg):
    r = number(reg, supply(), 24)
    assert "full-capacity-plan" in {a.id for a in r.answer.assumptions}
    number(reg, supply().replace("3 boxes", "5 boxes"), 40)


def test_exact_service_plan_can_supply_a_meal(reg):
    capacity = "Each bottle of juice will hold enough juice for 3 people's meal. "
    plan = (
        "Selene decides to bring 3 boxes of juice, each of which holds 2 bottles of juice, "
        "and this will be the exact amount she needs for everyone's meal. "
    )
    question = "How many people is Selene serving with the meal?"
    text = capacity + plan + question
    number(reg, text, 18)
    cosmetics = text.replace("juice", "lip gloss").replace("meal", "makeup")
    number(reg, cosmetics.replace("serving", "painting"), 18)
    assert not solve(text.replace("serving", "painting"), reg).answer.committed
    assert not solve(text.replace("the meal?", "makeup?"), reg).answer.committed
    assert not solve(
        capacity + supply().split("Each bottle")[0] + question, reg
    ).answer.committed


@pytest.mark.parametrize(
    "before,after",
    [
        ("bottles of juice", "bottles of water"),
        ("2 bottles", "2 tubes"),
        ("Selene serve?", "Daro serve?"),
        ("can Selene serve?", "did Selene serve?"),
        ("3 boxes", "1.5 boxes"),
    ],
)
def test_supply_capacity_is_not_actual_usage_or_an_unconnected_unit_chain(
    reg, before, after
):
    assert not solve(supply().replace(before, after), reg).answer.committed


def repair(object="bicycle"):
    return (
        f"Selene is fixing a {object}. Selene needs 2 ml of oil to fix each wheel. "
        f"Selene needs 3 ml of oil to fix the rest of the {object}. "
        f"How much oil does Selene need in total to fix the {object}?"
    )


@pytest.mark.parametrize(
    "object,expected", [("bicycle", 7), ("tricycle", 9), ("car", 11), ("boat", 3)]
)
def test_shared_component_attributes_supply_requirement_populations(
    reg, object, expected
):
    r = number(reg, repair(object), expected)
    assert "ordinary-component-count" in {a.id for a in r.answer.assumptions}


def test_requirement_unit_question_converts_declared_aliases(reg):
    number(reg, repair().replace("How much oil", "How many milliliters of oil"), 7)


def test_component_work_reuses_counts_for_repairs_and_cleaning(reg):
    text = repair().replace("fixing", "repairing").replace("fix", "repair")
    text = text.replace("ml of oil", "meters of tape").replace(
        "How much oil", "How much tape"
    )
    number(reg, text, 7)

    text = repair("cow").replace("fixing", "cleaning").replace("fix", "clean")
    text = text.replace("wheel", "leg").replace("ml of oil", "liters of water")
    text = text.replace("How much oil", "How much water")
    number(reg, text, 11)

    for clause in (
        "is cleaning",
        "to clean each",
        "to clean the rest",
        "to clean the cow?",
    ):
        mixed = text.replace(clause, clause.replace("clean", "repair"))
        assert not solve(mixed, reg).answer.committed


@pytest.mark.parametrize(
    "before,after",
    [
        ("a bicycle", "a box"),
        ("fix the bicycle?", "fix the car?"),
        ("3 ml of oil", "3 ml of water"),
        ("each wheel", "each wing"),
    ],
)
def test_unknown_components_or_other_resources_are_not_assumed(reg, before, after):
    assert not solve(repair().replace(before, after), reg).answer.committed


def transport():
    return (
        "The boat makes 3 trips per day. The boat can carry 8 people per trip. "
        "How many people can the boat transport in 3 days?"
    )


def test_scheduled_operation_capacity_uses_complete_periods(reg):
    r = number(reg, transport(), 72)
    assert "full-capacity-plan" in {a.id for a in r.answer.assumptions}
    number(reg, transport().replace("transport", "carry"), 72)
    number(reg, transport().replace("3 days?", "72 hours?"), 72)
    number(
        reg,
        transport().replace("trips", "journeys").replace("per trip", "per journey"),
        72,
    )


def test_scheduled_capacity_can_cross_exact_duration_units(reg):
    text = transport().replace("boat", "train").replace("per day", "per month")
    number(reg, text.replace("3 days?", "one year?"), 288)
    number(reg, text.replace("3 days?", "0.5 years?"), 144)
    assert not solve(text.replace("3 days?", "60 days?"), reg).answer.committed
    text = transport().replace("per day", "per hour")
    number(reg, text.replace("3 days?", "7200 seconds?"), 48)
    assert not solve(text.replace("3 days?", "5400 seconds?"), reg).answer.committed


@pytest.mark.parametrize(
    "before,after",
    [
        ("can the boat transport", "did the boat transport"),
        ("3 days?", "1.5 days?"),
        ("3 days?", "3 meters?"),
        ("per trip", "per boat"),
    ],
)
def test_transport_capacity_does_not_claim_actual_passengers(reg, before, after):
    assert not solve(transport().replace(before, after), reg).answer.committed


def constrained(item="fish", loss=False):
    query = f"How many more {item} would Selene have in the first bucket than the second bucket"
    if loss:
        query += f" if one of the first bucket {item} destroys another"
    return (
        f"Selene has two buckets. The first bucket is twice the size of the second bucket. "
        f"There are 36 liters of water in the first bucket. Selene follows the rule of "
        f"one liter of water per inch of {item}. If Selene keeps three-inch {item} "
        f"in the second bucket and four-inch {item} in the first bucket, " + query + "?"
    )


def test_resource_constrained_populations_keep_ordinal_scope_identity(reg):
    r = number(reg, constrained(), 3)
    assert "proportional-fully-stocked-containers" in {
        a.id for a in r.answer.assumptions
    }
    number(reg, constrained(loss=True), 2)
    number(reg, constrained("cars"), 3)
    number(reg, constrained("cars", True), 2)
    text = constrained("cars").replace("water", "sand")
    number(reg, text.replace("liters", "kilograms").replace("liter", "kilogram"), 3)


@pytest.mark.parametrize(
    "before,after",
    [
        ("twice the size", "twice the length"),
        ("two buckets", "three buckets"),
        ("in the second bucket and", "in the first bucket and"),
        ("There are 36 liters", "There are 0 liters"),
        ("rule of one liter", "rule of zero liters"),
    ],
)
def test_container_comparisons_do_not_merge_scopes_or_invent_geometry(
    reg, before, after
):
    assert not solve(
        constrained(loss=True).replace(before, after), reg
    ).answer.committed


def opening():
    return (
        "Leto can write 4 pages per minute. Leto continued writing a book today. "
        "Leto wrote for 10 minutes. Leto removed 6 pages. "
        "In all, the book had 70 pages by the end of today. "
        "How many pages did Leto start with today?"
    )


def test_opening_content_is_closing_less_output_plus_corrections(reg):
    r = number(reg, opening(), 36)
    assert "constant-stated-output-rate" in {a.id for a in r.answer.assumptions}
    number(reg, opening().replace("10 minutes", "0.25 hours"), 16)
    number(reg, opening().replace("10 minutes", "600 seconds"), 36)


def test_manufacturing_project_reuses_the_content_balance(reg):
    text = (
        "Leto can produce 3 toys per minute. Today at work, Leto continued working on a project "
        "he started producing yesterday. Leto produced for 8 minutes. Leto removed 4 toys. "
        "In all, the project had 41 toys by the end of today. "
        "How many toys did Leto start with today?"
    )
    number(reg, text, 21)


def test_future_output_cannot_fund_an_earlier_removal(reg):
    text = opening().replace("removed 6 pages", "removed 100 pages")
    text = text.replace("In all,", "Leto wrote for 25 minutes. In all,")
    assert not solve(text, reg).answer.committed


@pytest.mark.parametrize(
    "before,after",
    [
        ("70 pages", "20 pages"),
        ("removed 6 pages", "removed 6 sentences"),
        ("the book had", "the paper had"),
        ("start with today?", "start with yesterday?"),
        ("Leto start", "Selene start"),
        ("can write", "cannot write"),
        ("the end of", "the beginning of"),
    ],
)
def test_opening_balance_requires_same_actor_resource_product_and_period(
    reg, before, after
):
    assert not solve(opening().replace(before, after), reg).answer.committed


def daily():
    return (
        "There is very little car traffic on Birch Road. During the week, most cars pass it "
        "on Tuesday - 30. On Monday, 20% less than on Tuesday, and on Wednesday, 2 more cars "
        "than on Monday. On Thursday and Friday, it is about 8 cars each day. "
        "On the weekend, traffic drops to 4 cars per day. "
        "How many cars travel down Birch Road from Monday through Sunday?"
    )


def test_explicit_calendar_graph_reports_approximations(reg):
    r = number(reg, daily(), 104)
    assert "Approximate" in r.answer.reason
    assert "approximate-calendar-total" in {a.id for a in r.answer.assumptions}
    number(reg, daily().replace("During the week", "Over the week"), 104)


def test_exact_daily_counts_do_not_report_an_estimate(reg):
    r = number(reg, daily().replace("about 8", "8"), 104)
    assert not r.answer.assumptions


def test_direct_pedestrian_counts_use_the_same_finite_calendar(reg):
    text = (
        "On Monday, 5 people passed Birch Road. On Tuesday, 6 people passed Birch Road. "
        "How many people travel down Birch Road from Monday through Tuesday?"
    )
    r = number(reg, text, 11)
    assert not r.answer.assumptions


@pytest.mark.parametrize(
    "before,after",
    [
        ("Thursday and Friday", "Thursday and Thursday"),
        ("During the week", "During the month"),
        ("8 cars each day", "8 cars each hour"),
        ("2 more cars", "20 more cars"),
        ("Monday through Sunday", "Monday through Friday"),
        ("4 cars per day", "4 cars per hour"),
        ("on Monday.", "on Wednesday."),
    ],
)
def test_calendar_accounts_need_consistent_anchored_complete_days(reg, before, after):
    assert before in daily()
    assert not solve(daily().replace(before, after), reg).answer.committed


def test_existing_combined_comparison_keeps_grammar_coverage(reg):
    number(
        reg,
        "Selene has 18 more hamsters than Daro. Daro has 32 hamsters. "
        "How many hamsters do they have in total?",
        82,
    )


def test_container_holdings_keep_the_ordinary_quantity_contract(reg):
    from rulekit.kernel.model import Quantity, BatchEvidence

    result = number(
        reg,
        "Selene has 4 boxes. Daro has 7 boxes. How many boxes do they have in total?",
        11,
    )
    assert len(list(result.store.by_kind(Quantity))) == 2
    assert not list(result.store.by_kind(BatchEvidence))
