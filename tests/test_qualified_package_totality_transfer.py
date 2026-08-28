"""Qualified package contents and complete transfer into a container.

Synthetic only: the examples exercise the reusable grammar with invented
people, objects, and numbers rather than preserving a corpus/user specimen.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import (
    generate_candidate,
    list_ask_availability,
    list_rule_availability,
)
from rulekit.kernel.engine import analyze, solve
from rulekit.kernel.model import (
    ContainerCapacityInquiry,
    ContainerCapacityObservation,
    ContainerContent,
    Quantity,
    TotalityTransfer,
)


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/curated")).registry


def test_two_qualified_package_rates_transfer_the_complete_content(reg):
    result = solve(
        "Aven wants to know how many coins he can fit in a jar. "
        "He buys 4 large bags of coins, and 3 small bags of coins. "
        "A large bag has 25 coins, and a small bag has 10 coins. "
        "If he puts them all in the jar, how many coins does the jar contain?",
        reg,
        tracing=False,
    )

    assert result.answer.committed, result.answer.reason
    assert result.answer.value == 130.0
    assert result.deficiencies() == []
    assert any(
        fact.source == "aven"
        and fact.destination == "jar"
        for fact in result.store.by_kind(TotalityTransfer)
    )
    assert any(
        fact.container == "jar"
        and fact.content == "coin"
        and fact.operation == "transfer_all"
        for fact in result.store.by_kind(ContainerContent)
    )
    assert any(
        fact.provenance.source == "synth/container-totality-transfer"
        and fact.entity == "jar"
        and fact.measure == "coin"
        and fact.value == 130.0
        for fact in result.store.by_kind(Quantity)
    )


def test_definite_package_instance_is_not_a_per_package_rate(reg):
    result = solve(
        "Aven buys 4 large bags of coins. The large bag has 25 coins. "
        "If he puts them all in the jar, how many coins does the jar contain?",
        reg,
        tracing=False,
    )

    assert not result.answer.committed
    assert not any(
        fact.provenance.source == "synth/container-contents"
        and fact.entity == "aven"
        and fact.measure == "coin"
        for fact in result.store.by_kind(Quantity)
    )


def test_totality_transfer_declines_when_source_content_is_ambiguous(reg):
    result = solve(
        "Aven buys 2 large bags of coins and 3 small bags of pencils. "
        "A large bag has 20 coins, and a small bag has 8 pencils. "
        "If he puts them all in the jar, how many coins does the jar contain?",
        reg,
        tracing=False,
    )

    assert not result.answer.committed
    assert not any(
        fact.provenance.source == "synth/container-totality-transfer"
        for fact in result.store.by_kind(Quantity)
    )


def test_transfer_without_explicit_totality_does_not_move_the_collection(reg):
    result = solve(
        "Aven buys 2 large bags of coins. A large bag has 20 coins. "
        "He puts them in the jar. How many coins does the jar contain?",
        reg,
        tracing=False,
    )

    assert not result.answer.committed
    assert not list(result.store.by_kind(TotalityTransfer))


def test_content_state_ask_requires_a_declared_container(reg):
    result = solve(
        "Aven has 9 coins. How many coins does the teacher contain?",
        reg,
        tracing=False,
    )

    assert not result.answer.committed
    assert "no ask shape" in result.answer.reason


def test_transfer_and_content_ask_are_generation_supported(reg):
    project = load_project(Path("projects/curated"))
    premise = {
        item.id: item for item in list_rule_availability(project)
    }["arithmetic/container-totality-transfer"]
    ask = {
        item.id: item for item in list_ask_availability(project)
    }["ask/how-many-container-content-state"]

    assert premise.supported
    assert premise.generation == "contextual"
    assert ask.supported
    assert set(ask.supported_modes) == {
        "ask_only",
        "answerable",
        "validated_premises",
        "missing_evidence",
    }
    candidate = generate_candidate(
        project,
        rule_id="arithmetic/container-totality-transfer",
        seed=9151,
    )
    assert candidate.target_status == "matched"
    assert candidate.context_before
    assert candidate.to_json()["actual_rule_ids"] == [
        "arithmetic/container-totality-transfer"
    ]


def test_container_verbs_do_not_leak_into_broader_event_categories(reg):
    assert reg.word_in_category("contain", "state")
    assert not reg.word_in_category("contain", "possession_state")
    assert reg.word_in_category("put", "container_totality_transfer_verb")
    assert not reg.word_in_category("put", "acquire")


def test_inline_qualified_package_rates_compose_with_totality_transfer(reg):
    result = solve(
        "Bira is wondering how many coins she can fit in a jar. "
        "She buys 4 large bags with 25 coins, and 3 small bags of 10 coins. "
        "If she puts them all in the jar, how many coins does the jar contain?",
        reg,
        tracing=False,
    )

    assert result.answer.committed, result.answer.reason
    assert result.answer.value == 130.0
    assert result.deficiencies() == []
    assert any(
        fact.seeker == "bira"
        and fact.container == "jar"
        and fact.content == "coin"
        for fact in result.store.by_kind(ContainerCapacityInquiry)
    )
    package_counts = [
        fact
        for fact in result.store.by_kind(Quantity)
        if fact.entity == "bira" and fact.measure.split("[", 1)[0] == "bag"
    ]
    assert len(package_counts) == 2
    assert all(fact.provenance.container_count for fact in package_counts)


@pytest.mark.parametrize(
    ("transfer", "ask"),
    [
        (
            "she puts both bags of coins in the jar",
            "How many coins does the jar contain?",
        ),
        (
            "she puts the contents of both bags in the jar",
            "How many coins does the jar contain?",
        ),
        (
            "she puts the contents of both bags in the jar",
            "How many coins are in the jar?",
        ),
    ],
)
def test_two_explicit_package_group_transfer_paraphrases(reg, transfer, ask):
    result = solve(
        "Bira is wondering how many coins she can fit in a jar. "
        "She buys 4 large bags with 25 coins, and 3 small bags of 10 coins. "
        f"If {transfer}, {ask}",
        reg,
        tracing=False,
    )

    assert result.answer.committed, result.answer.reason
    assert result.answer.value == 130.0
    assert result.deficiencies() == []
    assert any(
        fact.package_class_count == 2
        for fact in result.store.by_kind(TotalityTransfer)
    )


def test_all_available_fit_supports_only_the_confirmed_amount_ask(reg):
    result = solve(
        "Bira is wondering how many coins she can fit in a jar. "
        "She buys 4 large bags with 25 coins, and 3 small bags of 10 coins. "
        "If all the coins fit, how many coins can we safely say will fit in the jar?",
        reg,
        tracing=False,
    )

    assert result.answer.committed, result.answer.reason
    assert result.answer.value == 130.0
    assert result.deficiencies() == []
    assert any(
        fact.mode == "all_available_fit"
        and fact.content == "coin"
        for fact in result.store.by_kind(ContainerCapacityObservation)
    )

    exact = solve(
        "Bira is wondering how many coins she can fit in a jar. "
        "She buys 4 large bags with 25 coins, and 3 small bags of 10 coins. "
        "If all the coins fit, how many coins can fit in the jar?",
        reg,
        tracing=False,
    )
    assert not exact.answer.committed
    assert "confirmed amount, not exact capacity" in exact.answer.reason


@pytest.mark.parametrize(
    "opener",
    [
        "Bira is wondering how many coins she can fit in a jar.",
        "Bira is checking to see how many coins can fit in a jar.",
        "Bira is checking to see how many coins can go into a jar.",
        "Bira is measuring the capacity of a jar.",
        "Bira is studying the capacity of a jar.",
    ],
)
def test_full_container_remainder_determines_exact_capacity(reg, opener):
    result = solve(
        f"{opener} "
        "Bira buys 4 large bags with 25 coins, and 3 small bags of 10 coins. "
        "If there are still 5 coins left after the jar is filled, "
        "how many coins can fit in the jar?",
        reg,
        tracing=False,
    )

    assert result.answer.committed, result.answer.reason
    assert result.answer.value == 125.0
    assert result.deficiencies() == []


def test_capacity_observation_boundaries_decline(reg):
    overlarge_remainder = solve(
        "Bira is measuring the capacity of a jar. "
        "Bira buys 2 large bags with 20 coins, and 2 small bags of 5 coins. "
        "If there are still 60 coins left after the jar is filled, "
        "how many coins can fit in the jar?",
        reg,
        tracing=False,
    )
    assert not overlarge_remainder.answer.committed
    assert "outside available total" in overlarge_remainder.answer.reason

    missing_context = solve(
        "Bira buys 2 large bags with 20 coins, and 2 small bags of 5 coins. "
        "If there are still 4 coins left after the jar is filled, "
        "how many coins can fit in the jar?",
        reg,
        tracing=False,
    )
    assert not missing_context.answer.committed
    assert "inquiry context; found 0" in missing_context.answer.reason

    malformed_path = solve(
        "Bira is checking to see how many coins can go into in a jar. "
        "Bira buys 2 large bags with 20 coins, and 2 small bags of 5 coins. "
        "If there are still 4 coins left after the jar is filled, "
        "how many coins can fit in the jar?",
        reg,
        tracing=False,
    )
    assert not malformed_path.answer.committed
    assert "inquiry context; found 0" in malformed_path.answer.reason


def test_both_package_groups_requires_exactly_two_qualified_classes(reg):
    result = solve(
        "Bira is wondering how many coins she can fit in a jar. "
        "She buys 4 large bags with 25 coins. "
        "If she puts both bags of coins in the jar, "
        "how many coins does the jar contain?",
        reg,
        tracing=False,
    )

    assert not result.answer.committed
    assert not any(
        fact.provenance.source == "synth/container-totality-transfer"
        for fact in result.store.by_kind(Quantity)
    )


def test_nominal_subject_disambiguates_modal_but_article_preserves_can_noun(reg):
    modal = analyze("Coins can fit in the jar.", reg, tracing=False)
    assert next(unit for unit in modal.units if unit.surface == "can").sense() == "modal"

    noun = analyze("The can fits in the jar.", reg, tracing=False)
    assert next(unit for unit in noun.units if unit.surface == "can").sense() == "noun"
