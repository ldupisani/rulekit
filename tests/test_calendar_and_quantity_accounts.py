"""Invented schedule, valuation and stock-composition examples and refusal boundaries."""

from pathlib import Path
import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/curated")).registry


def number(reg, text, value):
    r = solve(text, reg)
    assert r.answer.committed, r.answer
    assert r.value == pytest.approx(value)
    assert not r.deficiencies()
    return r


def weekly():
    return (
        "Nora collects 10 books every day. "
        "On Wednesday she collects 50% more books than the daily average. "
        "How many books does she collect in a week if the library is open from Monday to Friday?"
    )


def test_weekday_exception(reg):
    number(reg, weekly(), 55)


def test_aggregate_relative_clause_supplies_copular_subject(reg):
    number(
        reg,
        "Nora purchased 9 hats. What is the total number of hats that Nora purchased?",
        9,
    )


@pytest.mark.parametrize(
    "old,new",
    [
        ("Wednesday", "Sunday"),
        ("library is", "shop is"),
        ("50%", "50% and 20%"),
        ("10 books", "10 red books"),
    ],
)
def test_weekday_boundaries(reg, old, new):
    # A different site without a site anchor is fine; qualify the premise to
    # require the specific location for this boundary.
    text = "Nora works in the library. " + weekly()
    assert not solve(text.replace(old, new), reg).answer.committed


@pytest.mark.parametrize("recipient", ["cats", "birds"])
@pytest.mark.parametrize(
    "year,expected", [("", 59), (" of 2028", 60), (" of 2027", 59)]
)
def test_named_calendar_months(reg, recipient, year, expected):
    r = number(
        reg,
        f"Nora feeds the {recipient} in January and February{year}. "
        "She feeds them 1/4 cup in the morning and 3/4 cup in the afternoon. "
        "How many cups of food will she need for all two months?",
        expected,
    )
    assert ("non-leap" in r.answer.reason) if not year else ("202" in r.answer.reason)


@pytest.mark.parametrize(
    "old,new",
    [
        ("January and February", "January and January"),
        ("all two months", "all three months"),
        ("in the afternoon", "in the morning"),
        ("1/4 cup", "1/4 foot"),
    ],
)
def test_calendar_boundaries(reg, old, new):
    text = (
        "Nora feeds the birds in January and February. "
        "She feeds them 1/4 cup in the morning and 3/4 cup in the afternoon. "
        "How many cups of food will she need for all two months?"
    )
    assert not solve(text.replace(old, new), reg).answer.committed


def test_short_joint_savings_policy(reg):
    r = number(
        reg,
        "Nora and Iris save half of their income for a trip. "
        "Nora earns $8 per day. Iris earns $2 per day. "
        "How much money will they have saved after a year?",
        1825,
    )
    assert "365" in r.answer.reason


@pytest.mark.parametrize(
    "second",
    ["Iris earns $2 per week.", "Theo earns $2 per day.", "Iris earns £2 per day."],
)
def test_joint_savings_requires_same_group_currency_and_cadence(reg, second):
    text = (
        "Nora and Iris save half of their income for a trip. Nora earns $8 per day. "
        + second
        + " How much money will they have saved after a year?"
    )
    assert not solve(text, reg).answer.committed


def bonus():
    return (
        "Nora earns $48 a day and works for 6 hours. "
        "She earns an extra $12 a day and works 2 hours longer for the bonus. "
        "How much does Nora earn per hour with the bonus?"
    )


def test_both_sides_of_adjusted_rate(reg):
    number(reg, bonus(), 7.5)
    number(reg, bonus().replace("per hour", "per minute"), 0.125)


@pytest.mark.parametrize(
    "old,new",
    [
        ("extra $12 a day", "extra £12 a day"),
        ("2 hours longer", "2 feet longer"),
        ("extra $12 a day", "extra $12 a week"),
        ("Nora earn per hour", "Iris earn per hour"),
    ],
)
def test_adjusted_rate_boundaries(reg, old, new):
    assert not solve(bonus().replace(old, new), reg).answer.committed


def order():
    return (
        "Nora orders 2 kilograms of metal for $4 per kilogram. "
        "She also orders three times that much clay at $2 per kilogram. "
        "How much did everything cost altogether?"
    )


def test_measured_relative_quotes(reg):
    number(reg, order(), 20)
    number(reg, order().replace("$4 per kilogram", "$0.004 per gram"), 20)


@pytest.mark.parametrize(
    "old,new",
    [
        ("per kilogram", "per liter"),
        ("clay at $2", "clay at £2"),
        ("that much clay", "that much red clay"),
        ("She also orders", "Iris also orders"),
    ],
)
def test_measured_quote_boundaries(reg, old, new):
    assert not solve(order().replace(old, new), reg).answer.committed


@pytest.mark.parametrize("act", ["write", "print"])
def test_explicit_uniform_output_extent(reg, act):
    number(
        reg,
        f"Nora {act}s 12 pages per hour. How long will it take her to {act} 2 books of 30 pages each?",
        5,
    )
    number(
        reg,
        f"Nora {act}s 12 pages per hour. How many minutes will it take her to {act} 2 books that are 30 pages each?",
        300,
    )


@pytest.mark.parametrize(
    "text",
    [
        "Nora writes 12 pages per hour. How long will it take her to write 2 books?",
        "Nora writes 12 pages per hour. How long will it take Iris to write 2 books of 30 pages each?",
        "Nora prints 12 pages per hour. How long will it take her to write 2 books of 30 pages each?",
        "Nora prints 0 pages per hour. How long will it take her to print 2 books of 30 pages each?",
    ],
)
def test_output_duration_boundaries(reg, text):
    assert not solve(text, reg).answer.committed


def coins():
    return (
        "Nora exchanged 8 quarters for nickels. "
        "25% of the nickels are silver nickels worth $2 each. "
        "What is the value of Nora's money?"
    )


def test_exchange_then_revalue_subset(reg):
    number(reg, coins(), 21.5)
    number(reg, coins().replace("25%", "50%"), 41)


@pytest.mark.parametrize(
    "old,new",
    [
        ("exchanged", "wants to exchange"),
        ("25%", "26%"),
        ("25%", "125%"),
        ("silver nickels", "silver dimes"),
        ("$2", "£2"),
    ],
)
def test_exchange_boundaries(reg, old, new):
    assert not solve(coins().replace(old, new), reg).answer.committed


def calibration():
    return (
        "For each kilogram of clay Nora produces 2 liters of foam. "
        "On Monday, Nora used 3 kilograms of clay. On Tuesday, Nora used 2 kilograms of clay. "
        "Nora can sell foam for $4 per liter. "
        "How much money did Nora make from selling all the foam?"
    )


def test_nonweather_calibration(reg):
    number(reg, calibration(), 40)


@pytest.mark.parametrize(
    "old,new",
    [
        ("used 2 kilograms of clay", "used 2 kilograms of metal"),
        ("sell foam", "sell oil"),
        ("per liter", "per kilogram"),
        ("On Tuesday", "On Monday"),
    ],
)
def test_calibration_boundaries(reg, old, new):
    assert not solve(calibration().replace(old, new), reg).answer.committed


def transfers():
    return (
        "Nora purchased a box of hats. Nora gave 3 hats to Iris. "
        "Nora gave twice as many as Nora had given Iris to Theo. "
        "If Nora had 2 hats remaining, how many hats did Nora purchase?"
    )


def test_recipient_graph_and_stock_conservation(reg):
    number(reg, transfers(), 11)


@pytest.mark.parametrize(
    "old,new",
    [
        ("given Iris", "given Ava"),
        ("to Theo", "to Iris"),
        ("2 hats remaining", "2 books remaining"),
        ("Nora gave twice", "Iris gave twice"),
    ],
)
def test_transfer_boundaries(reg, old, new):
    assert not solve(transfers().replace(old, new), reg).answer.committed


def sections():
    return (
        "Nora sorts hats from a box. "
        "Nora sorted 2 red hats and 3 blue hats from the top section of the box. "
        "Half the hats on the bottom section of the box were yellow hats. "
        "Then, Nora sorted the remaining hats from the bottom of the box, including 4 green hats. "
        "How many hats did Nora have on the box when Nora started?"
    )


def test_nonpublication_partition_reconstruction(reg):
    number(reg, sections(), 13)


@pytest.mark.parametrize(
    "old,new",
    [
        ("bottom section", "top section"),
        ("Half", "All"),
        ("4 green hats", "4 green books"),
        ("2 red hats and 3 blue hats", "2 red hats and 3 red hats"),
    ],
)
def test_partition_reconstruction_boundaries(reg, old, new):
    assert not solve(sections().replace(old, new), reg).answer.committed


def test_nonliving_recipient_calendar_schedule(reg):
    number(
        reg,
        "Nora supplies the tanks in April and May. "
        "She supplies them 1/4 liter in the morning and 3/4 liter in the afternoon. "
        "How many liters of oil will she need for all two months?",
        61,
    )


def test_month_schedule_preserves_actor_identity(reg):
    text = (
        "The worker A supplies the tanks in April and May. "
        "The worker A supplies them 1/4 liter in the morning and 3/4 liter in the afternoon. "
        "How many liters of oil will the worker A need for all two months?"
    )
    number(reg, text, 61)
    assert not solve(
        text.replace("will the worker A", "will the worker B"), reg
    ).answer.committed
    assert not solve(text.replace("1/4 liter", "-1/4 liter"), reg).answer.committed


def test_recipient_reference_number_is_checked(reg):
    text = (
        "Nora feeds the birds in April and May. "
        "She feeds him 1/4 cup in the morning and 3/4 cup in the afternoon. "
        "How many cups of food will she need for all two months?"
    )
    assert not solve(text, reg).answer.committed


def test_valuation_adjective_does_not_absorb_currency(reg):
    from rulekit.kernel.engine import analyze

    r = analyze("The silver nickels are worth $7 each.", reg)
    assert any(u.surface == "worth" and u.sense() == "adjective" for u in r.units)
    assert any(
        u.features.get("currency_unit") == "dollar" and u.features.get("value") == 7
        for u in r.units
    )


def test_declared_nominal_modifier_selects_its_head(reg):
    from rulekit.kernel.engine import analyze

    r = analyze("The bottom section has books.", reg)
    assert any(
        u.features.get("lemma") == "section" and u.features.get("qualifier") == "bottom"
        for u in r.units
    )


def test_weekday_and_following_actor_remain_separate(reg):
    from rulekit.kernel.engine import analyze

    r = analyze("On Thursday, Iris used 2 liters of oil.", reg)
    assert any(
        u.features.get("lemma") == "thursday" and u.sense() == "noun" for u in r.units
    )
    assert any(u.surface == "Iris" and u.sense() == "name" for u in r.units)


def test_transfer_reconstruction_accepts_nonliving_recipients(reg):
    number(
        reg,
        "Nora purchased a container of coins. Nora gave 3 coins to the box. "
        "Nora gave twice as many as Nora had given the box to the tank. "
        "If Nora had 2 coins remaining, how many coins did Nora purchase?",
        11,
    )


def test_order_purpose_does_not_hide_an_unpriced_collection(reg):
    assert not solve(
        "Nora orders food for a restaurant. " + order(), reg
    ).answer.committed


def test_simple_transfer_reconstruction_reuses_ordinary_transfer_facts(reg):
    number(
        reg,
        "Nora purchased a box of hats. Nora gave 3 hats to Iris. "
        "If Nora had 2 hats remaining, how many hats did Nora purchase?",
        5,
    )


def test_existing_fractional_stock_still_uses_ordinary_transfers(reg):
    number(
        reg,
        "Nora found 16 coins. Nora spent half of the coins. "
        "Nora gave 3 coins to Iris. How many coins does Nora have?",
        5,
    )


def test_output_measure_requires_a_compatible_product(reg):
    assert not solve(
        "Nora writes 12 pages per hour. "
        "How long will it take her to write 2 dresses of 30 pages each?",
        reg,
    ).answer.committed


@pytest.mark.parametrize("product", ["novels", "textbooks"])
def test_output_extent_reuses_publication_categories(reg, product):
    number(
        reg,
        f"Nora prints 20 pages per hour. "
        f"How long will it take her to print 3 {product} of 10 pages each?",
        1.5,
    )


def test_inflected_supply_keeps_nominal_and_predicate_uses(reg):
    from rulekit.kernel.engine import analyze

    noun = analyze("Nora spent $9 on tennis supplies.", reg)
    assert any(
        u.features.get("lemma") == "supply" and u.sense() == "noun" for u in noun.units
    )
    verb = analyze("Nora supplies the tanks.", reg)
    assert any(
        u.features.get("lemma") == "supply" and u.sense() == "verb" for u in verb.units
    )


def test_collection_is_a_nominal_compound_modifier(reg):
    from rulekit.kernel.engine import analyze

    r = analyze("Nora has a collection of books.", reg)
    assert any(
        u.features.get("lemma") == "collection" and u.sense() == "noun" for u in r.units
    )


def test_affine_transfer_chain_with_nonliving_recipients(reg):
    text = (
        "Nora purchased a container of coins. Nora gave 3 coins to the box. "
        "Nora gave twice as many as Nora had given the box to the tank. "
        "Nora gave 1 less than three times as many to the jar as Nora had given to the tank. "
        "If Nora had 2 coins remaining, how many coins did Nora purchase?"
    )
    number(reg, text, 28)
    assert not solve(text.replace("1 less", "20 less"), reg).answer.committed


def test_adjusted_rate_preserves_actor_labels(reg):
    text = (
        "The teacher A earns $48 a day and works for 6 hours. "
        "The teacher A earns an extra $12 a day and works 2 hours longer for the bonus. "
        "How much does the teacher A earn per hour with the bonus?"
    )
    number(reg, text, 7.5)
    assert not solve(
        text.replace("does the teacher A", "does the teacher B"), reg
    ).answer.committed
