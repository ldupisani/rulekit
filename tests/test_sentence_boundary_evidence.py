"""Independent factual clauses keep their operands, identities and assumptions."""

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import BatchEvidence, Quantity
from test_composed_quantity_accounts import tank
from test_fractional_resource_references import allocation
from test_itemized_group_shares import ASK, GROUP_SPLIT, INVOICE, WITHIN
from test_population_partitive_rates import inquiry, partition
from test_relative_quantity_compositions import CASES, MARBLE_PARTITION
from test_scoped_quantity_compositions import purchase


@pytest.fixture(scope="module")
def reg():
    return load_project("projects/curated").registry


def equivalent(reg, joined, separate, value):
    assert joined != separate
    original, split = (solve(text, reg) for text in (joined, separate))
    for result in (original, split):
        assert result.answer.kind == "number", result.answer
        assert result.value == pytest.approx(value)
        assert not result.deficiencies()
    assert [a.id for a in split.answer.assumptions] == [a.id for a in original.answer.assumptions]
    return split


@pytest.mark.parametrize("separate", [
    "She brought $5 with her. She leaves with $1.",
    "Nora brought $5 with her. Nora leaves with $1.",
])
def test_opening_and_closing_cash(reg, separate):
    original = purchase()
    split = equivalent(reg, original, original.replace("She brought $5 with her and leaves with $1.", separate), 8)
    opening, closing = split.store.by_kind(BatchEvidence)
    assert opening.entity_ref == closing.entity_ref
    assert opening.provenance.sentence < closing.provenance.sentence


@pytest.mark.parametrize("cash", [
    "Nora leaves with $1. Nora brought $5 with her.",
    "Nora brought $5 with her. Mira leaves with $1.",
    "Nora brought $5 with her. She receives $3. She leaves with $1.",
    "Nora brought $5 with her. She leaves with £1.",
])
def test_cash_changes_require_one_ordered_purchase(reg, cash):
    assert not solve(purchase().replace("She brought $5 with her and leaves with $1.", cash), reg).answer.committed


DIMS = "The tank is 2 feet long, 3 feet wide, and 4 feet high."


@pytest.mark.parametrize("separate", [
    "The tank is 2 feet long. The tank is 3 feet wide. The tank is 4 feet high.",
    "The tank is 4 feet high. The tank is 2 feet long. The tank is 3 feet wide.",
    "The tank is 2 feet long. The tank is 3 feet wide. The tank is twice as high as it is long.",
])
def test_axes_keep_the_holder_unit_and_shape_assumption(reg, separate):
    result = equivalent(reg, tank(), tank().replace(DIMS, separate), 18)
    direct = [q for q in result.store.by_kind(Quantity) if q.measurement_axis]
    relative = [r for r in result.store.by_kind(BatchEvidence) if r.kind == "relative-axis"]
    assert {q.measurement_axis for q in direct} | {r.marker for r in relative} == {"long", "wide", "high"}
    assert result.answer.assumptions[0].sentences == tuple(sorted(r.provenance.sentence for r in direct + relative))


@pytest.mark.parametrize("width", [
    "The tank is 3 feet long.", "The box is 3 feet wide.", "The tank is 3 hours wide.",
])
def test_three_numbers_do_not_establish_three_axes(reg, width):
    separate = f"The tank is 2 feet long. {width} The tank is 4 feet high."
    assert not solve(tank().replace(DIMS, separate), reg).answer.committed


@pytest.mark.parametrize("case", ["explicit-nested-parent", "assumed-nested-parent"])
def test_color_and_flavor_subset_evidence(reg, case):
    joined, value, _ = CASES[case]
    separate = joined.replace(", and half", ". Half").replace(", and one third", ". One third")
    equivalent(reg, joined, separate, value)


def test_nested_size_and_color_in_separate_sentences(reg):
    question = "If 24 green marbles are small, how many marbles are there in the box?"
    joined = MARBLE_PARTITION + question
    separate = joined.replace(", and one third", ". One third")
    equivalent(reg, joined, separate, 96)
    for change in [("the green marbles are", "the blue marbles are"),
                   ("24 green marbles", "24 marbles"), ("are small", "are lemon flavored")]:
        assert not solve(separate.replace(*change), reg).answer.committed


@pytest.mark.parametrize("remaining", ["The rest gets", "The remaining farm workers receive"])
def test_complement_identifies_the_same_population(reg, remaining):
    joined = partition() + ". What is the total amount of money the workers get per day?"
    separate = joined.replace(" while the rest gets", ". " + remaining)
    equivalent(reg, joined, separate, 252)
    assert not solve(separate.replace(remaining, "The remaining school workers receive"), reg).answer.committed


def test_separately_reported_population_count(reg):
    joined = inquiry()
    equivalent(reg, joined, joined.replace(" while the rest gets", ". The rest gets"), 252)


def test_repeated_parts_of_day_and_recipient(reg):
    joined = ("Nora feeds the birds in January and February. "
              "She feeds them 1/4 cup in the morning and 3/4 cup in the afternoon. "
              "How many cups of food will she need for all two months?")
    separate = joined.replace(" and 3/4 cup", ". She feeds them 3/4 cup")
    equivalent(reg, joined, separate, 59)
    for change in [("in the afternoon", "in the morning"), ("3/4 cup", "3/4 foot"),
                   ("She feeds them 3/4", "Mira feeds them 3/4")]:
        assert not solve(separate.replace(*change), reg).answer.committed


@pytest.mark.parametrize("counterpart", ["The other team has 6 players.", "The other has 6.",
                                          "The other has 6 players.", "The other team has 6."])
def test_separate_pair_counts_and_unequal_division(reg, counterpart):
    group = f"One team has 4 players. {counterpart} "
    account = INVOICE + group
    split = "The players split the invoice equally. " + ASK
    equivalent(reg, account.replace(". The other", " and the other") + split, account + split, 6)
    by_team = solve(account + GROUP_SPLIT + WITHIN + ASK, reg)
    assert [line["value"] for line in by_team.value] == [7.5, 5]
    unspecified = solve(account + "They split the bill equally. " + ASK, reg)
    assert {option.id for option in unspecified.answer.clarification.options} == {"among-members", "within-groups"}
    for change in [("Two teams", "Three teams"), ("other", "another"), ("has 6", "had 6")]:
        assert not solve((account + split).replace(*change), reg).answer.committed


def test_explicit_original_stock_survives_depletion(reg):
    joined = allocation()
    separate = joined.replace("one-half of it", "one-half of the original clay").replace(
        ", one-fourth of it", ". She used one-fourth of the original clay").replace(
        ", and one-third", ". She used one-third")
    equivalent(reg, joined, separate, 2)
    ambiguous = separate.replace("one-fourth of the original clay", "one-fourth of it")
    assert not solve(ambiguous, reg).answer.committed


@pytest.mark.parametrize("boundary", [" and ", ", and ", ", ", "; "])
def test_complete_cash_clauses_use_the_same_evidence_on_either_side(reg, boundary):
    separate = "Nora brought $5 with her. She leaves with $1."
    joined = separate.replace(". She ", boundary + "she ")
    story = purchase().replace("She brought $5 with her and leaves with $1.", separate)
    equivalent(reg, story.replace(separate, joined), story, 8)


def test_combined_height_accepts_equivalent_axis_labels(reg):
    story = "The tank is 2 feet high. The box is 3 feet tall. Calculate their combined height."
    assert solve(story, reg).value == 5
    different_axis = solve(story.replace("3 feet tall", "3 feet wide"), reg)
    assert not different_axis.answer.committed
    assert "distinct measured axes" in different_axis.answer.reason


@pytest.mark.parametrize("counterpart", ["The other class has 6.", "The other has 6 coaches.",
                                          "The other team has 6 injured players."])
def test_explicit_counterpart_constraints_must_match(reg, counterpart):
    text = INVOICE + "One team has 4 players. " + counterpart + " The players split the invoice equally. " + ASK
    assert not solve(text, reg).answer.committed
