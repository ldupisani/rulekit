"""Unit-recipient sales composed over an exact named-period list."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import (
    generate_ask_scenario,
    generate_candidate,
    list_ask_availability,
)
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantity
from rulekit.kernel.patterns import match_ask


CURATED = Path("projects/curated")
PREMISE_RULE = "arithmetic/recipient-count-transfer-proportional-periods"
DIRECT_RECIPIENT_RULE = (
    "arithmetic/recipient-counted-transfer-proportional-periods"
)
ASK_RULE = "ask/how-many-entity-event-period-total"


@pytest.fixture(scope="module")
def project():
    return load_project(CURATED)


@pytest.fixture(scope="module")
def registry(project):
    return project.registry


def _story(question: str | None = None) -> str:
    return (
        "Mira sold stickers to 32 of her students in March, and then she "
        "sold one fourth as many stickers in April. "
        + (
            question
            or "How many stickers did Mira sell altogether in March and April?"
        )
    )


def test_recipient_count_and_proportional_period_compose(registry) -> None:
    result = solve(_story(), registry)

    assert (result.answer.kind, result.answer.value) == ("number", 40.0)
    assert not result.deficiencies()
    events = sorted(
        (
            quantity.time,
            quantity.value,
            quantity.occurrence,
        )
        for quantity in result.store.by_kind(Quantity)
        if quantity.provenance.source == PREMISE_RULE
    )
    assert events == [("april", 8.0, 0), ("march", 32.0, 0)]


def test_direct_counted_recipient_and_proportional_period_compose(
    registry,
) -> None:
    result = solve(
        "Mira sold stickers to 32 students in March, and then she "
        "sold one fourth as many stickers in April. "
        "How many stickers did Mira sell altogether in March and April?",
        registry,
    )

    assert (result.answer.kind, result.answer.value) == ("number", 40.0)
    assert not result.deficiencies()
    assert {
        (quantity.time, quantity.value)
        for quantity in result.store.by_kind(Quantity)
        if quantity.provenance.source == DIRECT_RECIPIENT_RULE
    } == {("march", 32.0), ("april", 8.0)}


def test_unit_recipient_transfer_is_an_opt_in_transfer_subcategory(
    registry,
) -> None:
    assert registry.category_parents["unit_recipient_transfer_verb"] == "transfer_out"
    assert registry.word_in_category("sold", "unit_recipient_transfer_verb")
    assert registry.word_in_category("gave", "transfer_out")
    assert not registry.word_in_category(
        "gave",
        "unit_recipient_transfer_verb",
    )
    frames = dict(registry.selectional_frames("sold"))
    assert frames["unit_recipient_transfer_verb"] == {
        "actor": "quantity_event_participant",
        "theme": "transferable_quantity_object",
        "recipient": "animate",
    }


def test_exact_period_ask_excludes_an_unlisted_month(registry) -> None:
    result = solve(
        "Mira sold stickers to 32 of her students in March, and then she "
        "sold one fourth as many stickers in April. "
        "Mira sold 7 stickers in June. "
        "How many stickers did Mira sell altogether in March and April?",
        registry,
    )

    assert (result.answer.kind, result.answer.value) == ("number", 40.0)


def test_exact_period_ask_includes_every_event_inside_a_listed_month(
    registry,
) -> None:
    result = solve(
        "Mira sold stickers to 32 of her students in March, and then she "
        "sold one fourth as many stickers in April. "
        "Mira sold 7 stickers in March. "
        "How many stickers did Mira sell altogether in March and April?",
        registry,
    )

    assert (result.answer.kind, result.answer.value) == ("number", 47.0)


def test_exact_period_ask_requires_evidence_for_every_named_period(
    registry,
) -> None:
    result = solve(
        "Mira sold 32 stickers in March. "
        "How many stickers did Mira sell altogether in March and April?",
        registry,
    )

    assert not result.answer.committed
    assert "april" in result.answer.reason


@pytest.mark.parametrize(
    "text",
    [
        (
            "Mira gave stickers to 32 of her students in March, and then she "
            "gave one fourth as many stickers in April. "
            "How many stickers did Mira give altogether in March and April?"
        ),
        (
            "Mira sold stickers to 32 of her students in March, and then she "
            "sold one fourth as many cards in April. "
            "How many stickers did Mira sell altogether in March and April?"
        ),
        (
            "Mira sold stickers to 32 of her students in March, and then she "
            "sold one fourth as many stickers in March. "
            "How many stickers did Mira sell altogether in March and April?"
        ),
        (
            "Mira sold stickers to 32 books in March, and then she "
            "sold one fourth as many stickers in April. "
            "How many stickers did Mira sell altogether in March and April?"
        ),
        (
            "Mira gave stickers to 32 students in March, and then she "
            "gave one fourth as many stickers in April. "
            "How many stickers did Mira give altogether in March and April?"
        ),
    ],
)
def test_incomplete_or_mismatched_constructions_do_not_invent_sales(
    registry, text
) -> None:
    result = solve(text, registry)

    assert not result.answer.committed
    assert not any(
        quantity.provenance.source == PREMISE_RULE
        for quantity in result.store.by_kind(Quantity)
    )


def test_period_pair_ask_preserves_both_explicit_periods(registry) -> None:
    result = solve(_story(), registry)
    matched = match_ask(result.question, registry)

    assert matched is not None
    assert matched[0].id == ASK_RULE
    assert matched[1]["periods"] == ["march", "april"]


def test_may_keeps_its_modal_and_calendar_uses(registry) -> None:
    result = solve(
        "Mira sold stickers to 20 of her students in April, and then she "
        "sold half as many stickers in May. "
        "How many stickers did Mira sell altogether in April and May?",
        registry,
    )

    assert (result.answer.kind, result.answer.value) == ("number", 30.0)
    assert registry.word_in_category("may", "named_month")
    assert registry.word_in_category("may", "capacity_modal")


def test_new_premise_and_ask_are_generator_reachable(project) -> None:
    premise = generate_candidate(project, rule_id=PREMISE_RULE, seed=23)
    direct = generate_candidate(
        project,
        rule_id=DIRECT_RECIPIENT_RULE,
        seed=29,
    )
    ask = generate_ask_scenario(project, ask_id=ASK_RULE, seed=23)
    availability = {
        item.id: item for item in list_ask_availability(project)
    }

    assert premise.target_status == "matched"
    assert premise.target_rule == PREMISE_RULE
    assert direct.target_status == "matched"
    assert direct.target_rule == DIRECT_RECIPIENT_RULE
    assert ask.target_ask == ASK_RULE
    assert availability[ASK_RULE].supported
