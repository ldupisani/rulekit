"""Category references select a complete, typed purchase ledger across domains."""
import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve

@pytest.fixture(scope="module")
def reg():
    return load_project("projects/curated").registry


def story(collection="clothes", first="a pair of shoes", second="a dress", new="new ", both="both ", conditional=True):
    ask = "if she wants to spend" if conditional else "to spend"
    return (f"Mira and Owen {both}want to buy {new}{collection}. "
            f"Owen buys {first} which costs $30 and {second} which costs $90. "
            f"How much should Mira budget {ask} twice as much as what Owen spent on {new}{collection}?")

@pytest.mark.parametrize("collection,first,second", [
    ("clothes", "a pair of shoes", "a dress"),
    ("ingredients", "sugar", "cheese"),
    ("goods", "a book", "a hat"),
])
@pytest.mark.parametrize("new", ["", "new "])
@pytest.mark.parametrize("both", ["", "both "])
@pytest.mark.parametrize("conditional", [True, False])
def test_collection_budget_paraphrases(reg, collection, first, second, new, both, conditional):
    result = solve(story(collection, first, second, new, both, conditional), reg)
    assert result.answer.kind == "number", result.answer
    assert result.answer.value == 240
    assert not result.deficiencies()

@pytest.mark.parametrize("edit", [
    lambda q: q.replace("a dress", "a book"),
    lambda q: q.replace("on new clothes", "on Tess's new clothes"),
    lambda q: q.replace("on new clothes", "on ingredients"),
    lambda q: q.replace("buy new clothes", "buy ingredients"),
    lambda q: q.replace("new clothes", "red clothes"),
    lambda q: q.replace("Mira and Owen", "Mira and Tess"),
    lambda q: q.replace("Mira and Owen", "Mira, Tess, and Owen"),
    lambda q: q.replace("want to buy", "do not want to buy"),
    lambda q: q.replace("new clothes", "3 clothes"),
    lambda q: q.replace("Owen buys", "Tess buys"),
])
def test_collection_boundaries(reg, edit):
    assert solve(edit(story()), reg).answer.kind == "decline"


def test_collection_reference_without_intro(reg):
    result = solve(story(new="").split(". ", 1)[1], reg)
    assert result.answer.value == 240
    assert not result.deficiencies()
