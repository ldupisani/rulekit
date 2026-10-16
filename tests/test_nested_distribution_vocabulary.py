"""Generic singular rates and reusable containers in nested allocations."""
import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project("projects/curated").registry


def question(item="apples", determiner="a", group="A group of", inner="baskets"):
    unit = "box" if inner == "boxes" else inner[:-1]
    return (
        f"{group} 8 workers collected 7 boxes of {item}. "
        f"3 boxes had 4 {inner}, with {determiner} {unit} having 6 {item}, "
        f"while the remaining boxes had 2 {inner}, with {determiner} {unit} having 5 {item}. "
        f"How many {item} would each worker get if they divide the {item} equally amongst themselves?"
    )


@pytest.mark.parametrize("item", ["apples", "books"])
@pytest.mark.parametrize("determiner", ["a", "each", "every"])
@pytest.mark.parametrize("group", ["A group of", "A team of", ""])
def test_generic_container_rate(reg, item, determiner, group):
    result = solve(question(item, determiner, group), reg)
    assert result.answer.value == 14, result.answer
    assert not result.deficiencies()


@pytest.mark.parametrize("inner", ["bags", "boxes", "baskets"])
def test_singular_rate_reuses_container_category(reg, inner):
    assert solve(question(inner=inner), reg).answer.value == 14


@pytest.mark.parametrize("edit", [
    lambda q: q.replace("a basket having 6", "one basket having 6"),
    lambda q: q.replace("a basket having 6", "the basket having 6"),
    lambda q: q.replace("a basket having 6", "a box having 6"),
    lambda q: q.replace("a basket having 6", "a baskets having 6"),
    lambda q: q.replace("5 apples", "5 books"),
    lambda q: q.replace("8 workers", "0 workers"),
])
def test_no_unstated_distribution_or_mismatched_contents(reg, edit):
    assert not solve(edit(question()), reg).answer.committed


@pytest.mark.parametrize("description", ["workers", "farm workers", "school workers"])
@pytest.mark.parametrize("item", ["apples", "books"])
@pytest.mark.parametrize("group", ["A group of", ""])
def test_items_before_containers_and_modified_recipients(reg, description, item, group):
    text = question(item=item, group=group)
    text = text.replace("8 workers", f"8 {description}")
    text = text.replace(f"7 boxes of {item}", f"{item} in 7 boxes")
    result = solve(text, reg)
    assert result.answer.value == 14, result.answer
    assert not result.deficiencies()


@pytest.mark.parametrize("opening", [
    "A team of 8 farm workers collected 7 boxes of apples.",
    "8 school workers collected 7 apple boxes.",
])
def test_modified_recipients_in_existing_orders(reg, opening):
    text = opening + question().split(".", 1)[1]
    assert solve(text, reg).answer.value == 14


@pytest.mark.parametrize("edit", [
    lambda q: q.replace("in 7 boxes", "near 7 boxes"),
    lambda q: q.replace("in 7 boxes", "in boxes"),
    lambda q: q.replace("each worker", "each child"),
    lambda q: q.replace("each worker", "each school worker"),
    lambda q: q.replace("3 boxes had", "4 school workers collected apples in 3 boxes. 3 boxes had"),
])
def test_alternative_order_does_not_infer_unstated_relations(reg, edit):
    text = question().replace("8 workers", "8 farm workers").replace(
        "7 boxes of apples", "apples in 7 boxes"
    )
    assert not solve(edit(text), reg).answer.committed


@pytest.mark.parametrize("item", ["peaches", "apples", "books"])
@pytest.mark.parametrize("verb", ["had", "took", "take"])
@pytest.mark.parametrize("object_form", ["explicit", "pronoun"])
def test_packing_quantities_and_item_pronoun(reg, item, verb, object_form):
    text = question(item=item).replace(" had ", f" {verb} ")
    if object_form == "pronoun":
        text = text.replace(f"divide the {item}", "divide them")
    result = solve(text, reg)
    assert result.answer.value == 14, result.answer
    assert not result.deficiencies()


@pytest.mark.parametrize("edit", [
    lambda q: q.replace("5 peaches", "5 books"),
    lambda q: q.replace("How many peaches", "How many books"),
    lambda q: q.replace("divide them", "divide it"),
    lambda q: q.replace("basket having", "basket taking"),
    lambda q: q.replace("How many", "The workers sold 3 peaches. How many"),
])
def test_packing_pronoun_boundaries(reg, edit):
    text = question(item="peaches").replace(" had ", " took ").replace(
        "divide the peaches", "divide them"
    )
    assert not solve(edit(text), reg).answer.committed
