"""An invoice may be divided among the purchasing groups or among their members."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/curated")).registry


INVOICE = "Two teams purchased the following: 6 tickets priced at $10 each. "
ROSTERS = "The first team has 4 players and the second team has 6 players. "
GROUP_SPLIT = "The teams split the invoice equally. "
WITHIN = "Each team splits its share equally among its players. "
ASK = "How much does each player pay?"
PAIR = "One team has 4 players and the other has 6. "


def check(reg, story, value, **kwargs):
    result = solve(story, reg, **kwargs)
    assert result.value == value, result.answer
    assert not result.deficiencies()
    return result.answer


def team_values(first, second):
    return [{"entity": "first team", "measure": "dollar", "value": first},
            {"entity": "second team", "measure": "dollar", "value": second}]


@pytest.mark.parametrize("sizes", [
    "Each team has 5 players. ",
    "Every team has 5 players. ",
    "The teams have 5 players each. ",
    "There are 5 players on each team. ",
])
def test_uniform_member_count_resolves_the_original_follow_up(reg, sizes):
    answer = check(reg, INVOICE + sizes + "How much does each player pay if they split the invoice equally?", 6)
    assert [a.id for a in answer.assumptions] == ["equal-member-contributions"]


@pytest.mark.parametrize("link", ["of", "with"])
def test_counted_teams_and_sizes_can_introduce_the_list(reg, link):
    text = INVOICE.replace("Two teams purchased", f"Two teams {link} 5 players each purchased")
    check(reg, text + "The players split the cost equally. " + ASK, 6)


@pytest.mark.parametrize("division", [
    "They split the invoice equally among all the players. ",
    "The players share the bill evenly. ",
    "The teams split the invoice equally among the players. ",
    "The bill is divided equally amongst the players. ",
    "The cost was split equally among players. ",
])
def test_equal_payment_across_the_whole_roster(reg, division):
    answer = check(reg, INVOICE + ROSTERS + division + ASK, 6)
    assert not answer.assumptions
    check(reg, INVOICE + ROSTERS + division + "How much does each team pay?", team_values(24, 36))


def test_equal_group_payments_have_different_member_shares(reg):
    story = INVOICE + ROSTERS + GROUP_SPLIT + WITHIN
    check(reg, story + ASK, team_values(7.5, 5))
    check(reg, story + "How much will each player on the first team pay?", 7.5)
    check(reg, story + "How much does each player on the second team pay?", 5)
    check(reg, story + "How much does each team pay?", 30)


@pytest.mark.parametrize("roster", [
    PAIR,
    "One team has four players, and the other has six players. ",
    "One team has 4 players and the other team has 6. ",
    "One team has 4 players and the other team has 6 players. ",
])
def test_one_group_and_the_other_use_the_stated_division(reg, roster):
    story = INVOICE + roster
    check(reg, story + "The players split the invoice equally. " + ASK, 6)
    check(reg, story + GROUP_SPLIT + WITHIN + ASK, [
        {"entity": "one team", "measure": "dollar", "value": 7.5},
        {"entity": "other team", "measure": "dollar", "value": 5},
    ])
    check(reg, story + GROUP_SPLIT + WITHIN + "How much does each player on the other team pay?", 5)


def test_two_equal_counts_and_repeated_numbers_keep_distinct_groups(reg):
    roster = "One class has 1 student and the other has 1. "
    story = INVOICE.replace("teams", "classes") + roster
    split = "The classes split the bill equally. Each class splits its share equally among its students. "
    check(reg, story + split + "How much does each student pay?", 30)


def test_unspecified_split_with_one_and_the_other_still_needs_clarification(reg):
    story = INVOICE + PAIR + "They split the bill equally. " + ASK
    answer = check(reg, story, None)
    assert {option.id for option in answer.clarification.options} == {"among-members", "within-groups"}
    check(reg, story, 6, interpretation="among-members")
    assert not solve(INVOICE + PAIR + GROUP_SPLIT + ASK, reg).answer.committed


@pytest.mark.parametrize("before, after", [
    ("Two teams", "Three teams"), ("One team", "Two teams"),
    ("the other has", "another has"), ("the other has", "the other class has"),
    ("the other has 6", "the other has 6 coaches"), ("has 6", "has at least 6"),
    ("has 6", "had 6"), ("4 players", "4 injured players"), ("has 6", "has 0"),
    ("each player pay", "each player on the first team pay"),
])
def test_contrasted_groups_must_identify_a_complete_pair(reg, before, after):
    text = INVOICE + PAIR + GROUP_SPLIT + WITHIN + ASK
    assert not solve(text.replace(before, after), reg).answer.committed


def test_group_shares_follow_the_ordinal_even_when_counts_are_given_out_of_order(reg):
    invoice = INVOICE.replace("Two teams", "Three teams")
    roster = "The third team has 2 players. The first team has 4 players. The second team has 5 players. "
    story = invoice + roster + GROUP_SPLIT + WITHIN
    check(reg, story + ASK, [
        {"entity": "first team", "measure": "dollar", "value": 5},
        {"entity": "second team", "measure": "dollar", "value": 4},
        {"entity": "third team", "measure": "dollar", "value": 10},
    ])
    check(reg, story + "How much does each player on the third team pay?", 10)


def test_equally_sized_indexed_groups_have_one_common_member_payment(reg):
    check(reg, INVOICE + ROSTERS.replace("6 players", "4 players") + GROUP_SPLIT + WITHIN + ASK, 7.5)


def test_unequal_groups_and_unspecified_division_offer_both_interpretations(reg):
    text = INVOICE + ROSTERS + "They split the bill equally. " + ASK
    answer = check(reg, text, None)
    assert {o.id for o in answer.clarification.options} == {"among-members", "within-groups"}
    for basis, expected in [("among-members", 6), ("within-groups", team_values(7.5, 5))]:
        assert check(reg, text, expected, interpretation=basis).clarification.selected == basis


def test_an_explicit_condition_selects_the_member_population(reg):
    check(reg, INVOICE + ROSTERS + "How much will each player pay if the players split the bill equally?", 6)
    check(reg, INVOICE + ROSTERS + "How much does each player pay if they divide the cost equally between the players?", 6)


def test_classes_and_students_use_the_same_allocation(reg):
    story = (INVOICE + ROSTERS + GROUP_SPLIT + WITHIN).replace("teams", "classes").replace("team", "class").replace("player", "student")
    check(reg, story + "How much does each student in the first class pay?", 7.5)


@pytest.mark.parametrize("change", [
    lambda s: s.replace("4 players and the second team has 6 players", "4 players"),
    lambda s: s.replace("6 players", "0 players"),
    lambda s: s.replace("4 players", "2.5 players"),
    lambda s: s.replace("second team", "third team"),
    lambda s: s.replace("second team", "first team"),
    lambda s: s.replace("second team", "second crew"),
    lambda s: s.replace("6 players", "6 coaches"),
    lambda s: s.replace("4 players", "4 injured players"),
    lambda s: s.replace("has 4 players", "owns 4 players"),
    lambda s: s.replace("has 4 players", "has at least 4 players"),
    lambda s: s.replace("The first team", "A team"),
    lambda s: s.replace(ROSTERS, "Every team has 5 players. " + ROSTERS),
    lambda s: s.replace(WITHIN, ""),
    lambda s: s.replace(GROUP_SPLIT, ""),
    lambda s: s.replace(GROUP_SPLIT, "The players split the bill equally. "),
    lambda s: s.replace("its players", "its coaches"),
    lambda s: s.replace("Each team splits", "Each team divide"),
    lambda s: s.replace("each player pay?", "each player on the third team pay?"),
    lambda s: s.replace("each player pay?", "each coach pay?"),
    lambda s: s.replace("priced at $10 each", "priced at $10 each plus a fee"),
])
def test_counts_and_both_divisions_must_identify_the_same_payers(reg, change):
    assert not solve(change(INVOICE + ROSTERS + GROUP_SPLIT + WITHIN + ASK), reg).answer.committed


def test_a_roster_alone_does_not_establish_equal_sharing(reg):
    assert not solve(INVOICE + ROSTERS + ASK, reg).answer.committed
    assert not solve(INVOICE + "They split the bill equally. " + ASK, reg).answer.committed
