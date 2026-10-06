"""Invented exhaustive populations with an equal-content prefix."""
from pathlib import Path
import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve

@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/curated")).registry

@pytest.mark.parametrize("prefix", [
    "There are 4 boxes, and each of the first three boxes has 6 apples.",
    "There are 4 boxes. Each of the first three boxes has 6 apples.",
    "There are 4 boxes. The first three boxes each have 6 apples.",
    "There are 4 boxes. The first three boxes have 6 apples each.",
])
@pytest.mark.parametrize("ask", [
    "How many apples does the fourth box have?",
    "How many apples are in the fourth box?",
    "How many apples does the last box have?",
    "How many apples does the final box have?",
    "How many apples does the remaining box have?",
])
def test_paraphrases(reg, prefix, ask):
    result = solve(f"{prefix} There are a total of 27 apples. {ask}", reg)
    assert result.answer.value == 9, result.answer
    assert result.answer.proof

@pytest.mark.parametrize("change", [
    ("4 boxes", "5 boxes"),
    ("fourth box", "third box"),
    ("27 apples", "12 apples"),
    ("three boxes", "2.5 boxes"),
    ("6 apples", "6.5 apples"),
    ("27 apples", "27 oranges"),
    ("first three boxes", "next three boxes"),
])
def test_insufficient_or_inconsistent_evidence(reg, change):
    text = ("There are 4 boxes. Each of the first three boxes has 6 apples. "
            "There are a total of 27 apples. How many apples does the fourth box have?")
    result = solve(text.replace(*change), reg)
    assert result.answer.kind == "decline", result.answer

@pytest.mark.parametrize("holder,item", [("houses", "gnomes"), ("boxes", "apples"), ("jars", "marbles")])
def test_related_collections(reg, holder, item):
    singular = reg.plural_to_singular[holder]
    text = (f"There are 6 {holder} on a street, and each of the first five {holder} has 4 {item} in the garden. "
            f"If there are a total of 29 {item} on the street, how many {item} does the sixth {singular} have?")
    result = solve(text, reg)
    assert result.answer.value == 9, result.answer

@pytest.mark.parametrize("total", ["There are 27 apples altogether.", "There are 27 apples in total."])
def test_total_paraphrases(reg, total):
    result = solve("There are 4 boxes. The first three boxes each have 6 apples. "
                   + total + " How many apples does the fourth box have?", reg)
    assert result.answer.value == 9, result.answer

@pytest.mark.parametrize("tail", [
    "There are a total of 27 apples in the garden.",
    "There are a total of 27 apples in the street.",
    "There are a total of 27 apples on the street. Nora ate 2 apples.",
])
def test_scope_and_extra_events(reg, tail):
    result = solve("There are 4 boxes on a street. Each of the first three boxes has 6 apples. "
                   + tail + " How many apples does the fourth box have?", reg)
    assert result.answer.kind == "decline", result.answer

@pytest.mark.parametrize("text,kind,value", [
    ("the fourth box", None, None),
    ("the fifth house", None, None),
    ("one fourth of the boxes", "fraction", .25),
    ("one fifth of the houses", "fraction", .2),
    ("the second round", None, None),
    ("the first side", None, None),
    ("the second side", None, None),
])
def test_ordinal_fraction_boundary(reg, text, kind, value):
    from rulekit.kernel.tokenize import tokenize
    from rulekit.kernel.numbers import annotate_numbers
    reading = tokenize(text)
    annotate_numbers(reading, reg)
    values = [(u.features.get("value_kind"), u.features.get("value")) for u in reading.units
              if u.features.get("value_kind")]
    assert values == ([(kind, value)] if kind else [])

@pytest.mark.parametrize("count,prefix,amount,total,order,expected", [
    (2, 1, 7, 19, "second", 12),
    (4, 3, 6, 18, "fourth", 0),
    (4, 3, 3, 14, "fourth", 5),
    (12, 11, 2, 30, "last", 8),
])
def test_partition_arithmetic_boundaries(reg, count, prefix, amount, total, order, expected):
    result = solve(f"There are {count} boxes. Each of the first {prefix} boxes has {amount} apples. "
                   f"There are a total of {total} apples. How many apples does the {order} box have?", reg)
    assert result.answer.value == expected, result.answer

@pytest.mark.parametrize("opening,total", [
    ("There are 4 boxes on a street.", "There are a total of 27 apples on the street."),
    ("Nora has 4 boxes.", "There are a total of 27 apples."),
])
def test_reuses_ordinary_populations(reg, opening, total):
    result = solve(opening + " Each of the first three boxes has 6 apples. " + total
                   + " How many apples does the fourth box have?", reg)
    assert result.answer.value == 9, result.answer

@pytest.mark.parametrize("verb", ["sold", "bought", "lost"])
def test_events_do_not_establish_a_holder_population(reg, verb):
    result = solve(f"Nora {verb} 4 boxes. Each of the first three boxes has 6 apples. "
                   "There are a total of 27 apples. How many apples does the fourth box have?", reg)
    assert result.answer.kind == "decline", result.answer

@pytest.mark.parametrize("left,right", [(3, 3), (3, 4)])
def test_ordinal_modifiers_preserve_distinct_holder_identities(reg, left, right):
    prefix = f"The fourth box has {left} apples. The fifth box has {right} apples. "
    combined = solve(prefix + "How many apples do the boxes have altogether?", reg)
    assert combined.answer.value == left + right, combined.answer
    ambiguous = solve(prefix + "How many apples does the box have?", reg)
    assert ambiguous.answer.kind == "decline", ambiguous.answer


def test_ordinal_holders_cannot_collapse_to_one_entity(reg):
    result = solve("The fourth box has 3 gnomes. The fifth box has 3 gnomes. "
                   "How many gnomes are there in all?", reg)
    assert result.answer.kind == "decline", result.answer

@pytest.mark.parametrize("order", ["first", "last", "final", "fourth", "fifth"])
def test_explicit_indexed_holdings_keep_the_existing_consumer(reg, order):
    from rulekit.kernel.patterns import match_ask
    result = solve(f"The {order} box has 7 apricots. How many apricots does the {order} box have?", reg)
    assert result.answer.value == 7, result.answer
    matched = match_ask(result.question, reg, store=result.store)
    assert matched[1]["consumer"] == "single-entity"


def test_question_selection_requires_typed_prefix_evidence(reg):
    from rulekit.kernel.patterns import match_ask
    from rulekit.kernel.facts import FactStore
    result = solve("There are 4 boxes. Each of the first three boxes has 6 apples. "
                   "There are a total of 27 apples. How many apples does the fourth box have?", reg)
    assert match_ask(result.question, reg)[1]["consumer"] == "holder-remainder"
    assert match_ask(result.question, reg, store=result.store)[1]["consumer"] == "holder-remainder"
    assert match_ask(result.question, reg, store=FactStore())[1]["consumer"] == "single-entity"


@pytest.mark.parametrize("location", ["street", "road", "lane", "avenue", "boulevard"])
@pytest.mark.parametrize("joined", [False, True])
@pytest.mark.parametrize("order", ["last", "final", "remaining", "fourth"])
def test_residential_location_vocabulary(reg, location, joined, order):
    join = ", and each" if joined else ". Each"
    text = (f"There are 4 houses on a {location}{join} of the first three houses has 5 gnomes in the garden. "
            f"If there are a total of 24 gnomes on the {location}, how many gnomes does the {order} house have?")
    result = solve(text, reg)
    assert result.answer.value == 9, result.answer
    assert result.answer.proof


@pytest.mark.parametrize("location", ["road", "lane", "avenue", "boulevard"])
def test_different_residential_locations_do_not_share_totals(reg, location):
    result = solve(f"There are 4 houses on a {location}. Each of the first three houses has 5 gnomes. "
                   "There are a total of 24 gnomes on the street. How many gnomes does the last house have?", reg)
    assert result.answer.kind == "decline", result.answer


@pytest.mark.parametrize("holder,item", [("jars", "pickles"), ("boxes", "apples"), ("bags", "marbles")])
@pytest.mark.parametrize("order", ["fourth", "last", "remaining"])
def test_content_bearing_population_reuses_existential_rule(reg, holder, item, order):
    from rulekit.kernel.model import Quantity
    singular = reg.plural_to_singular[holder]
    result = solve(f"There are 4 {holder} of {item}. The first three {holder} each have 5 {item}. "
                   f"There are a total of 23 {item}. How many {item} does the {order} {singular} have?", reg)
    assert result.answer.value == 8, result.answer
    populations = [q for q in result.store.by_kind(Quantity) if q.measure == singular]
    assert len(populations) == 1
    assert populations[0].value == 4
    assert populations[0].provenance.source == "arithmetic/existential-premise-bare"
    assert result.answer.proof


@pytest.mark.parametrize("total_item", ["pickles", "apples"])
def test_content_bearing_population_still_requires_matching_total(reg, total_item):
    result = solve("There are 4 jars of pickles. Each of the first three jars has 5 pickles. "
                   f"There are a total of 23 {total_item}. How many pickles does the final jar have?", reg)
    if total_item == "pickles":
        assert result.answer.value == 8, result.answer
    else:
        assert result.answer.kind == "decline", result.answer


@pytest.mark.parametrize("contents", [
    "5 pickles in total", "5 pickles altogether", "5 pickles together",
    "5 pickles all together", "5 pickles combined", "a total of 5 pickles",
])
@pytest.mark.parametrize("order", ["last", "fourth", "remaining"])
def test_collective_prefix_subtotal(reg, contents, order):
    from rulekit.kernel.model import BatchEvidence, GroupTotal
    result = solve(f"There are 4 jars of pickles. The first three jars have {contents}. "
                   f"There are a total of 23 pickles. How many pickles does the {order} jar have?", reg)
    assert result.answer.value == 18, result.answer
    prefix, = [r for r in result.store.by_kind(BatchEvidence) if r.kind == "holder-subtotal"]
    assert (prefix.value, prefix.subtotal, prefix.per_member) == (3, 5, 0)
    assert len(result.store.by_kind(GroupTotal)) == 1
    assert result.answer.proof
    assert "23 − 5 = 18" in result.answer.reason


@pytest.mark.parametrize("clause,expected", [
    ("The first three boxes have 5 apples in total.", 18),
    ("The first three boxes have 5 apples each.", 8),
    ("Each of the first three boxes has 5 apples.", 8),
])
def test_collective_and_distributive_prefixes_stay_distinct(reg, clause, expected):
    result = solve("There are 4 boxes. " + clause
                   + " There are a total of 23 apples. How many apples does the final box have?", reg)
    assert result.answer.value == expected, result.answer


@pytest.mark.parametrize("change", [
    ("4 jars", "5 jars"), ("last jar", "second jar"),
    ("5 pickles in total", "24 pickles in total"),
    ("three jars", "2.5 jars"), ("5 pickles in total", "5.5 pickles in total"),
    ("23 pickles", "23 apples"), ("first three", "next three"),
    ("in total", "in combined"), ("in total", "all total"),
    ("5 pickles in total", "5 pickles each in total"),
    ("The first three jars have", "Each of the first three jars has"),
])
def test_collective_prefix_boundaries(reg, change):
    text = ("There are 4 jars of pickles. The first three jars have 5 pickles in total. "
            "There are a total of 23 pickles. How many pickles does the last jar have?")
    result = solve(text.replace(*change), reg)
    assert result.answer.kind == "decline", result.answer


@pytest.mark.parametrize("subtotal,total,expected", [(0, 23, 23), (23, 23, 0), (3, 23, 20)])
def test_collective_prefix_zero_and_repeated_counts(reg, subtotal, total, expected):
    result = solve(f"There are 4 jars. The first three jars have {subtotal} pickles altogether. "
                   f"There are a total of {total} pickles. How many pickles does the last jar have?", reg)
    assert result.answer.value == expected, result.answer


def test_collective_prefix_extra_event_declines(reg):
    result = solve("There are 4 jars. The first three jars have 5 pickles altogether. Nora ate 2 pickles. "
                   "There are a total of 23 pickles. How many pickles does the last jar have?", reg)
    assert result.answer.kind == "decline", result.answer
