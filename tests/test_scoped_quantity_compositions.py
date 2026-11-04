"""Invented affine, indexed and monetary compositions with explicit scope boundaries."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.affine_graph import AffineGraph, AffineError
from rulekit.kernel.engine import solve
from rulekit.kernel.evaluate import ArithmeticLog


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/curated")).registry


def number(reg, text, value):
    result = solve(text, reg)
    assert result.answer.committed, result.answer
    assert result.value == pytest.approx(value)
    assert not result.deficiencies()
    return result


def test_affine_graph_keeps_free_origins_symbolic():
    graph = AffineGraph([], [("a", "b", 1, 3), ("b", "c", 1, 5)], ArithmeticLog())
    assert graph.linear([("a", 1), ("c", -1)]) == 8
    with pytest.raises(AffineError, match="unknown amount"):
        graph.value("a")


def test_affine_graph_solves_inverse_edges_and_rejects_inconsistent_cycles():
    graph = AffineGraph([("a", 17)], [("a", "b", 2, 1)], ArithmeticLog())
    assert graph.value("b") == 8
    with pytest.raises(AffineError):
        AffineGraph([("a", 17), ("b", 9)], [("a", "b", 2, 1)], ArithmeticLog())
    with pytest.raises(AffineError):
        AffineGraph([], [("a", "b", 1, 1), ("b", "a", 1, 1)], ArithmeticLog())


def test_disconnected_comparisons_cannot_supply_a_difference():
    graph = AffineGraph([], [("a", "b", 1, 3), ("c", "d", 1, 3)], ArithmeticLog())
    with pytest.raises(AffineError):
        graph.linear([("a", 1), ("c", -1)])


@pytest.mark.parametrize("activity", ["working", "teaching"])
@pytest.mark.parametrize("direction,value", [("less", 21), ("more", 27)])
def test_relative_activity_experience(reg, activity, direction, value):
    number(
        reg,
        f"Nora spends 12 years {activity}. Her partner has been {activity} for 3 years {direction}. "
        "What is their combined time?",
        value,
    )


def test_relative_activity_cannot_borrow_an_unrelated_activity(reg):
    assert not solve(
        "Nora spends 12 years teaching. Her partner has been working for 3 years less. "
        "What is their combined time?",
        reg,
    ).answer.committed
    assert not solve(
        "Nora spends 2 years teaching. Her partner has been teaching for 3 years less. "
        "What is their combined time?",
        reg,
    ).answer.committed


@pytest.mark.parametrize(
    "text,value",
    [
        (
            "Nora is 3 months older than Iris. Iris is 4 months older than Theo. "
            "How much older in months is Nora than Theo?",
            7,
        ),
        (
            "Nora is 3 years older than Iris. Iris is 4 months older than Theo. "
            "How much older in months is Nora than Theo?",
            40,
        ),
        (
            "Nora is 3 months older than Iris. Iris is 4 months older than Theo. "
            "How much younger in months is Theo than Nora?",
            7,
        ),
    ],
)
def test_unanchored_age_differences(reg, text, value):
    number(reg, text, value)


@pytest.mark.parametrize(
    "text",
    [
        "Nora is 3 months older than Iris. Theo is 4 months older than Ava. How much older in months is Nora than Theo?",
        "Nora is 3 months older than Iris. Iris is 3 months older than Nora. How much older in months is Nora than Iris?",
        "Nora is 3 months older than Iris. How old is Nora?",
    ],
)
def test_age_difference_requires_connected_consistent_evidence(reg, text):
    assert not solve(text, reg).answer.committed


def indexed():
    return (
        "The contest was split into two rounds. "
        "Nora skipped 2 fewer times than Iris in the first round. "
        "Nora skipped 4 more times than Iris in the last round. "
        "If Iris skipped 10 times in each round, what is the average number of skips per round completed by Nora?"
    )


def test_scoped_round_comparisons_and_frequency(reg):
    number(reg, indexed(), 11)


@pytest.mark.parametrize(
    "old,new",
    [
        ("two rounds", "three rounds"),
        ("last round", "first round"),
        ("2 fewer", "20 fewer"),
        ("Iris in the last", "Ava in the last"),
        ("in each round", "in the first round"),
    ],
)
def test_indexed_comparison_boundaries(reg, old, new):
    assert not solve(indexed().replace(old, new), reg).answer.committed


def extra():
    return (
        "Nora purchased 20 boxes of books. "
        "Nora bought 2 additional boxes for every 3 boxes Iris bought. "
        "If Iris purchased 30 boxes of books, how many boxes of books did Nora bring home?"
    )


def test_additional_ratio_preserves_initial_purchase(reg):
    number(reg, extra(), 40)


@pytest.mark.parametrize(
    "old,new",
    [
        ("3 boxes Iris", "0 boxes Iris"),
        ("30 boxes of books", "30 boxes of hats"),
        ("additional boxes", "boxes"),
        ("30 boxes of books", "2 boxes of books"),
    ],
)
def test_incremental_purchase_boundaries(reg, old, new):
    assert not solve(extra().replace(old, new), reg).answer.committed


def pool():
    return (
        "Nora has 20 red books and 30 blue books. "
        "Her friend Iris has one-half times as many red books as she has and twice the number of blue books. "
        "If they combine all the books together and share them equally between themselves, "
        "calculate the number of books each gets."
    )


def test_qualified_stock_pool(reg):
    number(reg, pool(), 60)


@pytest.mark.parametrize(
    "old,new",
    [
        ("one-half times", "1/2 times"),
        ("Her friend Iris", "Her classmate Iris"),
    ],
)
def test_qualified_pool_paraphrases(reg, old, new):
    number(reg, pool().replace(old, new), 60)


def test_explicit_standard_and_multiplier_pool(reg):
    number(
        reg,
        pool().replace("Her friend Iris", "Iris").replace("as she has", "as Nora has"),
        60,
    )
    number(reg, pool().replace("one-half times", "twice"), 75)


def test_possessive_comparison_standard_requires_compatible_reference_forms(reg):
    assert not solve(pool().replace("as she has", "as he has"), reg).answer.committed


@pytest.mark.parametrize(
    "old,new",
    [
        ("blue books as", "green books as"),
        ("twice the number of blue", "twice the number of red"),
        ("30 blue books", "31 blue books"),
        ("books each gets", "hats each gets"),
        ("share them equally", "share them"),
    ],
)
def test_qualified_pool_scope_boundaries(reg, old, new):
    text = pool().replace(old, new)
    if text == pool():
        # The first comparison's item must still have an observed base.
        text = text.replace("as many red books", "as many green books")
    assert not solve(text, reg).answer.committed


def tariff():
    return (
        "Nora earns $300 if she works for 30 hours a week and gets an extra $18 for every hour of overtime. "
        "If she worked 40 hours last week, calculate her total income."
    )


@pytest.mark.parametrize("hours,value", [(30, 300), (40, 480), (45, 570)])
def test_fixed_block_and_excess_compensation(reg, hours, value):
    number(reg, tariff().replace("40 hours last", f"{hours} hours last"), value)


def test_contractor_block_quote_uses_the_same_tariff(reg):
    number(reg, tariff().replace("earns", "charges"), 480)


@pytest.mark.parametrize(
    "old,new",
    [
        ("40 hours last", "29 hours last"),
        ("30 hours a week", "30 hours a day"),
        ("$18", "£18"),
        ("she worked", "Iris worked"),
    ],
)
def test_fixed_block_boundaries(reg, old, new):
    assert not solve(tariff().replace(old, new), reg).answer.committed


def purchase():
    return (
        "Nora goes to the store to buy a soda. The soda costs $.50 an ounce. "
        "She brought $5 with her and leaves with $1. How many ounces of soda did she buy?"
    )


@pytest.mark.parametrize("old,new", [("$.50", "$0.50"), ("$.50", "$.50"), ("$", "£")])
def test_inverse_measured_purchase(reg, old, new):
    number(reg, purchase().replace(old, new), 8)


@pytest.mark.parametrize(
    "old,new",
    [
        ("$1.", "$6."),
        ("$.50", "$0"),
        ("ounces of soda", "feet of soda"),
        ("$1.", "£1."),
        ("leaves with", "gives Iris"),
    ],
)
def test_measured_purchase_boundaries(reg, old, new):
    assert not solve(purchase().replace(old, new), reg).answer.committed


def valuation():
    return (
        "Nora's box weighs 100 pounds. It increased its weight to 2 times its starting weight. "
        "She is able to sell the box for $4 per pound. How much more is it worth?"
    )


def test_measurement_based_asset_value(reg):
    number(reg, valuation(), 400)


def test_living_asset_uses_the_same_measurement_valuation(reg):
    number(reg, valuation().replace("box", "cow"), 400)


def test_decimal_without_leading_zero_has_generic_numeric_value(reg):
    from rulekit.kernel.numbers import annotate_numbers
    from rulekit.kernel.tokenize import tokenize

    reading = tokenize(".75 -.5 1,234.50")
    annotate_numbers(reading, reg)
    assert [u.features.get("value") for u in reading.units] == [0.75, -0.5, 1234.50]


def test_directed_age_comparison_does_not_accept_self_reference(reg):
    assert not solve(
        "Nora is 3 months older than Iris. How much older in months is Nora than Nora?",
        reg,
    ).answer.committed


@pytest.mark.parametrize(
    "old,new",
    [
        ("100 pounds.", "100 pounds. Iris has a cow."),
        ("the box for", "the cow for"),
        ("per pound", "per liter"),
        ("2 times", "half"),
    ],
)
def test_asset_reference_and_measure_boundaries(reg, old, new):
    assert not solve(valuation().replace(old, new), reg).answer.committed


@pytest.mark.parametrize("period", ["year", "month"])
def test_relative_adjacent_period_total(reg, period):
    number(
        reg,
        f"Nora sold 22 books last {period}. She sold three times that many the {period} before. "
        f"How many books has Nora sold in the last two {period}s?",
        88,
    )


@pytest.mark.parametrize(
    "old,new",
    [
        ("last two years", "last three years"),
        ("the year before", "the month before"),
        ("She sold", "Iris sold"),
    ],
)
def test_relative_period_boundaries(reg, old, new):
    text = (
        "Nora sold 22 books last year. She sold three times that many the year before. "
        "How many books has Nora sold in the last two years?"
    )
    assert not solve(text.replace(old, new), reg).answer.committed


def available():
    return (
        "Oren booked a room in a hotel. The hotel has 6 floors with 5 identical rooms on each floor. "
        "Because of rain, the last floor is unavailable for the guests. "
        "Considering there are no other guests, in how many different rooms could Oren be checked in?"
    )


def test_uniform_grouped_availability(reg):
    number(reg, available(), 25)


@pytest.mark.parametrize(
    "old,new",
    [
        ("no other guests", "3 other guests"),
        ("last floor", "tenth floor"),
        ("on each floor", "in total"),
    ],
)
def test_grouped_availability_boundaries(reg, old, new):
    assert not solve(available().replace(old, new), reg).answer.committed


def test_availability_does_not_invent_a_qualified_subset(reg):
    assert not solve(
        available().replace("different rooms", "red rooms"), reg
    ).answer.committed


@pytest.mark.parametrize(
    "excluded,copula,value", [("last row", "is", 32), ("2 rows", "are", 24)]
)
def test_grouped_availability_also_counts_seating(reg, excluded, copula, value):
    number(
        reg,
        f"The theater has 5 rows with 8 seats on each row. The {excluded} {copula} unavailable. "
        "There are no other customers. How many seats are available?",
        value,
    )


def test_partial_group_class_cannot_supply_all_capacity(reg):
    assert not solve(
        "The theater has 5 rows with 8 red seats on each row. The last row is unavailable. "
        "There are no other customers. How many seats are available?",
        reg,
    ).answer.committed


def test_indexed_comparisons_also_count_completed_laps(reg):
    number(
        reg,
        "The contest was split into two rounds. Nora completed 2 fewer laps than Iris in the first round. "
        "Nora completed 4 more laps than Iris in the last round. "
        "If Iris completed 10 laps in each round, what is the average number of laps per round completed by Nora?",
        11,
    )


def test_compatible_adjectives_keep_declared_noun_senses(reg):
    from rulekit.kernel.engine import analyze

    reading = analyze("Iris has as many red books as Nora.", reg)
    books = next(u for u in reading.units if u.features.get("qualifier") == "red")
    assert books.sense() == "noun"
    assert books.features["lemma"] == "book"
    assert books.features["number"] == "plural"
    booking = analyze("Nora books a room.", reg)
    predicate = next(u for u in booking.units if u.features.get("lemma") == "book")
    assert predicate.sense() == "verb"
    assert predicate.features["number"] == "singular"


def test_distributive_unit_quotes_reuse_purchase_accounting(reg):
    number(
        reg,
        "Nora buys 3 films, 2 books and 5 CDs. "
        "Each film cost $4, each book cost $6 and each CD cost $2. "
        "How much money did Nora spend?",
        34,
    )


def test_quantified_homographs_remain_nouns_in_comparisons(reg):
    number(
        reg,
        "Nora has 18 books. Iris has 6 fewer books than Nora. How many books does Iris have?",
        12,
    )
    number(
        reg,
        "Nora wrote five times as many books as Iris. If Nora wrote 30 books, "
        "how many books did they write altogether?",
        36,
    )


@pytest.mark.parametrize(
    "old,new", [("pounds", "liters"), ("after gaining", "after losing")]
)
def test_mass_valuation_requires_the_declared_dimension_and_direction(reg, old, new):
    text = valuation().replace("worth?", "worth after gaining the weight?")
    if old == "pounds":
        text = text.replace("per pound", "per liter")
    assert not solve(text.replace(old, new), reg).answer.committed


def test_affine_cycles_can_determine_an_origin_without_an_observed_value():
    graph = AffineGraph([], [("a", "b", 2, 0), ("b", "a", 1, -3)], ArithmeticLog())
    assert graph.value("a") == 6
    assert graph.value("b") == 3


def test_span_verb_refusals_follow_selected_senses_and_keep_unresolved_verbs_blocked(
    reg,
):
    from rulekit.data.schemas import MatchToken
    from rulekit.kernel.engine import analyze
    from rulekit.kernel.patterns import match_sequence
    from rulekit.kernel.senses import annotate_senses
    from rulekit.kernel.tokenize import tokenize

    pattern = [
        MatchToken(slot="phrase", span=True, span_blocks=["verb"], at_start=True)
    ]
    assert match_sequence(analyze("red books.", reg), pattern, reg) is not None
    assert (
        match_sequence(
            analyze("Nora books a room.", reg),
            [MatchToken(lit="nora", at_start=True), *pattern],
            reg,
        )
        is None
    )
    unresolved = tokenize("books")
    annotate_senses(unresolved, reg)
    assert match_sequence(unresolved, pattern, reg) is None


def test_adpositions_keep_nominal_objects_and_distinguish_infinitives(reg):
    from rulekit.kernel.engine import analyze

    nominal = analyze("Iris spent $9 on books.", reg)
    assert next(u for u in nominal.units if u.surface == "books").sense() == "noun"
    verbal = analyze("Iris wants to book a room.", reg)
    assert next(u for u in verbal.units if u.surface == "book").sense() == "verb"


@pytest.mark.parametrize("marker", ["combined", "total"])
def test_duration_totals_use_the_existing_prenominal_aggregate_category(reg, marker):
    number(
        reg,
        f"Nora spends 12 years working. Her partner has been working for 3 years less. "
        f"What is their {marker} time?",
        21,
    )


@pytest.mark.parametrize(
    "question",
    [
        "How many books did Nora sell over the last two months?",
        "How many books did Nora sell altogether?",
        "How many books has Nora sold in total?",
    ],
)
def test_adjacent_period_totals_support_explicit_windows_and_ordinary_aggregates(
    reg, question
):
    number(
        reg,
        "Nora sold 22 books last month. She sold three times that many the month before. "
        + question,
        88,
    )


def test_a_future_window_cannot_borrow_past_reporting_periods(reg):
    assert not solve(
        "Nora sold 22 books last month. She sold three times that many the month before. "
        "How many books has Nora sold in the next two months?",
        reg,
    ).answer.committed


def test_generator_uses_the_source_constructions_selected_lexical_sense(reg):
    from rulekit.generation.sample import _binding_key

    assert _binding_key("meeting", reg, "verb") == ("meet",)
    assert _binding_key("meeting", reg, "noun") == ("meeting",)


@pytest.mark.parametrize("amount,unit", [(40, "page"), (2, "pound")])
def test_a_declared_measured_modifier_keeps_its_holder_nominal(reg, amount, unit):
    from rulekit.kernel.engine import analyze

    reading = analyze(f"Nora has a {amount}-{unit} book.", reg)
    holder = next(u for u in reading.units if u.features.get("lemma") == "book")
    assert holder.sense() == "noun"
    assert holder.features["value_kind"] == "attributive_count"
    assert holder.features["qualifier"] == unit
    assert holder.features["value"] == amount


def test_an_unlicensed_measure_does_not_describe_a_holder(reg):
    from rulekit.kernel.engine import analyze

    reading = analyze("Nora has a 2-rabbit book.", reg)
    assert not any(
        u.features.get("value_kind") == "attributive_count" for u in reading.units
    )


@pytest.mark.parametrize("owner,value", [("hotel", 25), ("warehouse", None)])
def test_capacity_exclusions_preserve_their_site_owner(reg, owner, value):
    text = available().replace("the last floor", f"the {owner}'s last floor")
    if value is None:
        assert not solve(text, reg).answer.committed
    else:
        number(reg, text, value)


@pytest.mark.parametrize(
    "text,head,licensed",
    [
        ("for every book", "book", True),
        ("half of each costs $3", "costs", False),
        ("after all book a room", "book", False),
    ],
)
def test_quantifier_objects_do_not_swallow_possible_finite_predicates(
    reg, text, head, licensed
):
    from rulekit.kernel.tokenize import tokenize
    from rulekit.kernel.numbers import annotate_numbers
    from rulekit.kernel.senses import annotate_senses
    from rulekit.kernel.obligations import _adposition_licenses_noun

    reading = tokenize(text)
    annotate_numbers(reading, reg)
    annotate_senses(reading, reg)
    unit = next(u for u in reading.units if u.surface == head)
    assert _adposition_licenses_noun(reading, unit, reg) is licensed
