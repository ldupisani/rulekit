"""Invented paraphrases and scope boundaries for relative quantities."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def registry():
    return load_project(Path("projects/curated")).registry


CASES = {
    "shared-food": (
        "Nora, Iris, and Ava bought 35 cookies. "
        "Iris and Ava each ate three times as many cookies as Nora did. "
        "How many cookies did Nora eat?",
        5, "shared-lot-fully-used",
    ),
    "shared-supplies": (
        "Nora, Iris, and Ava bought 42 pencils. "
        "Iris and Ava each used three times as many pencils as Nora. "
        "How many pencils did Nora use?",
        6, "shared-lot-fully-used",
    ),
    "revenue": (
        "Pens cost $3 each. "
        "Nora sold 9 pens in total. "
        "Iris sold twice the number of pens as Nora. "
        "How much more money did Iris make selling pens compared with Nora?",
        27, None,
    ),
    "revenue-purpose": (
        "Nora and Iris were selling pencils to fund their trip. "
        "The pencils cost $4 each. "
        "Nora sold 7 pencils total. "
        "Iris sold twice the number of pencils as Nora. "
        "How much more did Iris earn for the trip from selling pencils than Nora?",
        28, None,
    ),
    "grocery-budget": (
        "Nora bought bread for $3, milk for $4, and juice for twice the price of the bread. "
        "She had $21 for her shopping. "
        "How much money did Nora have left?",
        8, None,
    ),
    "supplies-budget": (
        "Nora bought a pen for $3, a notebook for $4, and an eraser for twice the price of the pen. "
        "She had $20 for her shopping. "
        "How much money did Nora have left?",
        7, None,
    ),
    "photo-deposit": (
        "Nora's family album has 120 pictures. "
        "They took one third as many pictures as they had in the family's album on the first day and "
        "25 more pictures than they took on the first day on the second day. "
        "They added all these pictures to the family album. "
        "Calculate the total number of pictures in the album.",
        225, None,
    ),
    "shell-deposit": (
        "Nora's family cabinet has 36 shells. "
        "They collected half as many shells as they had in the family's cabinet on the first day and "
        "12 more shells than they collected on the first day on the second day. "
        "They added all these shells to the family cabinet. "
        "Calculate the total number of shells in the cabinet.",
        84, None,
    ),
    "pencil-receipt": (
        "Nora has 36 pencils. "
        "She lost one third of them one morning. "
        "Then a friend sees her and gives her twice the amount that Nora had after she lost them. "
        "How many pencils does Nora end up with?",
        72, None,
    ),
    "sticker-receipt": (
        "Nora has 32 stickers. "
        "She lost 25% of them one day. "
        "A friend gave her triple the amount Nora had after she lost them. "
        "How many stickers does Nora end up with?",
        96, None,
    ),
    "pet-inventory": (
        "Nora has 5 birds, 4 hamsters, and three times as many rabbits as hamsters and birds combined. "
        "How many pets does Nora have in total?",
        36, None,
    ),
    "plant-inventory": (
        "Nora has 4 roses, 5 tulips, and twice as many daisies as tulips and roses combined. "
        "How many flowers does Nora have in total?",
        27, None,
    ),
    "explicit-nested-parent": (
        "There are some candies in a bag. "
        "Two thirds of the candies are blue, and half of the blue candies are lemon flavoured. "
        "If 18 blue candies are lemon flavoured, how many candies are there in the bag?",
        54, None,
    ),
    "assumed-nested-parent": (
        "There are some cookies in a box. "
        "Three fourths of the cookies are green, and one third of the green cookies are mint flavored. "
        "If 24 cookies are mint flavored, how many cookies are there in the box?",
        96, "observed-subtype-within-parent",
    ),
    "labels": (
        "Nora needs to put labels on the letters she is about to send. "
        "She has cards for each of her aunt, uncle and cousin. "
        "She has to pay the gas bill and the water bill separately. "
        "She wants to send two more rebates than she does bills and she has three times as many job "
        "applications as rebates to mail. "
        "How many labels does she need if everything needs 2 labels except the gas bill, which needs "
        "4?",
        44, None,
    ),
    "stamps": (
        "Nora needs to place stamps on the envelopes she is about to mail. "
        "She has cards for each of her aunt, cousin and grandmother. "
        "She has to pay the electric bill and the water bill separately. "
        "She wants to send four more rebates than she does bills and she has twice as many "
        "applications as rebates to mail. "
        "How many stamps does she need if everything needs one stamp except the water bill, which "
        "needs 3 stamps?",
        25, None,
    ),
    "aquarium": (
        "An aquarium contains an equal number of goldfish and blowfish. "
        "12 of the blowfish remain in their own tank, and the remaining blowfish go into a display "
        "tank. "
        "An equal number of goldfish join the blowfish in the display tank, but one half of these "
        "goldfish go back into their own tank. "
        "If the aquarium contains a combined total of 60 fish, how many goldfish are in the display "
        "tank?",
        9, None,
    ),
    "zoo": (
        "A zoo holds an equal number of rabbits and goats. "
        "6 of the goats stay in their own cage, and the remaining goats go into a display cage. "
        "An equal number of rabbits join the goats in the display cage, but half of these rabbits go "
        "back into their own cage. "
        "If the zoo holds a combined total of 36 animals, how many rabbits are in the display cage?",
        6, None,
    ),
    "daily-practice": (
        "Each day, Nora can juggle 3 more balls than the day before. "
        "If she starts juggling 2 balls and practices for 4 days, how many balls can Nora juggle?",
        14, None,
    ),
    "weekly-practice": (
        "Each week, Nora can write 4 more pages than the week before. "
        "If she starts writing 3 pages and practices for 3 weeks, how many pages can Nora write?",
        15, None,
    ),
}


@pytest.mark.parametrize("family", CASES)
def test_relative_quantity_compositions(registry, family):
    question, answer, assumption = CASES[family]
    result = solve(question, registry)
    assert result.answer.committed, result.answer
    assert result.value == pytest.approx(answer)
    assert not result.deficiencies()
    assert [entry.id for entry in result.answer.assumptions] == (
        [assumption] if assumption else []
    )


@pytest.mark.parametrize(
    "family, original, replacement",
    [
        ("shared-food", "Iris and Ava each", "Iris and Theo each"),
        ("shared-food", "How many cookies", "There are 7 cookies left. How many cookies"),
        ("revenue", "Pens cost $3 each.", "Pencils cost $3 each."),
        ("grocery-budget", "the price of the bread", "the price of the cereal"),
        ("supplies-budget", "She had $20", "She had $10"),
        ("photo-deposit", "to the family album", "to the family cabinet"),
        ("shell-deposit", "on the second day", "on the third day"),
        ("pencil-receipt", "How many pencils", "How many pens"),
        ("plant-inventory", "tulips and roses combined", "tulips and lilies combined"),
        ("explicit-nested-parent", "18 blue candies", "18 yellow candies"),
        ("explicit-nested-parent", "half of the blue", "four ninths of the blue"),
        ("assumed-nested-parent", "Three fourths", "5/7"),
        ("labels", "the gas bill, which needs 4", "the electric bill, which needs 4"),
        ("stamps", "which needs 3 stamps", "which needs 3 labels"),
        ("aquarium", "join the blowfish in the display tank", "join the blowfish in the storage tank"),
        ("zoo", "36 animals", "35 animals"),
        ("daily-practice", "practices for 4 days", "practices for 4 hours"),
    ],
)
def test_relative_quantity_keeps_scope_and_quantity_boundaries(
    registry, family, original, replacement
):
    question, _, _ = CASES[family]
    assert original in question
    result = solve(question.replace(original, replacement), registry)
    assert not result.answer.committed, result.answer


MARBLE_PARTITION = (
    "There are some marbles in a box. "
    "Three quarters of the marbles are green, and one third of the green marbles are small. "
)


@pytest.mark.parametrize(
    "count",
    [
        "24 are both green and small",
        "24 marbles are small and green",
        "24 green marbles are small",
        "24 small marbles are green",
    ],
)
def test_nested_marble_shares(registry, count):
    result = solve(
        f"{MARBLE_PARTITION}If {count}, how many marbles are there in the box?",
        registry,
    )
    assert result.value == 96, result.answer
    assert not result.answer.assumptions
    assert not result.deficiencies()


def test_nested_shares_allow_different_attribute_order_and_holder_phrasing(registry):
    result = solve(
        "There are some books inside a cabinet. "
        "Half of the books are large and 25% of the large books are blue. "
        "If 9 books are both blue and large, how many books are there within the cabinet?",
        registry,
    )
    assert result.value == 72, result.answer
    assert not result.answer.assumptions
    assert not result.deficiencies()


@pytest.mark.parametrize(
    "count",
    [
        "24 are small",
        "24 marbles are green",
        "24 small marbles are small",
        "24 red marbles are small",
        "24 green marbles are large",
        "24 green crayons are small",
        "0 green marbles are small",
    ],
)
def test_nested_shares_require_two_matching_observed_attributes(registry, count):
    result = solve(
        f"{MARBLE_PARTITION}If {count}, how many marbles are there in the box?",
        registry,
    )
    assert not result.answer.committed, result.answer


@pytest.mark.parametrize("change", ["another-container", "another-parent", "flavored-items", "incompatible-attribute"])
def test_nested_shares_require_one_compatible_collection(registry, change):
    premise = MARBLE_PARTITION
    count = "24 green marbles are small"
    holder = "box"
    if change == "another-container":
        holder = "cabinet"
    elif change == "another-parent":
        premise = premise.replace("the green marbles", "the blue marbles")
    elif change == "flavored-items":
        premise = premise.replace("are small", "are mint flavored")
        count = "24 green marbles are mint flavored"
    else:
        premise = premise.replace("are small", "are ripe")
        count = "24 green marbles are ripe"
    result = solve(f"{premise}If {count}, how many marbles are there in the {holder}?", registry)
    assert not result.answer.committed, result.answer
