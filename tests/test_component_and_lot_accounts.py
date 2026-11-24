"""Invented accounts with equivalent clause boundaries and incompatible evidence."""

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project("projects/curated").registry


PROMOTION = (
    "Every fourth customer gets a free ticket. Tickets cost $4 each. "
    "Nora sold $36 worth of tickets. How many free tickets did Nora give away?"
)
STOCK = (
    "Nora started with 90 marbles. She gave away 18 marbles to her friends. "
    "She gave 12 marbles to her brothers. She sold half of the remaining marbles. "
    "How many marbles did she have left?"
)
PROGRESS = (
    "Iris read 3 chapters of a book. Iris read 8 pages of the 4th chapter of the book. "
    "Iris did not read the remaining pages of chapter four. Iris read 2 more chapters of the book. "
    "Each chapter in the book had 20 pages. How many pages did Iris read in total?"
)
PACKAGE = (
    "Nora bought 3 cartons of milk that are 2 liters each. The price of milk is $4 per liter. "
    "How much did Nora pay?"
)
LOCATION = (
    "There are 24 students in a class. One quarter are absent. "
    "One third of the students who are present are in the classroom. The rest are in the library. "
    "How many students are in the library?"
)
ADMISSION = (
    "A couple with two children, ages 8 and 12 years old, decided to go to a museum. "
    "The regular ticket costs $20. Children below 12 years old have a $3 discount. "
    "They gave the cashier $100. How much change will they receive?"
)
AREA = (
    "Nora's garden is 30 square meters larger than twice Iris's garden. "
    "Nora's garden is 150 square meters. How many square meters is Iris's garden?"
)
INPUT = (
    "Nora makes clay models of birds. Large birds take 6 blocks of clay. Small birds take 2 blocks. "
    "Nora made twice as many small birds as large birds. Nora used 16 blocks of clay for small birds. "
    "How many blocks of clay did Nora use in total?"
)
LOADS = (
    "2 teams of 3 people shared a house for 4 days. Each person uses 1 blanket per day. "
    "The truck can hold 10 blankets per load. How many loads will it take to transport all the blankets?"
)
SAVINGS = (
    "A gallon of milk normally costs $5. A gallon of milk now costs $3. "
    "A box of cereal has a $1 discount. You buy 2 gallons of milk and 4 boxes of cereal. "
    "How much will you save in total?"
)


@pytest.mark.parametrize(
    "text,expected",
    [
        (PROMOTION, 3),
        (STOCK, 30),
        (PROGRESS, 108),
        (PACKAGE, 24),
        (PACKAGE.replace("The price of milk is", "Milk costs"), 24),
        (LOCATION, 12),
        (
            LOCATION.replace("24 students", "90 students").replace(
                "One quarter are absent", "One third are absent"
            ),
            40,
        ),
        (PROMOTION.replace("$4 each", "$0.10 each").replace("$36 worth", "$0.70 worth"), 2),
        (ADMISSION, 23),
        (AREA, 60),
        (INPUT, 40),
        (LOADS, 3),
        (SAVINGS, 8),
        (PROGRESS.replace("4th chapter", "fourth chapter"), 108),
        (PROGRESS.replace("chapter", "section").replace("book", "report"), 108),
        (PROMOTION.replace("free tickets did", "free ones did"), 3),
        (PROMOTION.replace("Tickets cost $4 each", "Each ticket costs $4"), 3),
        (
            PROMOTION.replace("ticket", "book")
            .replace("Tickets", "Books")
            .replace("customer", "shopper"),
            3,
        ),
        (
            PROGRESS.replace(
                "Iris did not read the remaining pages of chapter four. Iris read 2 more chapters of the book. ",
                "",
            ),
            68,
        ),
        (
            PACKAGE.replace(
                " that are 2 liters each", ". Each carton of milk weighs 2 kilograms"
            ).replace("per liter", "per kilogram"),
            24,
        ),
        (PACKAGE.replace(" that are 2 liters each", ". Each carton contains 2 liters"), 24),
        (PACKAGE.replace("2 liters", "500 milliliters"), 6),
        (
            STOCK.replace(
                "She gave away 18 marbles to her friends. She gave 12 marbles to her brothers.",
                "She gave away 30 marbles to her friends.",
            ),
            30,
        ),
        (
            LOCATION.replace(
                "One quarter are absent. One third",
                "One quarter of the students are absent, and one third",
            ).replace("students who are present", "present students"),
            12,
        ),
        (
            LOCATION.replace("students", "workers")
            .replace("in a class", "in a warehouse")
            .replace("classroom", "office")
            .replace("library", "garden"),
            12,
        ),
        (
            ADMISSION.replace(
                "A couple with two children, ages 8 and 12 years old, decided to go to a museum.",
                "Two adults and 2 children went to a museum. The children are 8 and 12 years old.",
            ),
            23,
        ),
        (
            AREA.replace(
                "How many square meters is Iris's garden?",
                "What is the area of Iris's garden in square meters?",
            ),
            60,
        ),
        (AREA.replace("How many square meters", "How many square centimeters"), 600000),
        (
            INPUT.replace("of clay. Small birds", "of clay and small birds").replace(
                "large birds. Nora used", "large birds; Nora used"
            ),
            40,
        ),
        (INPUT.replace("Nora makes clay models of birds. ", "").replace("birds", "panels"), 40),
        (
            ADMISSION.replace(
                "A couple with two children, ages 8 and 12 years old, decided to go to a museum.",
                "Two adults and 3 children went to a museum. The first child is 7 years old. "
                "The second child is 8 years old. The third child is 12 years old.",
            ),
            6,
        ),
        (LOADS.replace("2 teams of 3 people shared", "Each team has 3 people. Two teams shared"), 3),
        (SAVINGS.replace("milk and 4 boxes", "milk. You buy 4 boxes"), 8),
        (SAVINGS.replace("milk", "oil").replace("cereal", "pencils").replace("normally", "usually"), 8),
        (PROMOTION.replace("How many", "Nora stopped after the last customer paid. How many"), 2),
    ],
)
def test_composed_amounts(reg, text, expected):
    result = solve(text, reg)
    assert result.value == pytest.approx(expected), result.answer
    assert not result.deficiencies()


@pytest.mark.parametrize(
    "text,old,new",
    [
        (PROMOTION, "free tickets did", "free books did"),
        (AREA, "How many square", "Ava's field is 200 square meters. How many square"),
        (PROMOTION, "worth of tickets", "worth of books"),
        (PROMOTION, "$36", "$37"),
        (PROGRESS, "4th chapter", "5th chapter"),
        (PROGRESS, "8 pages", "21 pages"),
        (PROGRESS, "of chapter four", "of chapter three"),
        (PACKAGE, " that are 2 liters each", ". Each carton weighs 2 liters"),
        (PACKAGE, "price of milk", "price of oil"),
        (PACKAGE, "per liter", "per kilogram"),
        (PACKAGE, "Nora pay", "Iris pay"),
        (LOCATION, "the rest are in the library", "the rest are in the classroom"),
        (LOCATION, "24 students", "25 students"),
        (ADMISSION, "two children", "three children"),
        (ADMISSION, "$100", "$10"),
        (AREA, "150 square meters", "15 square meters"),
        (AREA, "Iris's garden?", "Ava's garden?"),
        (INPUT, "16 blocks", "15 blocks"),
        (INPUT, "use in total", "use in total for large birds"),
        (INPUT, "blocks of clay did", "blocks of wax did"),
        (LOADS, "10 blankets", "10 towels"),
        (LOADS, "to transport", "to wash"),
        (SAVINGS, "You buy 2 gallons of milk", "You buy 2 boxes of milk"),
        (SAVINGS, "milk now costs $3", "milk now costs $6"),
    ],
)
def test_missing_or_conflicting_component_evidence(reg, text, old, new):
    assert old.lower() in text.lower()
    # Keep the sentence-initial capitalization for the location clause.
    if old not in text:
        old, new = old.capitalize(), new.capitalize()
    assert not solve(text.replace(old, new), reg).answer.committed


def test_reported_promotion_assumptions(reg):
    result = solve(PROMOTION, reg)
    assert {a.id for a in result.answer.assumptions} == {
        "one-item-per-customer",
        "earned-free-item-delivered",
    }


@pytest.mark.parametrize(
    "premise,expected",
    [
        ("Two coaches with five players went to the park.", 7),
        ("A trio with four students.", 7),
        ("A teacher with three students, ages 8, 8, and 10 years old, went to the library.", 4),
        ("A teacher with three students. The students are 8, 8 and 10 years old.", 4),
        (
            "Two teachers and two students. The teachers are 30 and 40 years old. The students are 8 and 10 years old.",
            4,
        ),
    ],
)
def test_group_headcount_is_independent_of_admission(reg, premise, expected):
    r = solve(premise + " How many people were in the group?", reg)
    assert r.value == expected, r.answer
    assert not r.deficiencies()


@pytest.mark.parametrize(
    "premise",
    [
        "A family with three students went to the library.",
        "A teacher with three students, ages 8 and 10 years old.",
        "A teacher with three students, ages 8 9 and 10 years old.",
        "A teacher with three students, ages 8 or 9 and 10 years old.",
        "A teacher with two students, ages $8 and 10 years old.",
        "A teacher with two students, ages 6 months and 10 years old.",
        "A teacher with two students. The players are 8 and 10 years old.",
        "Two teachers with two teachers went to the museum.",
    ],
)
def test_group_size_or_age_attachment_is_underdetermined(reg, premise):
    assert not solve(premise + " How many people were in the group?", reg).answer.committed


@pytest.mark.parametrize(
    "description",
    [
        "Two coaches with three players, ages 6, 8 and 12 years old, went to the park.",
        "Two coaches with three players went to the park. The players are 6, 8 and 12 years old.",
    ],
)
@pytest.mark.parametrize("join", [". Players", ", but players"])
def test_nonfamily_discount_uses_the_named_subgroup(reg, description, join):
    q = (
        description + " The regular ticket costs $20" + join + " below 12 years old have a $3 discount. "
        "They gave the clerk $100. How much change will they receive?"
    )
    r = solve(q, reg)
    assert r.value == 6, r.answer
    assert not r.deficiencies()
    discounts = [row for row in r.store.facts if getattr(row, "kind", "") == "cohort-discount"]
    assert [row.container_ref.head for row in discounts] == ["player"]


def test_inline_age_evidence_identifies_the_subgroup_and_preserves_repeated_ages(reg):
    q = "A teacher with three students, ages 8, 8 and 10 years old, decided to go to the library. How many people were in the group?"
    r = solve(q, reg)
    assert r.value == 4
    members = [row for row in r.store.facts if getattr(row, "kind", "") == "group-members"]
    ages = [row for row in r.store.facts if getattr(row, "kind", "") == "group-member-measurement"]
    assert sorted((row.entity, row.verb, row.acquisition, row.attribute) for row in members) == [
        ("student", "go", "library", "decide"),
        ("teacher", "go", "library", "decide"),
    ]
    assert sorted((row.entity_ref.head, row.measure, row.value) for row in ages) == [
        ("student", "year", 8),
        ("student", "year", 8),
        ("student", "year", 10),
    ]
    assert len({row.position for row in ages}) == 3


def test_collective_size_does_not_assign_an_age_to_its_members(reg):
    r = solve(ADMISSION, reg)
    assert r.value == 23
    assert {a.id for a in r.answer.assumptions} == {
        "assumed-purchase-per-member",
        "regular-price-for-unspecified-members",
    }
    assert all(
        row.entity == "child"
        for row in r.store.facts
        if getattr(row, "kind", "") == "group-member-measurement"
    )


@pytest.mark.parametrize(
    "purchase,quote,offer,expected",
    [
        (
            "They each bought two books.",
            "A book costs $8.",
            "Players get a $2 discount on each book.",
            68,
        ),
        (
            "Each person purchased two books.",
            "The regular price of a book is $8.",
            "Players receive a $2 discount on each book.",
            68,
        ),
        (
            "They each bought two books.",
            "Books are $8 each.",
            "Coaches have a $2 discount on each book.",
            72,
        ),
        (
            "Each person purchased one rental.",
            "The usual rental costs $8.",
            "Players have a $2 discount.",
            34,
        ),
    ],
)
def test_cohort_discount_on_goods_and_services(reg, purchase, quote, offer, expected):
    story = f"Two coaches with three players. {purchase} {quote} {offer}"
    total = solve(story + " How much did they pay in total?", reg)
    change = solve(story + " They gave the clerk $100. How much change will they receive?", reg)
    assert (total.value, change.value) == (expected, 100 - expected)
    assert not total.deficiencies() and not change.deficiencies()
    assert not total.answer.assumptions and not change.answer.assumptions


HEIGHT_OFFER = (
    "Two coaches with three players. Each person bought one book. "
    "The players are 130, 145 and 150 centimeters tall. The players are 12, 13 and 14 years old. "
    "The regular book costs $20. Players below 1.5 meters high get a $3 discount. "
    "They gave the clerk $100. How much change will they receive?"
)


@pytest.mark.parametrize(
    "comparison,expected",
    [("below", 6), ("under", 6), ("above", 0), ("over", 0), ("at or above", 3), ("at or below", 9)],
)
def test_cohort_eligibility_uses_property_direction_units_and_endpoint(reg, comparison, expected):
    result = solve(HEIGHT_OFFER.replace("below", comparison), reg)
    assert result.value == expected, result.answer
    assert not result.deficiencies()


@pytest.mark.parametrize(
    "old,new",
    [
        ("centimeters tall", "years tall"),
        ("centimeters tall", "centimeters wide"),
        ("meters high", "years high"),
        ("Players below", "Coaches below"),
        ("130, 145 and 150", "130 and 145"),
        ("Each person bought one book. ", ""),
        ("one book", "two books"),
        ("one book", "one pencil"),
        ("a $3 discount", "a $3 discount on each rental"),
        ("below", "at and above"),
    ],
)
def test_cohort_offer_requires_matching_quantity_eligibility_and_goods(reg, old, new):
    assert not solve(HEIGHT_OFFER.replace(old, new), reg).answer.committed


def test_group_purchase_pronoun_after_a_subgroup_needs_a_clear_buyer(reg):
    story = (
        "Two coaches with three players. The players are 8, 10 and 12 years old. "
        "They each bought one book. The regular book costs $20. Players have a $3 discount. "
        "How much did they pay?"
    )
    assert not solve(story, reg).answer.committed
    assert solve(story.replace("They each", "Each person"), reg).value == 91


@pytest.mark.parametrize("quote", ["The regular book costs $8.", "The regular price of a book is $8."])
def test_regular_quote_also_feeds_an_individual_purchase(reg, quote):
    result = solve(quote + " Iris bought 3 books. How much did Iris spend?", reg)
    assert result.value == 24
    assert not result.deficiencies()


def test_group_change_uses_the_tender_denomination(reg):
    result = solve(
        "Two teachers with three students. Each person bought one pencil. "
        "The regular pencil costs 30 cents. Students have a 10 cents discount. "
        "They gave the clerk $2. How much change will they receive?",
        reg,
    )
    assert result.value == pytest.approx(0.80), result.answer
    assert not result.deficiencies()


@pytest.mark.parametrize(
    "action,past,part,work,unit,predicate",
    [
        ("read", "read", "chapter", "novel", "pages", "has"),
        ("watch", "watched", "episode", "series", "minutes", "lasts"),
        ("listen to", "listened to", "track", "recording", "minutes", "lasts"),
        ("listen to", "listened to", "episode", "podcast", "minutes", "has"),
    ],
)
@pytest.mark.parametrize("combined", [False, True])
def test_section_progress_keeps_the_activity_work_and_measured_extent(
    reg, action, past, part, work, unit, predicate, combined
):
    separator = " but " if combined else ". Iris "
    q = (
        f"Iris {past} 2 {part}s of a {work}. Iris {past} 6 {unit} of the third {part} of the {work}. "
        f"Iris did not {action} the remaining {unit} of {part} three{separator}{past} 2 more {part}s of the {work}. "
        f"Each {part} {predicate} 12 {unit}. "
    )
    asks = (
        f"Calculate the total number of {unit} that Iris {past} altogether?",
        f"What is the total number of {unit} Iris {past}?",
        f"How many {unit} did Iris {action} in total?",
    )
    for ask in asks:
        result = solve(q + ask, reg)
        assert result.value == 54, (ask, result.answer)
        assert not result.deficiencies()
        events = [
            row
            for row in result.store.facts
            if getattr(row, "kind", "")
            in {
                "completed-sections",
                "partial-section",
                "skipped-section-remainder",
                "additional-sections",
            }
        ]
        assert len(events) == 4
        assert all(row.verb == action for row in events)


def test_timed_section_progress_converts_to_the_requested_unit(reg):
    whole = "Nora watched 2 episodes of a series. "
    size = "Each episode lasts 1.5 hours. "
    partial = "Nora watched 15 minutes of the third episode of the series. "
    ask = "How many minutes did Nora watch in total?"
    assert solve(whole + size + ask, reg).value == 180
    assert solve(whole + partial + size + ask, reg).value == 195


@pytest.mark.parametrize(
    "change",
    [
        ("Nora watched 5 minutes", "Nora listened to 5 minutes"),
        ("Nora watch in total", "Nora listen to in total"),
        ("10 minutes", "10 pages"),
        ("5 minutes", "5 pages"),
        ("the series", "the video"),
        ("Nora watched 5 minutes", "Iris watched 5 minutes"),
        ("Nora watched 2 episodes", "Nora read 2 episodes"),
    ],
)
def test_content_progress_requires_a_compatible_activity_frame(reg, change):
    q = (
        "Nora watched 2 episodes of a series. Nora watched 5 minutes of the third episode of the series. "
        "Each episode has 10 minutes. How many minutes did Nora watch in total?"
    )
    assert not solve(q.replace(*change), reg).answer.committed


def test_written_sections_support_units_other_than_pages(reg):
    story = "Nora read two sections of a report. Each section has 80 words. "
    assert solve(story + "How many words of the report did Nora read?", reg).value == 160
    for ask in (
        "How many pages of the report did Nora read?",
        "How many words of the novel did Nora read?",
    ):
        assert not solve(story + ask, reg).answer.committed
