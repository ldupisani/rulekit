"""Named shopping intentions establish context without implying purchases."""
import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve

@pytest.fixture(scope="module")
def reg():
    return load_project("projects/curated").registry

def story(intro="Mira and Owen both want to buy new pairs of shoes and dresses."):
    return (intro + " Owen buys a pair of shoes which costs $30 and a dress which costs $90. "
            "How much should Mira budget if she wants to spend twice as much as what Owen spent on the pair of shoes and dress?")

def check(reg, text, expected):
    result = solve(text, reg)
    assert result.answer.kind == "number", result.answer
    assert result.answer.value == expected
    assert not result.deficiencies(), result.deficiencies()

@pytest.mark.parametrize("both", ["both ", ""])
@pytest.mark.parametrize("new", ["new ", ""])
@pytest.mark.parametrize("relative", ["which", "that"])
def test_named_pair_purchase_intention(reg, both, new, relative):
    intro = f"Mira and Owen {both}want to buy {new}pairs of shoes and dresses."
    check(reg, story(intro).replace("which", relative), 240)

@pytest.mark.parametrize("both", ["both ", ""])
@pytest.mark.parametrize("new", ["new ", ""])
def test_ordinary_items_use_the_same_budget_logic(reg, both, new):
    intro = f"Mira and Owen {both}want to buy {new}books and hats."
    text = story(intro).replace("a pair of shoes", "a book").replace("dress", "hat").replace("the pair of shoes", "the book")
    check(reg, text, 240)


def test_pair_and_nonclothing_item(reg):
    check(reg, story().replace("dresses", "books").replace("dress", "book"), 240)


def test_named_group_without_two_member_marker_can_be_larger(reg):
    check(reg, story().replace("Mira and Owen both", "Mira, Tess, and Owen"), 240)

@pytest.mark.parametrize("edit", [
    lambda q: q.replace("Mira and Owen both", "Mira, Tess, and Owen both"),
    lambda q: q.replace("Mira and Owen", "Mira and Tess"),
    lambda q: q.replace("shoes and dresses", "shoes and hats"),
    lambda q: q.replace("Mira and Owen both", "They both"),
    lambda q: q.replace("want to buy new pairs", "want to buy 3 pairs"),
    lambda q: q.replace("want to buy", "do not want to buy"),
    lambda q: q.replace("Owen buys", "Tess buys"),
])
def test_intention_boundaries(reg, edit):
    assert solve(edit(story()), reg).answer.kind == "decline"


def test_unaccounted_item_qualifier_is_not_ignored(reg):
    text = ("Mira and Owen want to buy red books and hats. "
            "Owen buys a book which costs $30 and a hat which costs $90. "
            "How much should Mira budget to spend twice as much as Owen spent?")
    assert solve(text, reg).answer.kind == "decline"
