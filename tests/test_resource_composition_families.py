"""Invented analogues of recurring budgets, material regions and closed allocations."""
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def registry():
    return load_project(Path("projects/curated")).registry


def cyclic_story():
    return (
        "Dena spends $60 per month on baseball supplies. Her season is 3 months long. "
        "She wants to save during the remaining months by mowing lawns. "
        "She charges $5 for each. "
        "How many jobs does Dena need to average per month to save for her supplies?"
    )


def area_story(material="cloth"):
    return (
        f"Fia is cutting {material} to make panels. "
        "She cuts a 5 foot by 3 foot rectangle for the bedroom, "
        "and a 2 foot by 3 foot rectangle for the living room. "
        f"The roll of {material} is 12 feet by 9 feet. "
        f"How much {material} is left in square feet?"
    )


def distribution_story(item="marbles", unit="bags", people="friends"):
    singular = {"bags": "bag", "boxes": "box"}[unit]
    return (
        f"Fia had six {unit} of {item} with the same number of {item} in each {singular}. "
        f"She kept six {item} and shared the remaining {item} equally with her four {people}. "
        f"Her {people} received three {item} each. "
        f"How many {item} are in each {singular}?"
    )


def purchase_story(first="books", second="marbles", unit="box", plural="boxes"):
    return (
        f"Fia bought 3 {plural} of {first} and 5 {plural} of {second}. "
        f"Each {unit} of {first} costs $8 and each {unit} of {second} costs $2. "
        f"How much more did Fia spend on {first} than on {second}?"
    )


def stored_story():
    return (
        "Dena received $30. "
        "She spent a fifth of it on a book and put half of the rest in her savings account. "
        "Dena put the remaining money in her wallet. "
        "Her cat got ahold of her wallet and destroyed all the money inside except $2. "
        "How many dollars did Dena lose?"
    )


def assert_number(text, registry, value):
    result = solve(text, registry)
    assert result.answer.committed, result.answer.reason
    assert result.value == pytest.approx(value)
    assert result.deficiencies() == []
    return result


def test_annual_complementary_saving_window(registry):
    result = assert_number(cyclic_story(), registry, 4)
    assert "year" in result.answer.reason and "9 saving periods" in result.answer.reason


@pytest.mark.parametrize("extra", [
    "Dena saved during the year. ",
    "Cato saved during the remaining months. ",
    "Dena worked before Monday. ",
])
def test_saving_window_does_not_excuse_a_separate_temporal_event(registry, extra):
    text = cyclic_story().replace("She charges", extra + "She charges")
    assert not solve(text, registry).answer.committed


def test_an_explicit_activity_period_matches_the_expense_purpose(registry):
    assert_number(cyclic_story().replace("Her season", "Her baseball season"), registry, 4)
    assert not solve(cyclic_story().replace("Her season", "Her tennis season"), registry).answer.committed


@pytest.mark.parametrize("phrase", [
    "She wants to use the months she is not playing baseball to save up by mowing lawns.",
    "She wants to use the months she's not playing baseball to save up by raking and mowing lawns.",
    "She wants to use the months she's not playing baseball to save up by raking, shovelling, and mowing lawns.",
])
def test_saving_plan_paraphrases_and_task_lists(registry, phrase):
    text = cyclic_story().replace("She wants to save during the remaining months by mowing lawns.", phrase)
    assert_number(text, registry, 4)


def test_seasonal_costs_can_fund_other_purchase_categories_and_services(registry):
    assert_number(cyclic_story().replace("baseball supplies", "clothes")
                  .replace("her supplies", "her clothes")
                  .replace("mowing lawns", "washing cars"), registry, 4)


@pytest.mark.parametrize("before,after", [
    ("3 months", "12 months"), ("3 months", "15 months"),
    ("$5", "$0"), ("Her season is 3 months long. ", ""),
    ("She charges $5 for each. ", ""), ("her supplies?", "Cato's supplies?"),
    ("She charges", "Cato charges"),
    ("mowing lawns", "mowing cars"), ("mowing lawns", "washing lawns"),
])
def test_cyclic_budget_needs_a_closed_compatible_window(registry, before, after):
    assert not solve(cyclic_story().replace(before, after), registry).answer.committed


@pytest.mark.parametrize("material", ["cloth", "paper", "cardboard"])
def test_material_area_remainder_across_materials(registry, material):
    assert_number(area_story(material), registry, 87)


def test_area_unit_conversion_applies_to_both_dimensions(registry):
    assert_number(area_story().replace("left in square feet", "left in square inches"), registry, 12528)


def test_explicit_material_cut_needs_no_fabrication_introduction(registry):
    assert_number(
        "The sheet of paper is 12 feet by 9 feet. "
        "Fia cuts a 5 foot by 3 foot rectangle of paper. "
        "How much paper is left in square feet?", registry, 93,
    )


@pytest.mark.parametrize("before,after", [
    ("12 feet by 9 feet", "0 feet by 9 feet"),
    ("5 foot by 3 foot", "15 foot by 3 foot"),
    ("2 foot by 3 foot", "2 hours by 3 foot"),
    ("roll of cloth", "roll of paper"),
    ("Fia is cutting cloth to make panels. ", ""),
    ("square feet?", "feet?"),
    ("3 foot rectangle", "3 foot rectangles"),
])
def test_material_regions_reject_missing_scope_and_incompatible_dimensions(registry, before, after):
    assert not solve(area_story().replace(before, after), registry).answer.committed


@pytest.mark.parametrize("item,unit,people", [
    ("marbles", "bags", "friends"), ("pencils", "boxes", "workers"),
    ("apples", "bags", "monkeys"),
])
def test_uniform_contents_reconstruct_the_original_stock(registry, item, unit, people):
    assert_number(distribution_story(item, unit, people), registry, 3)


@pytest.mark.parametrize("before,after", [
    ("with her", "among her"),
    ("same number", "equal number"),
    ("How many marbles are in each bag?", "How many marbles does each bag contain?"),
])
def test_uniform_content_phrasings(registry, before, after):
    assert_number(distribution_story().replace(before, after), registry, 3)


@pytest.mark.parametrize("before,after", [
    ("six bags", "seven bags"), ("four friends", "0 friends"),
    ("same number", "number"), ("Her friends received", "Cato's friends received"),
    ("marbles are in each bag", "pencils are in each bag"),
])
def test_uniform_content_does_not_guess_counts_or_owners(registry, before, after):
    assert not solve(distribution_story().replace(before, after), registry).answer.committed


@pytest.mark.parametrize("first,second,unit,plural", [
    ("books", "marbles", "box", "boxes"),
    ("ice cream", "frozen yogurt", "carton", "cartons"),
    ("water", "vinegar", "bottle", "bottles"),
])
def test_item_cost_comparison_uses_package_quotes(registry, first, second, unit, plural):
    result = assert_number(purchase_story(first, second, unit, plural), registry, 14)
    from rulekit.kernel.model import Quantity
    for quantity in result.store.by_kind(Quantity):
        assert quantity.measure_ref.head == unit
        assert quantity.content_ref is not None


def test_reversed_less_comparison_and_payment_vocabulary(registry):
    text = purchase_story().replace("more did Fia spend on books than on marbles", "less did Fia pay for marbles than for books")
    assert_number(text, registry, 14)


def test_scoped_package_quotes_cannot_be_used_as_unscoped_item_prices(registry):
    text = purchase_story().split("How much")[0] + "How much did Fia spend?"
    assert not solve(text, registry).answer.committed


@pytest.mark.parametrize("before,after", [
    ("Each box of books", "Each bag of books"),
    ("and each box of marbles costs $2.", "."),
    ("3 boxes", "3.5 boxes"),
    ("bought", "wants"),
    ("boxes of books and", "boxes of red books and"),
    ("3 boxes of books", "3 red boxes of books"),
    ("more did Fia spend on books than on marbles", "more did Fia spend on marbles than on books"),
])
def test_purchase_quotes_require_matching_units_and_transactions(registry, before, after):
    assert not solve(purchase_story().replace(before, after), registry).answer.committed


def test_attached_package_prices_keep_the_existing_purchase_cost_route(registry):
    result = solve("Fia buys 3 pounds of sugar for $18, a box of apples that costs "
                   "half the price of the sugar, and a bottle of water that costs "
                   "twice the price of the sugar. How much does Fia spend?", registry)
    assert result.value == 63


def test_ordered_allocations_then_loss(registry):
    assert_number(stored_story(), registry, 10)


@pytest.mark.parametrize("before,after", [
    ("a fifth", "20%"), ("the rest", "the remainder"),
    ("cat", "dog"), ("except $2", "but $2"),
    ("savings account", "account"), ("wallet", "purse"),
])
def test_stored_cash_paraphrases_preserve_the_pool(registry, before, after):
    assert_number(stored_story().replace(before, after), registry, 10)


@pytest.mark.parametrize("actor", ["Her dog", "The machine"])
def test_explicit_store_loss_needs_no_access_context(registry, actor):
    assert_number(stored_story().replace(
        "Her cat got ahold of her wallet and destroyed all the money inside except $2.",
        f"{actor} shredded all the money in her wallet except $2.",
    ), registry, 10)


@pytest.mark.parametrize("before,after", [
    ("except $2", "except $20"),
    ("half of the rest", "two thirds of it"),
    ("Dena put the remaining money in her wallet. ", ""),
    ("Her cat got ahold of her wallet", "Her cat got ahold of his wallet"),
    ("in her wallet.", "in her savings account."),
    ("in her wallet.", "in her account."),
])
def test_loss_declines_when_the_stored_pool_is_not_determined(registry, before, after):
    assert not solve(stored_story().replace(before, after), registry).answer.committed


@pytest.mark.parametrize("make_story", [cyclic_story, area_story, distribution_story, purchase_story, stored_story])
def test_closed_calculations_do_not_ignore_an_extra_transaction(registry, make_story):
    text = make_story()
    index = text.index("How ")
    assert not solve(text[:index] + "Cato bought 7 books. " + text[index:], registry).answer.committed


@pytest.mark.parametrize("project", ["curated", "gsm8k"])
def test_reusable_vocabulary_is_owned_by_the_shared_core(project):
    loaded = load_project(Path("projects") / project)
    for word in ("baseball", "bolt", "carton", "cloth", "curtain", "fabric", "foot",
                 "frozen yoghurt", "frozen yogurt", "ice cream", "kept", "purse", "rectangle", "sheet"):
        assert "core-english" in loaded.source_index.lexicon[word].path.parts


@pytest.mark.parametrize("rule_id", [
    "arithmetic/cut-measured-region",
    "arithmetic/remainder-to-owned-store", "arithmetic/uniform-container-stock",
])
def test_qualified_constructions_have_realizable_generation_witnesses(rule_id):
    from rulekit.generation import generate_candidate
    candidate = generate_candidate(load_project(Path("projects/curated")), rule_id=rule_id, seed=0)
    assert candidate.target_status in {"matched", "shadowed"}


def test_a_cut_continuation_requires_its_same_sentence_predicate():
    from rulekit.generation import GenerationError, generate_candidate, retest_candidate
    project = load_project(Path("projects/curated"))
    rule = "arithmetic/cut-measured-region-continuation"
    with pytest.raises(GenerationError, match="preceding_verb_category"):
        generate_candidate(project, rule_id=rule, seed=0)
    candidate = retest_candidate(
        project, rule_id=rule, seed=0, origin="reading",
        sentence="Fia cuts a 3 foot by 4 foot rectangle and a 2 foot by 2 foot rectangle.",
    )
    assert candidate.target_status == "matched"
