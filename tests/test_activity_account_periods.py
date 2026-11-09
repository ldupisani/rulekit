"""Invented reporting scopes for stock balances and completed-work counters."""

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import ActivityAccountEvidence
from rulekit.kernel.reference_identity import ReferenceIdentity
from rulekit.kernel.reporting_periods import reporting_period
from rulekit.kernel.rate_calculation import convert_exact_duration
from rulekit.kernel.evaluate import ArithmeticLog


@pytest.fixture(scope="module")
def reg():
    return load_project("projects/curated").registry


def progress(
    period="week",
    activity="inspect",
    past="inspected",
    item="parts",
    actor="Nora",
    subject="she",
    prior=None,
):
    prior = prior or f"last {period}"
    return (
        f"{actor} can {activity} 4 {item} per minute. "
        f"This {period}, {actor} continued working on a batch {subject} started {prior}. "
        f"{actor} {past} for 10 minutes. "
        f"In all, {actor} had {past} 70 {item} by the end of this {period}. "
        f"How many {item} had {actor} {past} at the beginning of this {period}?"
    )


def stock():
    return (
        "Nora can collect 6 shells per minute. This hour at the warehouse, "
        "Nora continued working on a collection she started the previous hour. "
        "Nora collected for 5 minutes. Nora removed 4 shells. "
        "In all, the collection had 50 shells by the end of this hour. "
        "How many shells did Nora start with this hour?"
    )


def number(reg, text, expected):
    result = solve(text, reg)
    assert result.value == pytest.approx(expected), result.answer
    assert not result.deficiencies()
    return result


@pytest.mark.parametrize("period", ["hour", "day", "week", "month", "year"])
def test_report_grain_does_not_supply_elapsed_work(reg, period):
    result = number(reg, progress(period), 30)
    context = next(
        r
        for r in result.store.by_kind(ActivityAccountEvidence)
        if r.kind == "activity-account-context"
    )
    assert context.reporting_period_ref.head == period
    assert context.prior_period_ref.qualifiers == ("last",)
    assert isinstance(context.position, int)


@pytest.mark.parametrize(
    "activity,past,item",
    [
        ("repair", "repaired", "bicycles"),
        ("clean", "cleaned", "rooms"),
        ("sort", "sorted", "cards"),
    ],
)
def test_completed_work_is_not_limited_to_content_creation(reg, activity, past, item):
    number(reg, progress(activity=activity, past=past, item=item), 30)


def test_nonliving_agent_and_observed_rate(reg):
    text = progress(actor="The machine", subject="it")
    number(reg, text.replace("can inspect", "inspects"), 30)


def test_initiating_activity_and_direct_continuation_share_the_account(reg):
    number(
        reg, progress().replace("started last week", "started inspecting last week"), 30
    )
    text = progress().replace(
        "This week, Nora continued working on a batch she started last week.",
        "Nora continued inspecting a batch this week.",
    )
    number(reg, text, 30)


def test_physical_collection_and_depletion_share_the_balance(reg):
    number(reg, stock(), 24)
    text = (
        stock().replace("can collect", "can consume").replace("collected", "consumed")
    )
    text = text.replace("shells", "batteries")
    number(reg, text, 84)


def test_explicit_scoped_interval_and_current_period_alias(reg):
    text = progress().replace("for 10 minutes.", "for 10 minutes this week.")
    number(reg, text.replace("this week?", "the current week?"), 30)
    number(
        reg,
        progress("day")
        .replace("This day", "Today")
        .replace("last day", "yesterday")
        .replace("this day", "today"),
        30,
    )


def test_calendar_rate_conversion_uses_exact_month_counts(reg):
    text = progress("year").replace("4 parts per minute", "12 parts per year")
    number(reg, text.replace("10 minutes", "6 months"), 64)


@pytest.mark.parametrize(
    "before,after",
    [
        ("last week", "yesterday"),
        ("last week", "next week"),
        ("end of this week", "end of last week"),
        ("beginning of this week", "beginning of this year"),
        ("Nora inspected for", "Leto inspected for"),
        ("Nora inspected for", "Nora repaired for"),
        ("70 parts", "70 cards"),
        ("10 minutes", "200 hours"),
        ("10 minutes", "0.1 minutes"),
        ("started last week", "started repairing last week"),
    ],
)
def test_inconsistent_or_unestablished_account_scope_declines(reg, before, after):
    assert not solve(progress().replace(before, after), reg).answer.committed


def test_a_report_period_cannot_stand_in_for_unknown_calendar_conversion(reg):
    text = progress("month").replace("per minute", "per month")
    assert not solve(text, reg).answer.committed


def test_explicit_activity_period_must_match_the_report(reg):
    text = progress().replace("for 10 minutes.", "for 10 minutes last week.")
    assert not solve(text, reg).answer.committed


def test_inspection_does_not_create_physical_stock(reg):
    text = (
        stock().replace("can collect", "can inspect").replace("collected", "inspected")
    )
    assert not solve(text, reg).answer.committed


def test_removing_stock_does_not_reverse_completed_work(reg):
    text = progress().replace("In all,", "Nora removed 4 parts. In all,")
    assert not solve(text, reg).answer.committed


@pytest.mark.parametrize(
    "activity,past,item",
    [("inspect", "inspected", "parts"), ("type", "typed", "words")],
)
def test_rate_subject_preserves_ordinal_identity(reg, activity, past, item):
    text = progress(
        actor="The first machine", subject="it", activity=activity, past=past, item=item
    )
    number(reg, text, 30)
    text = text.replace("The first machine can", "The second machine can")
    assert not solve(text, reg).answer.committed


@pytest.mark.parametrize(
    "before,after",
    [
        ("had Nora inspected", "have Nora inspected"),
        ("Nora inspected for", "Nora inspect for"),
        ("Nora had inspected 70", "Nora have inspected 70"),
    ],
)
def test_activity_accounts_require_subject_verb_agreement(reg, before, after):
    assert not solve(progress().replace(before, after), reg).answer.committed


def test_opening_stock_question_requires_subject_auxiliary_agreement(reg):
    assert not solve(
        stock().replace("did Nora start", "do Nora start"), reg
    ).answer.committed


def test_period_normalization_retains_scope_and_declines_compound_restrictions(reg):
    current = reporting_period(ReferenceIdentity("week"), reg)
    assert (
        reporting_period(ReferenceIdentity("week", qualifiers=("current",)), reg)
        == current
    )
    assert reporting_period(
        ReferenceIdentity("week", qualifiers=("previous",)), reg
    ).precedes(current)
    for ref in [
        ReferenceIdentity("week", owner="nora"),
        ReferenceIdentity("week", qualifiers=("previous", "current")),
        ReferenceIdentity("week", qualifiers=("busy",)),
        ReferenceIdentity("week", resolved=False),
    ]:
        assert reporting_period(ref, reg) is None
    log = ArithmeticLog()
    assert convert_exact_duration(2, "hour", "second", reg, log, source="test") == 7200
    assert convert_exact_duration(1, "month", "day", reg, log, source="test") is None
