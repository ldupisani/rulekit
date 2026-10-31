"""Invented source ellipsis, explicit stock references and final balances."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_ask_scenario, generate_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import BatchEvidence, FractionQuantity


@pytest.fixture(scope="module")
def project():
    return load_project(Path("projects/curated"))


def allocation():
    return ("Dena bought 12 kilograms of clay to make models. "
            "She used one-half of it for red models, one-fourth of it for blue models, "
            "and one-third of the remaining clay for green models. "
            "How many kilograms of clay are left after making those three kinds of models?")


def number(project, text, expected):
    result = solve(text, project.registry)
    assert result.answer.committed, result.answer.reason
    assert result.value == pytest.approx(expected)
    assert result.deficiencies() == []
    return result


@pytest.mark.parametrize("before,after", [
    ("one-half of it", "one-half"),
    ("one-half of it", "one-half of the clay"),
    ("one-fourth of it", "one-fourth"),
    ("one-fourth of it", "one-fourth of the clay"),
    ("the remaining clay", "the remainder"),
    ("the remaining clay", "the rest"),
    ("the remaining clay", "the remainder of the clay"),
    ("the remaining clay", "the rest of the clay"),
    ("are left after making those three kinds of models?", "remains?"),
    ("are left after making those three kinds of models?", "is left?"),
    ("are left after making those three kinds of models?", "are left at the end?"),
    ("are left after making those three kinds of models?", "are left in the end?"),
    ("are left after making those three kinds of models?", "are left at the end."),
    ("are left after making those three kinds of models?", "remains at the end."),
    (" to make models", ""),
])
def test_reference_and_final_balance_paraphrases(project, before, after):
    number(project, allocation().replace(before, after), 2)


@pytest.mark.parametrize("source", ["", " of the clay", " of it"])
def test_source_omissions_and_names_compose_without_a_production_goal(project, source):
    text = allocation().replace(" to make models", "").replace("one-half of it", "one-half" + source)
    text = text.replace("the remaining clay", "the remainder")
    result = number(project, text, 2)
    assert not list(result.store.by_kind(FractionQuantity))
    uses = [r for r in result.store.by_kind(BatchEvidence) if r.kind == "fractional-resource-use"]
    assert [r.marker for r in sorted(uses, key=lambda r: r.position)] == ["opening", "opening", "remainder"]


@pytest.mark.parametrize("source", ["the remainder", "the rest", "the remaining clay"])
def test_remainder_basis_remains_distinct_from_original_stock(project, source):
    text = allocation().replace("one-fourth of it", f"one-fourth of {source}")
    number(project, text, 3)
    # An explicit unqualified stock reference still uses the opening amount.
    number(project, allocation().replace("one-fourth of it", "one-fourth of the clay"), 2)


@pytest.mark.parametrize("source", ["", " of the clay", " of it"])
def test_simplified_single_fraction_needs_no_catalog_or_variety_count(project, source):
    number(project, "Dena bought 12 kilograms of clay. "
           f"She used one-fourth{source} for models. How many kilograms of clay remains?", 9)


@pytest.mark.parametrize("source", ["the remainder", "the rest", "the remaining clay"])
def test_separate_sentences_keep_current_balance_and_explicit_actor(project, source):
    number(project, "Dena bought 12 kilograms of clay. She used half for red models. "
           f"She used half of {source} for blue models. How many kilograms of clay are left?", 3)


@pytest.mark.parametrize("material,unit,expected", [
    ("clay", "kilograms", 9), ("foam", "liters", 9), ("wire", "meters", 9),
])
@pytest.mark.parametrize("ending", ["are left.", "remains.", "are left at the end.", "remains in the end?"])
def test_measured_unit_families_and_question_punctuation(project, material, unit, expected, ending):
    number(project, f"Dena bought 12 {unit} of {material}. She used one-fourth for models. "
           f"How many {unit} of {material} {ending}", expected)


@pytest.mark.parametrize("question", [
    "How much clay is left at the end?",
    "What is the mass of clay left at the end?",
    "How many grams of clay are left in the end?",
])
def test_final_frame_reuses_existing_quantity_question_forms(project, question):
    expected = 9000 if "grams" in question else 9
    number(project, "Dena bought 12 kilograms of clay. She used one-fourth for models. " + question, expected)


@pytest.mark.parametrize("fruit,product", [("banana", "bread"), ("blueberry", "bread"), ("apple", "cake")])
def test_food_products_preserve_generic_ingredient_modifiers(project, fruit, product):
    text = allocation().replace("clay", "butter").replace("models", "cookies")
    text = text.replace("green cookies", f"{fruit} {product}")
    text = text.replace("after making those three kinds of cookies", "at the end")
    result = number(project, text, 2)
    uses = [r for r in result.store.by_kind(BatchEvidence) if r.kind == "fractional-resource-use"]
    assert any(r.container == product and fruit in r.container_ref.qualifiers for r in uses)


def test_a_mass_product_can_also_be_the_explicit_production_goal(project):
    number(project, "Dena bought 8 kilograms of butter to make bread. "
           "She used half of the butter for banana bread. How many kilograms of butter are left?", 4)


@pytest.mark.parametrize("before,after", [
    ("one-half of it", "one-half of the butter"),
    ("the remaining clay", "the rest of the butter"),
    ("the remaining clay", "the remainder of the butter"),
    ("the remaining clay", "the red remainder"),
    ("the remaining clay", "the remainder of her clay"),
    ("one-half of it", "4/5"),  # original-stock allocations overdraw
    ("one-half of it", "4/5 of it"),
    ("one-half of it", "one-half of some clay"),
    ("one-half of it", "one-half of the red clay"),
    ("She used", "Cato used"),
    ("She used", "She might use"),
    ("She used", "She did not use"),
    ("three kinds", "two kinds"),
    ("green models", "red models"),
    ("green models", "banana bread"),
    ("12 kilograms of clay", "12 kilograms of clay and 4 kilograms of butter"),
    ("are left after making those three kinds of models?", "are left at the start?"),
    ("are left after making those three kinds of models?", "are left before the end?"),
    ("are left after making those three kinds of models?", "are left at the end of next week?"),
    ("kilograms of clay are left", "meters of clay are left"),
])
def test_missing_or_mismatched_sources_and_extra_conditions_decline(project, before, after):
    assert not solve(allocation().replace(before, after), project.registry).answer.committed


def test_multiple_stocks_do_not_license_a_bare_or_anaphoric_fraction(project):
    text = ("Dena bought 12 kilograms of clay. Dena bought 8 kilograms of butter. "
            "She used half for models. How many kilograms of clay are left?")
    assert not solve(text, project.registry).answer.committed


@pytest.mark.parametrize("source", ["", " of it", " of the clay"])
def test_later_sentence_does_not_guess_original_or_current_stock(project, source):
    text = ("Dena bought 12 kilograms of clay. She used half for red models. "
            f"She used half{source} for blue models. How many kilograms of clay are left?")
    result = solve(text, project.registry)
    assert not result.answer.committed
    assert "original stock" in result.answer.reason
    assert result.deficiencies() == []


@pytest.mark.parametrize("source", ["", " of it", " of the clay"])
def test_after_a_remainder_reference_the_list_cannot_silently_revert_to_opening_stock(project, source):
    text = allocation().replace("one-fourth of it", "one-fourth of the rest")
    text = text.replace("one-third of the remaining clay", "one-third" + source)
    result = solve(text, project.registry)
    assert not result.answer.committed
    assert "original stock" in result.answer.reason
    assert result.deficiencies() == []


def test_period_terminator_keeps_the_physical_measurement_basis(project):
    # A linear unit may not be inferred as area just because the stock is a sheet.
    text = ("The sheet of paper is 8 feet by 6 feet. "
            "Dena cuts a 2 foot by 3 foot rectangle. How many feet of paper are left.")
    assert not solve(text, project.registry).answer.committed


@pytest.mark.parametrize("rule_id", [
    "arithmetic/fractional-resource-named-use",
    "arithmetic/fractional-resource-elided-use",
    "arithmetic/fractional-resource-residual-use",
])
def test_contextual_reference_grammars_generate_with_stock_evidence(project, rule_id):
    candidate = generate_candidate(project, rule_id=rule_id, seed=4500)
    assert candidate.target_status == "matched"
    assert candidate.context_before


@pytest.mark.parametrize("family,unit,material", [
    ("mass", "kilograms", "clay"), ("volume", "liters", "foam"), ("length", "meters", "wire"),
])
@pytest.mark.parametrize("predicate", ["left", "remains"])
def test_period_questions_round_trip_and_compose(project, family, unit, material, predicate):
    locks = {"unit": unit, "material": material}
    locks.update({"be": "are", "remaining": "left"} if predicate == "left" else {"remain": "remains"})
    candidate = generate_ask_scenario(project,
        ask_id=f"ask/measured-remainder-{family}-period-{predicate}", scenario_mode="ask_only",
        seed=6301, locked_bindings=locks, max_attempts=4)
    assert candidate.consumer == "material-region-remainder"
    number(project, f"Dena bought 12 {unit} of {material}. She used one-fourth for models. "
           + candidate.question, 9)
