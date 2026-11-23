"""Paired readings of invented questions with and without repeated context."""

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from test_calendar_and_quantity_accounts import bonus, calibration, order, sections
from test_composed_quantity_accounts import tank
from test_grouped_requirements_and_projections import CASES
from test_journey_duration import story as journey
from test_proportional_portions_sales import sales
from test_scoped_quantity_compositions import available, indexed, purchase
from test_scoped_schedule_compositions import attendance
from test_scoped_shares_bills_recipes import recipe


@pytest.fixture(scope="module")
def reg():
    return load_project("projects/curated").registry


SALES = "Mira is a painter. She paints pictures and sells them at the park. " + sales().replace(
    "Mira charges", "She charges"
)
SAVINGS = (
    "Nora and Iris save half of their income for a trip. Nora earns $8 per day. "
    "Iris earns $2 per day. How much money will they have saved after a year?"
)
CALENDAR = (
    "Nora feeds the birds in January and February of 2027. "
    "She feeds them 1/4 cup in the morning and 3/4 cup in the afternoon. "
    "How many cups of food will she need for all two months?"
)
INVOICE = (
    "Four friends buy the following: 4 pencils that cost $2 each; and 2 books that cost $4 each. "
    "They divide the bill equally. How much does each friend pay?"
)
ORDER = (
    "Three friends eat at a restaurant and order the following: "
    "3 pieces of cake that cost $2 each; and 3 cups of soda that cost $1 each. "
    "They split the bill equally. How much does each friend pay?"
)
ROUNDS = (
    "Nora and Iris had a skipping contest. The contest was split into two rounds. "
    "Nora completed 2 more skips than Iris in the first round. "
    "Nora got tired and only completed half the number of skips as Iris in the last round. "
    "If Iris skipped 10 times in each round, what is the average number of skips per round completed by Nora?"
)
CAPACITY = CASES["occupied-benches"][0]
MEMBERSHIP = ", whose number of members was the same as the benches' capacity"
CREW = CASES["expanding-crew"][0]
EVAPORATION = tank().replace("She spills half the water in the tank.", "While she's gone, half the water in the tank evaporates.")


SHORT_FORMS = {
    "sale-without-venue": (SALES, " at the park", "", 336),
    "sale-without-background": (SALES, "She paints pictures and sells them at the park. ", "", 336),
    "savings-without-purpose": (SAVINGS, " for a trip", "", 1825),
    "purchase-without-venue": (purchase(), " to the store", "", 8),
    "cash-without-self-reference": (purchase(), " with her and", " and", 8),
    "booking-without-venue": (available(), " in a hotel", "", 25),
    "exclusion-without-cause": (available(), "Because of rain, the", "The", 25),
    "exclusion-without-beneficiaries": (available(), " for the guests", "", 25),
    "room-count-without-identical": (available(), "identical ", "", 25),
    "occupancy-without-membership-count": (CAPACITY, MEMBERSHIP, "", 36),
    "occupancy-without-organization": (CAPACITY, " of a school" + MEMBERSHIP, "", 36),
    "expanded-crew-at-same-rate": (CREW, "who work at the same rate", "at the same rate", 7),
    "both-calendar-months": (CALENDAR, "all two months", "both months", 59),
    "the-two-calendar-months": (CALENDAR, "all two months", "the two months", 59),
    "invoice-without-introduction": (INVOICE, "buy the following:", "buy", 4),
    "invoice-with-plain-conjunction": (INVOICE, "buy the following: 4 pencils that cost $2 each; and", "buy 4 pencils that cost $2 each and", 4),
    "ordering-without-venue": (ORDER, " at a restaurant", "", 3),
    "ordering-without-dining": (ORDER, "eat at a restaurant and ", "", 3),
    "purchase-without-also": (order(), "She also orders", "She orders", 20),
    "cost-without-altogether": (order(), " altogether", "", 20),
    "adjustment-without-repeated-bonus": (bonus(), " for the bonus.", ".", 7.5),
    "sale-without-money-noun": (calibration(), "How much money", "How much", 40),
    "section-without-then": (sections(), "Then, Nora sorted", "Nora sorted", 13),
    "sections-without-introduction": (sections(), "Nora sorts hats from a box. ", "", 13),
    "sections-without-repeated-holder": (sections(), "Nora sorts hats from a box.", "Nora sorts hats.", 13),
    "stock-at-the-start": (sections(), "when Nora started", "at the start", 13),
    "plan-without-purpose": (recipe(), " for a party.", ".", 6),
    "direct-ratio-observation": (recipe(), "She knows her mom drinks", "Her mom drinks", 6),
    "population-without-there": (recipe(), "people there", "people", 6),
    "adoption-without-repeated-scope": (recipe(), "the same ratio for the party", "the same ratio", 6),
    "attendance-without-venue": (attendance(), " at the park", "", 60),
    "attendance-without-total-marker": (attendance(), " altogether?", "?", 60),
    "active-relative-performance": (indexed(), "completed by Nora", "Nora completed", 11),
    "average-as-verb": (indexed(), "what is the average number of skips per round completed by Nora", "how many skips did Nora average per round", 11),
    "evaporation-without-absence": (EVAPORATION, "While she's gone, half", "Half", 18),
    "spill-without-absence": (EVAPORATION.replace("half the water in the tank evaporates", "her dog spills half the water in the tank"),
     "While she's gone, her dog", "Her dog", 18),
    "provision-without-repeated-activity": (CASES["mixed-cohorts"][0], "does Mira need to prepare", "does Mira need", 19),
    "only-without-condition": (ROUNDS, "got tired and only completed", "only completed", 8.5),
    "performance-without-condition": (ROUNDS, "got tired and only completed", "completed", 8.5),
    "journey-without-repeated-modes": (journey(), " with walking and biking", "", 7),
    "journey-without-total-marker": (journey(), " in total", "", 7),
}


@pytest.mark.parametrize("question,phrase,replacement,value", SHORT_FORMS.values(), ids=SHORT_FORMS)
def test_omission_preserves_value_and_assumptions(reg, question, phrase, replacement, value):
    assert phrase in question
    original = solve(question, reg)
    shorter = solve(question.replace(phrase, replacement), reg)
    for result in (original, shorter):
        assert result.value == pytest.approx(value), result.answer
        assert not result.deficiencies()
    assert [a.id for a in shorter.answer.assumptions] == [a.id for a in original.answer.assumptions]


MISSING_EVIDENCE = {
    "one-way-schedule": (journey().replace(" with walking and biking", ""), "to and from school twice", "to school twice"),
    "division-unspecified": (INVOICE.replace("buy the following:", "buy"), "They divide the bill equally. ", ""),
    "crew-rate-unspecified": (CREW, " who work at the same rate", ""),
    "ratio-never-adopted": (recipe().replace(" for a party.", "."), "She will use the same ratio for the party. ", ""),
    "conflicting-adoption-scope": (recipe().replace(" for a party.", "."), "the same ratio for the party", "the same ratio for her family"),
    "no-sale": (calibration(), "from selling all the foam", "from making all the foam"),
    "both-refers-to-three": (CALENDAR.replace("all two months", "both months"), "January and February", "January, February and March"),
    "changed-participant": (ROUNDS.replace("got tired and only ", ""), "Nora and Iris had", "Nora and Theo had"),
    "changed-performance": (indexed(), "completed by Nora", "Nora jumped"),
    "changed-passive-performance": (indexed(), "completed by Nora", "jumped by Nora"),
    "singular-count-question": (indexed(), "what is the average number of skips per round completed by Nora",
                                "how many skip did Nora average per round"),
    "finite-predicate-after-modal": (CALENDAR.replace("all two months", "both months"), "she need", "she needed"),
    "unidentified-subgroup": (CAPACITY.replace(MEMBERSHIP, ""), "members attended", "gardeners attended"),
    "different-holder": (sections().replace("Nora sorts hats from a box. ", ""), "from the bottom of the box", "from the bottom of the cart"),
    "different-stock-actor": (sections().replace("Nora sorts hats from a box.", "Nora sorts hats."), "Then, Nora sorted", "Then, Theo sorted"),
    "unstated-saving-purpose": (SAVINGS.replace(" for a trip", ""), "saved after a year", "saved for their trip after a year"),
    "conditional-loss": (EVAPORATION, "While she's gone, half", "If half"),
}


@pytest.mark.parametrize("question,phrase,replacement", MISSING_EVIDENCE.values(), ids=MISSING_EVIDENCE)
def test_short_forms_still_require_the_decisive_evidence(reg, question, phrase, replacement):
    assert phrase in question
    assert not solve(question.replace(phrase, replacement), reg).answer.committed


@pytest.mark.parametrize("items,value", [
    ("4 pencils that cost $2 in total and 2 books that cost $4 each", 2.5),
    ("4 pencils that cost $2 each and 2 books that cost $4 in total", 3),
    ("4 pencils that cost $2 each, 2 hats that cost $4 each, and 2 books that cost $4 each", 6),
])
def test_inline_purchases_keep_every_price_basis(reg, items, value):
    result = solve(f"Four friends buy {items}. They divide the invoice equally. How much does each friend pay?", reg)
    assert result.value == value, result.answer
    assert not result.deficiencies()


def test_undated_month_pair_keeps_its_calendar_assumption(reg):
    result = solve(CALENDAR.replace(" of 2027", "").replace("all two months", "both months"), reg)
    assert result.value == 59
    assert "non-leap" in result.answer.reason
    assert [a.id for a in result.answer.assumptions] == ["non-leap-calendar"]
