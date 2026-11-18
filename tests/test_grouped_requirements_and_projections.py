"""Invented paraphrases for capacities, rates and comparable quantities."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.tokenize import split_sentences


@pytest.fixture(scope="module")
def registry():
    return load_project(Path("projects/curated")).registry


CASES = {
    "mixed-cohorts": (
        "Mira needs to prepare notebooks for two groups that each have 7 children "
        "and a class with 5 children. How many notebooks does Mira need to prepare?",
        19, "one-item-per-recipient",
    ),
    "graded-cohorts": (
        "Kira needs to bake muffins for two second-grade classes that each have "
        "six children and a P.E. class with five children. How many muffins does she need to bake?",
        17, "one-item-per-recipient",
    ),
    "cohort-count-each": (
        "Mira needs to prepare notebooks for three groups with 5 children each "
        "and a class with 4 children. How many notebooks does Mira need to prepare?",
        19, "one-item-per-recipient",
    ),
    "explicit-tenure": (
        "Mira works for $10 per hour and 15 hours per week. She worked for 3 weeks. "
        "She saved all her money because she wants to buy a desk for $100. "
        "How much will Mira have left after she buys the desk?",
        350, None,
    ),
    "undated-budget": (
        "Mira works for $10 an hour and 15 hours a week. It's been a month since she "
        "started working. She saved all her money because she wants to purchase a desk for $100. "
        "How much money will she have left after she purchases the desk?",
        500, "undated-work-budget-weeks",
    ),
    "expanding-crew": (
        "Mira and Alex are loading a van with a capacity of 180 boxes at 9 boxes "
        "per minute per worker. They work for 5 minutes and are joined by 3 other "
        "workers who work at the same rate. How many minutes did loading the van take?",
        7, None,
    ),
    "elapsed-crew-expansion": (
        "Mira and Alex are loading a van with a capacity of 150 boxes at 10 boxes "
        "per minute per worker. After 3 minutes, 1 other worker joins them at the same rate. "
        "How many minutes did loading the van take?",
        6, None,
    ),
    "occupied-benches": (
        "24 benches with a capacity of 3 people each were placed for the meeting of a school, "
        "whose number of members was the same as the benches' capacity. "
        "If one quarter of the benches were not occupied and the rest each had two people, "
        "how many members attended the meeting?",
        36, "occupied-places-belong-to-group",
    ),
    "quote-per-bottle": (
        "The warehouse offers 24 bottles of juice for $12 per case. "
        "The shop offers 8 bottles of juice for $6. "
        "How much more does each bottle cost at the shop, in cents?",
        25, None,
    ),
    "quote-per-pack": (
        "The warehouse offers 10 boxes of apples for $25. "
        "The market offers the same apples for $18 and it has 6 boxes. "
        "How much more expensive per box in cents is the deal at the market?",
        50, "offer-count-covered-by-quote",
    ),
    "relative-material-lengths": (
        "Mira is making rolls of tape. The first roll is half the length of the second roll. "
        "The third roll is twice as long as the first roll. Mira used 18 inches of tape "
        "for the third roll. How many inches of tape did she use for the second roll?",
        18, "relative-extent-as-material-amount",
    ),
    "extent-projection": (
        "Mira grows 2 inches per year. If she is 3 feet tall, how tall will she be in 3 years?",
        3.5, None,
    ),
    "offset-before-multiple": (
        "Dana has 4 fewer marbles than three times as many as Mira has. "
        "If Mira has 6 marbles, how many marbles does Dana have?",
        14, None,
    ),
    "relative-event-frequency": (
        "The first dog jumped 3 times per minute. "
        "The second dog jumped twice as frequently as the first dog. "
        "How many jumps did the two dogs make in 4 minutes?",
        36, None,
    ),
    "combined-fittings": (
        "Nora is booking rooms for a group of 11 guests. Each room has two beds, "
        "which can fit two guests each, and a couch, which can fit one guest. "
        "How many rooms does Nora need to book?",
        3, None,
    ),
}


@pytest.mark.parametrize("case", CASES)
def test_composed_questions(registry, case):
    text, expected, assumption = CASES[case]
    result = solve(text, registry)
    assert result.answer.committed, result.answer
    assert result.value == pytest.approx(expected)
    assert not result.deficiencies()
    assert [item.id for item in result.answer.assumptions] == ([assumption] if assumption else [])


@pytest.mark.parametrize(
    "case, original, replacement",
    [
        ("mixed-cohorts", "each have", "have"),
        ("explicit-tenure", "after she buys the desk", "after she buys the bike"),
        ("expanding-crew", "capacity of 180", "capacity of 70"),
        ("expanding-crew", "at the same rate", "at a different rate"),
        ("occupied-benches", "each had two people", "each had four people"),
        ("occupied-benches", "one quarter", "one fifth"),
        ("quote-per-bottle", "8 bottles of juice", "8 bottles of milk"),
        ("quote-per-pack", "deal at the market", "deal at the warehouse"),
        ("relative-material-lengths", "18 inches of tape", "18 inches of yarn"),
        ("extent-projection", "3 feet tall", "3 feet wide"),
        ("relative-event-frequency", "the two dogs", "the three dogs"),
        ("combined-fittings", "fit one guest", "fit one student"),
    ],
)
def test_scope_and_capacity_boundaries(registry, case, original, replacement):
    text, _, _ = CASES[case]
    assert original in text
    result = solve(text.replace(original, replacement), registry)
    assert not result.answer.committed, result.answer


def test_initialism_inside_sentence_and_at_sentence_boundary():
    initialisms = ("p.e.",)
    text = "The P.E. class meets today. It is listed as P.E. Where do they meet?"
    assert split_sentences(text, initialisms=initialisms) == [
        "The P.E. class meets today.",
        "It is listed as P.E.",
        "Where do they meet?",
    ]
