"""Invented examples for invariant expenses, named portions, and scaled sales."""
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/curated")).registry


def income(prior="50%", later="25%", increase="300", title="Mrs. Vale", habitual="used to spend", costs="rent and utilities", ask="previous monthly income"):
    return (f"{title} {habitual} {prior} of her monthly income on {costs}. "
            f"Her salary was recently increased by ${increase} so now her {costs} only amount to {later} of her monthly income. "
            f"How much was her {ask}?")


def portions(first="Mira and Tess", second="Lena and Nora", whole="pizzas", acquisition="buy", share="50%", ask="How many pizza pieces are left uneaten?"):
    return (f"Mira, Tess, Lena, and Nora each {acquisition} {whole} cut into 8 pieces. "
            f"{first} eat {share} of their {whole}. {second} eat 75% of the {whole}. {ask}")


def sales(period="month", front=True, split=False, factor="twice", ask=None):
    quotes = ("Mira charges $24 for a large painting. She charges $12 for a small painting." if split else
              "Mira charges $24 for a large painting and $12 for a small painting.")
    counts = (f"Last {period} she sold six large paintings and two small paintings." if front else
              f"She sold six large paintings and two small paintings last {period}.")
    return f"{quotes} {counts} If she sold {factor} as much this {period}, " + (ask or f"how much are her sales for this {period}?")


@pytest.mark.parametrize("prior,later,increase,expected", [("50%", "25%", "300", 300), ("60%", "40%", "200", 400), ("1/2", "1/4", "125", 125)])
def test_income_counterfactuals(reg, prior, later, increase, expected):
    result = solve(income(prior, later, increase), reg)
    assert result.answer.value == pytest.approx(expected), result.answer
    assert not result.deficiencies()


@pytest.mark.parametrize("title", ["Mrs. Vale", "Ms. Vale", "Dr. Vale", "Mira"])
@pytest.mark.parametrize("habitual", ["used to spend", "spent"])
def test_income_titles_and_tense(reg, title, habitual):
    result = solve(income(title=title, habitual=habitual), reg)
    assert result.answer.value == pytest.approx(300), result.answer


@pytest.mark.parametrize("edit", [
    lambda q: q.replace("25%", "60%"),
    lambda q: q.replace("$300", "$0"),
    lambda q: q.replace("25%", "0%"),
    lambda q: q.replace("so now her rent and utilities", "so now her rent"),
    lambda q: q.replace("25% of her monthly income", "25% of her income"),
    lambda q: q.replace("50% of her", "50% of Bob's"),
    lambda q: q.replace("her previous monthly income", "Bob's previous monthly income"),
])
def test_income_boundaries(reg, edit):
    assert solve(edit(income()), reg).answer.kind == "decline"


@pytest.mark.parametrize("acquisition", ["buy", "bought", "get", "have"])
@pytest.mark.parametrize("share", ["50%", "half", "1/2"])
def test_portion_paraphrases(reg, acquisition, share):
    result = solve(portions(acquisition=acquisition, share=share), reg)
    assert result.answer.value == 12, result.answer


@pytest.mark.parametrize("whole,ask", [("cakes", "How many pieces are left?"), ("pizzas", "How many pizza pieces are uneaten?"), ("personal pan pizzas", "How many pizza pieces are left uneaten?")])
def test_portion_wholes_and_asks(reg, whole, ask):
    result = solve(portions(whole=whole, ask=ask), reg)
    assert result.answer.value == 12, result.answer


@pytest.mark.parametrize("first,second", [("Mira and Tess", "Tess and Nora"), ("Mira", "Lena and Nora"), ("Mira or Tess", "Lena and Nora"), ("Mira and Tess", "Lena and Eva"), ("Mira and Mira", "Lena and Nora")])
def test_portion_partition_boundaries(reg, first, second):
    assert solve(portions(first=first, second=second), reg).answer.kind == "decline"


@pytest.mark.parametrize("period", ["month", "week", "year"])
@pytest.mark.parametrize("front,split", [(True, False), (False, False), (True, True)])
def test_sales_period_and_sentence_variations(reg, period, front, split):
    result = solve(sales(period, front, split), reg)
    assert result.answer.value == 336, result.answer


@pytest.mark.parametrize("edit", [
    lambda q: q.replace("twice as much", "twice as many paintings"),
    lambda q: q.replace("two small paintings", "two large paintings"),
    lambda q: q.replace("this month?", "this year?"),
    lambda q: q.replace("$12", "12 liters"),
    lambda q: q.replace("her sales", "Bob's sales"),
])
def test_sales_boundaries(reg, edit):
    assert solve(edit(sales()), reg).answer.kind == "decline"


@pytest.mark.parametrize("edit", [
    lambda q: q.replace("only amount to", "amount to"),
    lambda q: q.replace("only amount to", "are"),
    lambda q: q.replace("was recently increased", "increased"),
    lambda q: q.replace("previous monthly income", "old monthly income"),
    lambda q: q.replace("rent and utilities", "utilities and rent"),
])
def test_income_equivalence_paraphrases(reg, edit):
    result = solve(edit(income()), reg)
    assert result.answer.value == pytest.approx(300), result.answer


def test_individual_portions(reg):
    result = solve("Mira and Tess each buy cakes cut into 8 pieces. Mira eats half of the cakes. Tess eats 25% of the cakes. How many pieces are left?", reg)
    assert result.answer.value == 10, result.answer


def test_sales_single_product(reg):
    result = solve("Mira charges $15 for a painting. She sold four paintings last week. If she sold twice as much this week, how much are her sales for this week?", reg)
    assert result.answer.value == 120, result.answer


def test_sales_background(reg):
    q = sales().replace("Mira charges", "She charges")
    result = solve("Mira is a painter. She paints pictures and sells them at the park. " + q, reg)
    assert result.answer.value == 336, result.answer


def test_title_sentence_boundaries_are_registry_driven():
    from rulekit.kernel.tokenize import split_sentences
    text = "Mx. Vale has 2.5 coins. Who has coins?"
    assert split_sentences(text, ("mx",)) == ["Mx. Vale has 2.5 coins.", "Who has coins?"]
    assert split_sentences(text) == ["Mx.", "Vale has 2.5 coins.", "Who has coins?"]


@pytest.mark.parametrize("edit", [
    lambda q: q.replace("50%", "150%"),
    lambda q: q.replace("8 pieces", "0 pieces"),
    lambda q: q.replace("their pizzas", "Bob's pizzas"),
    lambda q: q.replace("pizza pieces", "cake pieces"),
])
def test_portion_amount_and_ownership_boundaries(reg, edit):
    assert solve(edit(portions()), reg).answer.kind == "decline"


@pytest.mark.parametrize("token,expected", [
    ({"slot": "people", "span": True, "enumeration_cat": "missing_category"}, "unknown category"),
    ({"slot": "people", "span": True}, "enumeration-gated span"),
])
def test_enumeration_contract_is_checked_at_compile_time(tmp_path, token, expected):
    from ruamel.yaml import YAML
    from rulekit.data.packs import load_pack
    from rulekit.data.registry import CompileError, compile_registry
    (tmp_path / "pack.yaml").write_text("format: rulekit/pack@1\nname: invented\n")
    rule = {"id": "invented/enumeration", "phase": "read", "match": {"sentence": [token]},
            "emits": [{"fact": "batch_evidence", "kind": "population", "entity": "", "measure": "", "value": 1, "members": "{people.members}"}]}
    YAML().dump({"format": "rulekit/rules@1", "rules": [rule]}, tmp_path / "rules.yaml")
    with pytest.raises(CompileError, match=expected):
        compile_registry([load_pack(tmp_path)])


@pytest.mark.parametrize("background", [
    "Tess is a painter.",
    "Mira is not a painter.",
    "Mira is a painter at the park.",
])
def test_sales_background_must_be_exact_and_positive(reg, background):
    assert solve(background + " " + sales(), reg).answer.kind == "decline"


@pytest.mark.parametrize("whole", [
    "personal pizzas", "pan pizzas", "personal pan pizzas", "large pizzas",
    "large pan pizzas", "cheese pizzas", "large cheese pizzas",
    "small cakes", "apple cakes",
])
def test_modified_portioned_wholes_use_generic_references(reg, whole):
    text = portions(whole=whole, ask="How many pieces are left uneaten?")
    result = solve(text, reg)
    assert result.answer.value == 12, result.answer
    assert not result.deficiencies(), result.deficiencies()


@pytest.mark.parametrize("whole", ["personal pan pizzas", "large cheese pizzas", "small pizzas"])
def test_later_bare_whole_reference_preserves_the_established_population(reg, whole):
    text = portions(whole=whole).replace(f"of their {whole}", "of their pizzas").replace(f"of the {whole}", "of the pizzas")
    result = solve(text, reg)
    assert result.answer.value == 12, result.answer
    assert not result.deficiencies()


@pytest.mark.parametrize("population,share", [
    ("large pizzas", "small pizzas"),
    ("personal pan pizzas", "personal cheese pizzas"),
    ("cheese pizzas", "apple pizzas"),
    ("pizzas", "large pizzas"),
])
def test_conflicting_or_new_whole_descriptors_decline(reg, population, share):
    text = portions(whole=population).replace(f"of their {population}", f"of their {share}")
    assert solve(text, reg).answer.kind == "decline"


@pytest.mark.parametrize("asked,expected", [("large cheese pizza", 12), ("cheese pizza", 12), ("small cheese pizza", None)])
def test_qualified_piece_questions_preserve_whole_scope(reg, asked, expected):
    result = solve(portions(whole="large cheese pizzas", ask=f"How many {asked} pieces are left?"), reg)
    assert result.answer.value == expected, result.answer
    assert result.answer.kind == ("number" if expected is not None else "decline")


def test_modified_foods_are_compositional_not_atomic_products(reg):
    from rulekit.kernel.engine import analyze
    from rulekit.kernel.reference_identity import reference_from_unit
    assert "personal pan pizza" not in reg.lexicon
    assert "pizza_portion_whole" not in reg.category_parents
    reading = analyze("personal pan pizzas", reg)
    pizza = next(u for u in reading.units if u.features.get("lemma") == "pizza")
    ref = reference_from_unit(pizza)
    assert ref.head == "pizza"
    assert set(ref.qualifiers) == {"personal", "pan"}
    cheese = next(u for u in analyze("personal cheese pizzas", reg).units if u.features.get("lemma") == "pizza")
    assert reference_from_unit(cheese) != ref
