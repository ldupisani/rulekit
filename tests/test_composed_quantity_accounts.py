"""Invented compositions of comparisons, cash, measurements and counted units."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/curated")).registry


def number(reg, text, value, **kwargs):
    result = solve(text, reg, **kwargs)
    assert result.answer.committed, result.answer
    assert result.value == pytest.approx(value)
    assert not result.deficiencies()
    return result


@pytest.mark.parametrize("delta", ["fewer", "less"])
def test_coordinated_subject_comparison(reg, delta):
    text = (
        f"Nora has 12 {delta} pears than Iris, and Theo has half as many pears as Nora. "
        "If Iris has 54 pears, how many pears does Theo have?"
    )
    number(reg, text, 21)


def cash():
    return (
        "At a market, Nora sells handmade books for 8 dollars per book. "
        "Today, Nora sells 5 books and is given an extra 6 dollars from an appreciative customer. "
        "Later on, Nora deposits 11 dollars from today's profits into her bank account. "
        "How many dollars is Nora left with after making the deposit?"
    )


@pytest.mark.parametrize(
    "old,new,value",
    [
        ("8 dollars", "8 dollars", 35),
        ("handmade books", "books", 35),
        ("extra 6", "additional 6", 35),
        ("Later on, ", "", 35),
        ("11 dollars", "46 dollars", 0),
    ],
)
def test_sale_cash_and_deposit(reg, old, new, value):
    number(reg, cash().replace(old, new), value)


@pytest.mark.parametrize(
    "old,new",
    [
        ("11 dollars", "47 dollars"),
        ("5 books", "5 apples"),
        ("per book", "per apple"),
        ("her bank account", "Iris's bank account"),
        ("8 dollars", "8 kilograms"),
    ],
)
def test_cash_account_boundaries(reg, old, new):
    assert not solve(cash().replace(old, new), reg).answer.committed


def breakfast():
    return (
        "Nora and Iris had lunch at a cafe. "
        "A slice of bread costs £2, and eggs cost £4 each. "
        "Nora had 3 slices of bread and 1 egg. Iris had 2 slices of bread and 3 eggs. "
        "How much did their lunch cost?"
    )


@pytest.mark.parametrize(
    "old,new,value",
    [
        ("lunch", "lunch", 26),
        ("lunch", "meeting", 26),
        ("£", "$", 26),
        ("cafe", "restaurant", 26),
    ],
)
def test_named_activity_quotes(reg, old, new, value):
    number(reg, breakfast().replace(old, new), value)


@pytest.mark.parametrize(
    "old,new",
    [
        ("£4", "4 kilograms"),
        ("£4", "$4"),
        ("1 egg. Iris had", "1 egg. Theo had"),
        ("A slice of bread", "A cup of bread"),
    ],
)
def test_named_cost_scope_and_units(reg, old, new):
    assert not solve(breakfast().replace(old, new), reg).answer.committed


def outcomes():
    return (
        "Four people gained a total of 86 kilograms of weight. "
        "The first person gained 18 kilograms. "
        "The second person gained 6 kilograms less than the first person. "
        "The two remaining people gained the same amount. "
        "How many kilograms did each of the last two people gain?"
    )


@pytest.mark.parametrize(
    "old,new,value",
    [
        ("6 kilograms less", "6 kilograms less", 28),
        ("6 kilograms less", "6 kilograms more", 22),
        ("kilograms", "grams", 28),
        ("same amount", "equal amount", 28),
    ],
)
def test_relative_member_partition(reg, old, new, value):
    number(reg, outcomes().replace(old, new), value)


@pytest.mark.parametrize(
    "old,new",
    [
        ("Four people", "Five people"),
        ("second person", "fourth person"),
        ("first person.", "third person."),
        ("6 kilograms less", "26 kilograms less"),
        ("same amount", "amount"),
        ("last two people", "last three people"),
    ],
)
def test_partition_completeness(reg, old, new):
    assert not solve(outcomes().replace(old, new), reg).answer.committed


@pytest.mark.parametrize(
    "text,value",
    [
        (
            "A farm produced 40 carrots, 8 fewer potatoes and twice as many peppers as the potatoes. "
            "How many vegetables did the farm produce?",
            136,
        ),
        (
            "A garden produced 40 roses and 10 fewer tulips. How many flowers did the garden produce?",
            70,
        ),
        (
            "A garden produced 40 roses, 10 more tulips and twice as many pears as the tulips. "
            "How many flowers did the garden produce?",
            90,
        ),
    ],
)
def test_relative_item_category_accounts(reg, text, value):
    number(reg, text, value)


@pytest.mark.parametrize(
    "text",
    [
        "A garden produced 5 apples and 8 fewer pears. How many flowers did the garden produce?",
        "A garden produced 5 apples and twice as many pears as the potatoes. How many flowers did the garden produce?",
        "A garden produced 5 apples and 2 fewer pears. It lost 1 apple. How many flowers did the garden produce?",
    ],
)
def test_relative_inventory_boundaries(reg, text):
    assert not solve(text, reg).answer.committed


def forecast():
    return (
        "A painter weighs 75 kg at 5 weeks from a race. "
        "He is on a plan that allows him to lose 2 kg per week until the day of the race. "
        "How much will he weigh on the day of the race?"
    )


@pytest.mark.parametrize(
    "old,new,value",
    [
        ("plan", "plan", 65),
        ("plan", "diet", 65),
        ("lose", "gain", 85),
        ("weeks from", "months from", None),
    ],
)
def test_measurement_projection(reg, old, new, value):
    text = forecast().replace(old, new)
    if value is None:
        assert not solve(text, reg).answer.committed
    else:
        number(reg, text, value)


def tank():
    return (
        "Nora is filling a tank. She fills it halfway. "
        "She spills half the water in the tank. "
        "Nora triples the amount of water in the tank. "
        "The tank is 2 feet long, 3 feet wide, and 4 feet high. "
        "How many cubic feet of water are in the tank?"
    )


def test_three_axis_container_interpretation_is_reported(reg):
    result = number(reg, tank(), 18)
    assert not result.answer.clarification
    assert "interpreting" in result.answer.reason
    assert "rectangular prism" in result.answer.reason
    assert [a.id for a in result.answer.assumptions] == ["rectangular-container"]
    number(reg, tank(), 18, interpretation="rectangular-container")


def pieces():
    return (
        "Nora had 4 cookie pies to share with her 15 classmates and her teacher, Ms. Iris. "
        "If each of the cookie pies were cut into 6 slices and Nora, her classmates, and Ms. Iris all had 1 piece, "
        "how many slices are left?"
    )


def test_counted_group_named_individual_and_owner(reg):
    number(reg, pieces(), 7)


def test_distribution_stock_shortfall_and_alias_boundaries(reg):
    assert not solve(
        pieces().replace("4 cookie pies", "2 cookie pies"), reg
    ).answer.committed
    assert not solve(
        pieces().replace("and Ms. Iris all", "and Ms. Theo all"), reg
    ).answer.committed


def test_partition_retains_the_whole_reference(reg):
    number(reg, pieces().replace("4 cookie pies", "4 birthday cookie pies"), 7)
    assert not solve(
        pieces().replace("4 cookie pies", "4 apple pies"), reg
    ).answer.committed
    assert not solve(
        pieces()
        .replace("4 cookie pies", "4 cookie pies A")
        .replace("each of the cookie pies", "each of the cookie pies B"),
        reg,
    ).answer.committed


def packages():
    return (
        "It is Ira's turn to provide a snack for the baseball team after the game and he has decided to bring rice. "
        "The rice comes in packs of 4 individual pouches. "
        "Ira has 9 members on his baseball team, plus 2 coaches and 1 helper. "
        "How many packs of rice does he need to buy?"
    )


def test_individual_unit_interpretation_and_whole_rounding(reg):
    result = number(reg, packages(), 3)
    assert not result.answer.clarification
    assert "complete roster" in result.answer.reason
    assert "one individual unit per recipient" in result.answer.reason
    number(reg, packages(), 3, interpretation="one-unit-each")
    number(
        reg,
        packages().replace("9 members", "10 members"),
        4,
    )


def test_unspecified_package_units_still_need_a_requirement(reg):
    text = packages().replace("individual pouches", "pouches")
    result = solve(text, reg)
    assert not result.answer.committed
    assert result.answer.clarification
    number(reg, text, 3, interpretation="one-unit-each")


@pytest.mark.parametrize(
    "old,new",
    [
        ("4 feet high", "4 feet long"),
        ("3 feet wide, and 4 feet high", "3 feet wide"),
        ("The tank is", "The tank is a cylinder. The tank is"),
        ("The tank is", "The round tank is"),
    ],
)
def test_rectangular_interpretation_needs_complete_uncontradicted_dimensions(
    reg, old, new
):
    assert not solve(tank().replace(old, new), reg).answer.committed


@pytest.mark.parametrize("old", ["The tank is", "water in the tank."])
def test_unmodeled_container_descriptor_preserves_shape_clarification(reg, old):
    text = tank().replace(old, old.replace("tank", "round tank"))
    result = solve(text, reg)
    assert not result.answer.committed
    assert result.answer.clarification


def test_explicit_serving_requirement(reg):
    text = packages().replace(
        "How many packs", "Each person needs 2 pouches. How many packs"
    )
    number(reg, text, 6)
    assert not solve(text.replace("Each person", "Each coach"), reg).answer.committed


def test_currency_and_mass_remain_distinct(reg):
    result = solve("A box costs £3. How many grams does the box weigh?", reg)
    assert not result.answer.committed
    number(
        reg,
        breakfast()
        .replace("£", "£")
        .replace("£2", "2 pounds sterling")
        .replace("£4", "4 pounds sterling"),
        26,
    )


def test_relative_retail_inventory(reg):
    number(
        reg,
        "A store sold 24 shirts, 4 fewer pants and twice as many coats as the pants. "
        "How many clothes did the store sell?",
        84,
    )


def test_plain_production_remains_an_ordinary_quantity(reg):
    result = solve(
        "A garden produced 20 potatoes. How many potatoes did the garden produce?", reg
    )
    from rulekit.kernel.model import BatchEvidence

    assert not result.document.store.by_kind(BatchEvidence)


def test_container_overflow_and_competing_content(reg):
    assert not solve(
        tank().replace("half the water", "one-tenth of the water"),
        reg,
        interpretation="rectangular-container",
    ).answer.committed
    assert not solve(
        tank().replace("amount of water", "amount of oil"),
        reg,
        interpretation="rectangular-container",
    ).answer.committed


def test_explicit_rectangular_container(reg):
    result = number(reg, tank().replace("The tank is", "The rectangular tank is"), 18)
    assert "interpreting" not in result.answer.reason
    assert not result.answer.assumptions


@pytest.mark.parametrize("role", ["boxer", "collector"])
def test_measured_role_does_not_change_global_person_classification(reg, role):
    text = (
        f"A {role} weighs 80 kg at 3 weeks from a race. "
        "He is on a diet that allows him to lose 2 kg per week until the day of the race. "
        "How much will he weigh on the day of the race?"
    )
    assert not reg.word_in_category(role, "animate")
    assert not reg.category_terms_disjoint("flower", role)
    number(reg, text, 74)


def test_competing_measured_subjects_do_not_resolve_by_recency(reg):
    text = (
        "A boxer weighs 80 kg at 3 weeks from a race. "
        "A collector weighs 70 kg at 3 weeks from a race. "
        "He is on a diet that allows him to lose 2 kg per week until the day of the race. "
        "How much will he weigh on the day of the race?"
    )
    assert not solve(text, reg).answer.committed


@pytest.mark.parametrize("phrase", ["The slice of bread", "Slices of bread"])
def test_serving_quote_needs_a_generic_unit_or_explicit_distributor(reg, phrase):
    assert not solve(
        breakfast().replace("A slice of bread", phrase), reg
    ).answer.committed


def test_fill_object_refers_to_the_container(reg):
    from rulekit.kernel.reference_identity import reference_from_unit

    result = number(reg, tank(), 18, interpretation="rectangular-container")
    object_unit = next(u for u in result.premises[1].units if u.surface == "it")
    assert reference_from_unit(object_unit).head == "tank"


def test_unresolved_container_is_not_replaced_by_the_person(reg):
    text = tank().replace(
        "Nora is filling a tank.", "Nora is filling a tank. Nora is filling a bucket."
    )
    assert not solve(text, reg, interpretation="rectangular-container").answer.committed


def test_plural_role_does_not_imply_one_named_recipient(reg):
    assert not solve(
        pieces().replace("her teacher,", "her teachers,"), reg
    ).answer.committed


def test_comparison_questions_keep_their_existing_reference_contract(reg):
    number(
        reg,
        "The teacher has 12 cards and 4 fewer books. How many cards does the teacher have?",
        12,
    )
    assert not solve(
        "A garden produced 8 roses and 2 fewer tulips. "
        "How many flowers did the garden produce yesterday?",
        reg,
    ).answer.committed


def test_missing_participant_order_is_not_zero(reg):
    assert not solve(
        breakfast().replace("Iris had 2 slices of bread and 3 eggs. ", ""), reg
    ).answer.committed


def test_explicitly_different_container_label_is_preserved(reg):
    text = (
        tank()
        .replace("a tank.", "a tank A.")
        .replace("water in the tank.", "water in the tank B.", 1)
    )
    assert not solve(text, reg, interpretation="rectangular-container").answer.committed


def test_unknown_class_membership_cannot_be_excluded(reg):
    assert not solve(
        "A garden produced 20 roses and 5 fewer backpacks. "
        "How many flowers did the garden produce?",
        reg,
    ).answer.committed
