"""Invented clause, source, holder, quota and scoped schedule paraphrases."""

from pathlib import Path
import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/curated")).registry


def amount(reg, text, value):
    result = solve(text, reg)
    assert result.answer.committed, result.answer
    assert result.value == pytest.approx(value)
    assert not result.deficiencies()
    return result


def schedule():
    return (
        "Nora's three students study writing in different classes. "
        "They each have 2 lessons this month. Each class practices 12 minutes for every lesson they study. "
        "Each lesson lasts 3 minutes. How many minutes will Nora spend watching her students study and practice altogether?"
    )


@pytest.mark.parametrize(
    "edit", ["ordinary", "in-total", "fused", "conjoined", "conditional"]
)
def test_complete_schedule_clauses_and_total_phrases(reg, edit):
    text = schedule()
    if edit == "in-total":
        text = text.replace("altogether?", "in total?")
    if edit == "fused":
        text = text.replace("minutes. How many", "minutes, how many")
    if edit == "conjoined":
        text = text.replace("study. Each lesson", "study, and each lesson").replace(
            "minutes. How many", "minutes, how many"
        )
    if edit == "conditional":
        text = text.replace(
            "Each lesson lasts 3 minutes. How", "If each lesson lasts 3 minutes, how"
        )
    amount(reg, text, 90)


@pytest.mark.parametrize(
    "edit",
    ["extra-clause", "incomplete", "embedded", "mismatched-total", "disjunction"],
)
def test_clause_recovery_needs_complete_independent_evidence(reg, edit):
    text = schedule()
    if edit == "extra-clause":
        text = text.replace(
            "Each lesson lasts", "The classes overlap. Each lesson lasts"
        )
    if edit == "incomplete":
        text = text.replace("Each lesson lasts 3 minutes.", "And 3 minutes.")
    if edit == "embedded":
        text = text.replace(
            "Each lesson lasts", "Nora wonders whether each lesson lasts"
        )
    if edit == "mismatched-total":
        text = text.replace("altogether?", "in combined?")
    if edit == "disjunction":
        text = text.replace("study. Each lesson", "study, or each lesson")
    assert not solve(text, reg).answer.committed


def test_independent_clause_permission_requires_a_fact_reader():
    from pydantic import ValidationError
    from rulekit.data.schemas import PatternRule

    with pytest.raises(ValidationError, match="independent_clause"):
        PatternRule(
            id="test/unlicensed-boundary",
            match={"sentence": []},
            independent_clause=True,
        )


def test_qualified_enumeration_requires_a_declared_member_category():
    from pydantic import ValidationError
    from rulekit.data.schemas import MatchToken

    with pytest.raises(ValidationError, match="enumeration_qualified"):
        MatchToken(slot="members", span=True, enumeration_qualified=True)


def sources():
    return (
        "A fox gained 240 pounds eating apples, small woodland birds, nuts and chicken. "
        "It gained a quarter of the weight from apples, and it gained twice that amount from nuts. "
        "Chicken made up half of the remaining weight it gained. How many pounds did it gain eating small birds?"
    )


@pytest.mark.parametrize(
    "edit", ["ordinary", "oxford", "nominal", "possessive", "separate", "units"]
)
def test_observed_source_totals_reuse_qualified_list_and_remainder_accounts(reg, edit):
    text = sources()
    if edit == "oxford":
        text = text.replace("nuts and chicken", "nuts, and chicken")
    if edit in ("nominal", "possessive"):
        text = text.replace("weight it gained", "weight gain")
    if edit == "possessive":
        text = text.replace(
            "How many pounds did it gain eating small birds?",
            "How much of its weight gain came from small birds?",
        )
    if edit == "separate":
        text = text.replace(", and it gained", ". It gained")
    if edit == "units":
        text = text.replace("pounds", "kilograms")
    result = amount(reg, text, 30)
    if edit == "ordinary":
        inventories = [
            f for f in result.facts() if getattr(f, "kind", "") == "contribution-source"
        ]
        bird = next(f for f in inventories if f.container == "bird")
        assert bird.container_ref.qualifiers == ("small", "woodland")


def test_observed_funding_sources_share_the_measured_outcome_adapter(reg):
    text = (
        "Nora earned $240. Nora received grants and donations. Nora received fees and sales. "
        "She earned a quarter of the money from grants, and she earned twice that amount from fees. "
        "Sales made up half of the remaining money she earned. How many dollars did Nora earn from donations?"
    )
    amount(reg, text, 30)
    amount(
        reg,
        text.replace(
            "How many dollars did Nora earn from donations?",
            "How much of her money came from donations?",
        ),
        30,
    )


@pytest.mark.parametrize(
    "edit",
    [
        "extra-source",
        "different-kind",
        "dimension",
        "unknown-descriptor",
        "typo",
        "negative",
    ],
)
def test_source_lists_preserve_partition_dimension_and_grammar_boundaries(reg, edit):
    text = sources()
    if edit == "extra-source":
        text = text.replace("nuts and chicken", "nuts, chicken and berries")
    if edit == "different-kind":
        text = text.replace("eating small birds?", "eating large birds?")
    if edit == "dimension":
        text = text.replace("weight it gained", "volume gain")
    if edit == "unknown-descriptor":
        text = text.replace("weight it gained", "red weight gain")
    if edit == "typo":
        text = text.replace(
            "How many pounds did it gain eating small birds?",
            "How much of it's weight gain came from small birds?",
        )
    if edit == "negative":
        text = text.replace("240 pounds", "-240 pounds")
    result = solve(text, reg)
    assert not result.answer.committed
    if edit == "typo":
        assert result.deficiencies()


def holders():
    return (
        "There are 7 kilograms of bean soup in 18 cans. If 8 of the cans are holding 250 grams each, "
        "how much bean soup is each of the remaining cans holding on average?"
    )


@pytest.mark.parametrize(
    "edit",
    [
        "ordinary",
        "equal sized",
        "equally sized",
        "equal-sized",
        "equally-sized",
        "unequal",
        "granular",
    ],
)
def test_measured_holder_averages_do_not_depend_on_capacity_equality(reg, edit):
    text = holders()
    if edit in ("equal sized", "equally sized", "equal-sized", "equally-sized"):
        text = text.replace("18 cans", f"18 {edit} cans")
    if edit == "unequal":
        text = text.replace("18 cans", "18 cans of unequal size")
    if edit == "granular":
        text = text.replace("bean soup", "corn").replace("cans", "baskets")
    amount(reg, text, 0.5)


def test_unequal_capacity_does_not_determine_individual_fill(reg):
    result = solve(
        holders()
        .replace("18 cans", "18 cans of unequal size")
        .replace(" on average", ""),
        reg,
    )
    assert not result.answer.committed
    assert "distributed" in result.answer.reason
    assert "capacity" in result.answer.reason


def test_a_zero_residual_is_zero_for_every_remaining_holder(reg):
    text = (
        holders()
        .replace("7 kilograms", "2 kilograms")
        .replace("18 cans", "18 cans of unequal size")
    )
    amount(reg, text, 0)
    amount(reg, text.replace(" on average", ""), 0)


@pytest.mark.parametrize(
    "before,after",
    [
        ("7 kilograms", "1 kilogram"),
        ("bean soup is", "tomato soup is"),
        ("250 grams", "250 meters"),
    ],
)
def test_holder_average_still_checks_stock_identity_and_dimensions(reg, before, after):
    assert not solve(holders().replace(before, after), reg).answer.committed


def goal():
    return (
        "Nora's workout goal is 20 pushups. On Monday, Nora did 7 pushups, and 9 pushups on Tuesday. "
        "How many pushups would Nora have to do on Wednesday to meet her goal?"
    )


@pytest.mark.parametrize(
    "edit,value",
    [("daily", 44), ("minimum", 44), ("weekly", 4), ("already-met", 0), ("pages", 44)],
)
def test_daily_make_up_and_whole_cycle_goals_remain_distinct(reg, edit, value):
    text = goal()
    if edit == "minimum":
        text = text.replace("her goal?", "her minimum goal?")
    if edit in ("weekly", "already-met"):
        text = text.replace("workout goal", "weekly workout goal")
    if edit == "already-met":
        text = text.replace("9 pushups", "19 pushups")
    if edit == "pages":
        text = text.replace("workout goal", "project goal").replace("pushups", "pages")
    amount(reg, text, value)


@pytest.mark.parametrize("edit", ["named-day", "no-day", "pages"])
def test_cumulative_progress_reduces_one_cycle_quota(reg, edit):
    text = (
        "Nora's weekly goal is 40 tasks. She did 28 tasks by Tuesday. "
        "How many tasks would Nora have to do on Wednesday to meet her goal?"
    )
    if edit == "no-day":
        text = text.replace("would Nora", "does she").replace(" on Wednesday", "")
    if edit == "pages":
        text = text.replace("tasks", "pages")
    amount(reg, text, 12)


@pytest.mark.parametrize(
    "edit", ["cumulative-daily", "conflict", "future", "different-unit", "overlap"]
)
def test_goal_scope_and_progress_cannot_be_inferred_from_incompatible_histories(
    reg, edit
):
    text = "Nora's weekly goal is 40 tasks. She did 28 tasks by Tuesday. How many tasks would Nora have to do on Wednesday to meet her goal?"
    if edit == "cumulative-daily":
        text = text.replace("weekly", "daily")
    if edit == "conflict":
        text = text.replace("40 tasks.", "40 tasks per day.")
    if edit == "future":
        text = text.replace("by Tuesday", "by Thursday")
    if edit == "different-unit":
        text = text.replace("28 tasks", "28 pages")
    if edit == "overlap":
        text = text.replace(
            "She did 28 tasks", "On Monday, Nora did 4 tasks. She did 28 tasks"
        )
    assert not solve(text, reg).answer.committed


def earnings():
    return (
        "Nora earns $12 an hour at her main job. She earns 25% less for her second job. "
        "She works 40 hours at her main job, and half that amount at her second job per week. "
        "How much does she earn per week?"
    )


@pytest.mark.parametrize(
    "edit",
    ["ordinary", "with", "on", "as-much", "that-much", "both-periods", "first-period"],
)
def test_scoped_extents_and_relative_reference_forms_keep_reporting_cadence(reg, edit):
    text = earnings()
    if edit in ("with", "on"):
        text = text.replace("for her second job", f"{edit} her second job")
    if edit == "as-much":
        text = text.replace("that amount", "as much")
    if edit == "that-much":
        text = text.replace("that amount", "that much")
    if edit == "both-periods":
        text = text.replace("main job, and", "main job per week, and")
    if edit == "first-period":
        text = text.replace("main job, and", "main job per week, and").replace(
            "second job per week.", "second job."
        )
    amount(reg, text, 660)


@pytest.mark.parametrize(
    "edit,value",
    [("conditional", 3960), ("explicit", 3960), ("fortnight", 1320), ("zero", 0)],
)
def test_reporting_rate_accounts_project_over_one_stated_span(reg, edit, value):
    text = earnings().replace(
        "How much does she earn per week?",
        "If she worked for 6 weeks, how much would she earn?",
    )
    if edit == "explicit":
        text = text.replace(
            "If she worked for 6 weeks, how much would she earn?",
            "How much would she earn over 6 weeks?",
        )
    if edit == "fortnight":
        text = text.replace("6 weeks", "14 days")
    if edit == "zero":
        text = text.replace("6 weeks", "0 weeks")
    amount(reg, text, value)


@pytest.mark.parametrize(
    "edit",
    [
        "cadence-conflict",
        "unknown-cadence",
        "wrong-owner",
        "ambiguous-standard",
        "units",
    ],
)
def test_rate_projection_keeps_scope_reporting_and_operand_boundaries(reg, edit):
    text = earnings().replace(
        "How much does she earn per week?",
        "If she worked for 6 weeks, how much would she earn?",
    )
    if edit == "cadence-conflict":
        text = text.replace("main job, and", "main job per month, and")
    if edit == "unknown-cadence":
        text = text.replace(" per week.", ".")
    if edit == "wrong-owner":
        text = text.replace("If she worked", "If Ezra worked")
    if edit == "ambiguous-standard":
        text = text.replace(
            "She earns 25%", "Nora earns $8 an hour at her third job. She earns 25%"
        )
    if edit == "units":
        text = text.replace("6 weeks", "6 meters")
    assert not solve(text, reg).answer.committed
