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
from rulekit.kernel.engine import solve
from rulekit.kernel.model import ContainerContent, Quantity, TotalityTransfer


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
