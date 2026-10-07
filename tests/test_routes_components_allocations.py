"""Invented analogues for indexed residuals, labeled tallies and allocations."""
from pathlib import Path
import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/curated")).registry


def route(words=False, actor="it", direction="right-hand ", split=False, background=True):
    ords = ("first", "second", "third", "fourth") if words else ("1st", "2nd", "3rd", "4th")
    start = "A truck is driving through a tunnel with many turns. " if background else ""
    join = ". At" if split else " and at"
    return (start + f"The truck must travel through a ring that requires a total of 4 {direction}turns. "
            f"After the {ords[0]} turn, {actor} travels 6 meters. After the {ords[1]} turn, {actor} travels 9 meters. "
            f"After the {ords[2]} turn, {actor} travels a little further{join} the {ords[3]} turn, {actor} immediately exits the tunnel. "
            f"The truck has driven a total of 31 meters around the ring. How far did {actor} travel after the {ords[2]} turn?")


def recipe(factor="half", prefix=True, split=False, ask=None):
    start = "To make cake, together with other ingredients, " if prefix else ""
    join = ". Mira needs " if split else ", and "
    separator = ", and " if split else ", "
    return (start + f"Mira needs 6 cups of water{separator}12 cups of flour{join}{factor} as many teaspoons of salt as the number of cups of flour. "
            + (ask or "Calculate the combined total number of cups of water, flour, and teaspoons of salt that she needs to make the cake."))


def allocation(intro="Mr. Vale shared a certain amount of money between his two sons, Aven and Bira.", split=False, factor="twice", ask="How much was the money shared?"):
    join = ". " if split else ", and "
    return f"{intro} Aven got $240{join}Bira got {factor} as much as Aven. {ask}"


def check(reg, text, value):
    result = solve(text, reg)
    assert result.answer.kind == "number", result.answer
    assert result.answer.value == pytest.approx(value), result.answer
    assert not result.deficiencies(), result.deficiencies()
    assert result.answer.proof is not None


@pytest.mark.parametrize("words", [False, True])
@pytest.mark.parametrize("actor", ["it", "the truck"])
@pytest.mark.parametrize("split", [False, True])
def test_route_ordinals_references_and_clause_boundaries(reg, words, actor, split):
    check(reg, route(words, actor, split=split), 16)


@pytest.mark.parametrize("direction", ["", "left-hand ", "right-hand "])
@pytest.mark.parametrize("background", [False, True])
def test_route_direction_and_optional_background(reg, direction, background):
    check(reg, route(direction=direction, background=background), 16)


@pytest.mark.parametrize("edit", [
    lambda q: q.replace("4 right-hand", "5 right-hand"),
    lambda q: q.replace("2nd turn, it travels 9", "1st turn, it travels 9"),
    lambda q: q.replace("immediately ", ""),
    lambda q: q.replace("31 meters", "10 meters"),
    lambda q: q.replace("it travels 9", "the car travels 9"),
    lambda q: q.replace("around the ring", "around the road"),
    lambda q: q.replace("after the 3rd turn?", "after the 4th turn?"),
    lambda q: q.replace("a little further", "8 meters"),
    lambda q: q.replace("After the 2nd turn, it travels 9 meters. ", ""),
    lambda q: q.replace("31 meters", "31 dollars"),
    lambda q: q.replace("the tunnel.", "the road."),
])
def test_route_incomplete_or_conflicting_evidence_declines(reg, edit):
    assert solve(edit(route()), reg).answer.kind == "decline"


@pytest.mark.parametrize("factor,expected", [("half", 24), ("1/2 times", 24), ("50%", 24), ("twice", 42), ("3 times", 54)])
@pytest.mark.parametrize("prefix", [False, True])
@pytest.mark.parametrize("split", [False, True])
def test_component_comparisons(reg, factor, expected, prefix, split):
    check(reg, recipe(factor, prefix, split), expected)


@pytest.mark.parametrize("ask", [
    "What is the total number of cups of water, cups of flour, and teaspoons of salt?",
    "Calculate the total number of cups of water, cups of flour, and teaspoons of salt.",
    "Determine the combined total number of cups of water, flour, and teaspoons of salt.",
])
def test_component_explicit_and_elliptical_lists(reg, ask):
    check(reg, recipe(ask=ask), 24)


def test_two_component_dependency_chain(reg):
    check(reg, "Tess needs 8 grams of sugar. Tess needs twice as many kilograms of flour as the number of grams of sugar. What is the total number of grams of sugar and kilograms of flour?", 24)


@pytest.mark.parametrize("edit", [
    lambda q: q.replace("as the number of cups of flour", "as the number of teaspoons of flour"),
    lambda q: q.replace("as the number of cups of flour", "as the number of teaspoons of salt"),
    lambda q: q.replace("cups of water, flour, and teaspoons of salt that", "cups of water, water, and teaspoons of salt that"),
    lambda q: q.replace("that she needs to make the cake", "that she needs to make the pizza"),
    lambda q: q.replace("the combined total number of cups of water, flour, and teaspoons of salt", "the total number of cups"),
    lambda q: q.replace("Calculate", "Mira needs 2 cups of sugar. Calculate"),
    lambda q: q.replace("she needs", "Tess needs"),
    lambda q: q.replace("1/2 times", "-1 times"),
])
def test_component_scope_and_unit_boundaries(reg, edit):
    assert solve(edit(recipe(factor="1/2 times")), reg).answer.kind == "decline"


@pytest.mark.parametrize("split", [False, True])
@pytest.mark.parametrize("factor,expected", [("twice", 720), ("three times", 960), ("half", 360)])
def test_allocation_reuses_relational_receipts(reg, split, factor, expected):
    check(reg, allocation(split=split, factor=factor), expected)


@pytest.mark.parametrize("intro", [
    "Mira shared money between two friends, Aven and Bira.",
    "Dr. Vale shared money among two sons, Aven and Bira.",
])
def test_allocation_vocabulary_and_titles(reg, intro):
    check(reg, allocation(intro=intro), 720)


def test_allocation_explicit_source_ask(reg):
    check(reg, allocation(ask="How much money did Mr. Vale share?"), 720)


@pytest.mark.parametrize("edit", [
    lambda q: q.replace("two sons", "three sons"),
    lambda q: q.replace("Aven and Bira", "Aven and Aven"),
    lambda q: q.replace("Bira got", "Cora got"),
    lambda q: q.replace("How much", "Cora got $20. How much"),
    lambda q: q.replace("$240", "240 liters"),
    lambda q: q.replace("$240", "$-240"),
    lambda q: q.replace("twice as much as Aven", "twice as much as Cora"),
])
def test_allocation_incomplete_or_unrelated_receipts_decline(reg, edit):
    assert solve(edit(allocation()), reg).answer.kind == "decline"


def test_three_checkpoints_and_unit_conversion(reg):
    text = ("A bike travels through a road that requires 3 turns. After the first turn, the bike travels 500 meters. "
            "At the third turn, the bike immediately exits the tunnel. The bike traveled 2 kilometers around the road. "
            "How many meters did the bike travel after the second turn?")
    check(reg, text, 1500)


def test_named_group_without_redundant_count(reg):
    check(reg, allocation(intro="Mira shared money between Aven and Bira."), 720)


def test_three_allocation_recipients(reg):
    check(reg, "Mira shared money among three friends, Aven, Bira, and Cora. Aven got $50. Bira got twice as much as Aven. Cora got three times as much as Aven. How much money did Mira share?", 300)


def test_three_component_dependency_chain(reg):
    check(reg, "Mira needs 4 cups of water. Mira needs twice as many cups of flour as cups of water. Mira needs half as many teaspoons of salt as cups of flour. What is the total number of cups of water, cups of flour, and teaspoons of salt?", 16)


@pytest.mark.parametrize("surface", ["1st", "23rd"])
def test_numeric_ordinals_are_indices_not_cardinal_counts(reg, surface):
    from rulekit.kernel.engine import analyze
    from rulekit.kernel.patterns import match_sequence
    from rulekit.data.schemas import MatchToken
    reading = analyze(f"After the {surface} turn.", reg)
    assert match_sequence(reading, [MatchToken(slot="index", type="ordinal")], reg)
    assert not match_sequence(reading, [MatchToken(slot="count", type="number")], reg)
    assert next(u for u in reading.units if u.features.get("lemma") == "turn").senses() == ["noun"]


def test_ordinary_turn_verb_is_preserved(reg):
    from rulekit.kernel.engine import analyze
    reading = analyze("The car must turn.", reg)
    assert next(u for u in reading.units if u.features.get("fold") == "turn").senses() == ["verb"]
