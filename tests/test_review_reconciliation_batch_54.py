"""Answerable-ask review reconciliation: relevant, cardinal evidence."""

import json
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_ask_scenario
from rulekit.generation.reviews import review_path
from rulekit.kernel.engine import analyze, solve
from rulekit.kernel.model import Quantity
from rulekit.kernel.patterns import match_ask


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
REVIEW_IDS = {
    "rev-3d58464777da4c67",
    "rev-ec0e2fdaf72c4718",
    "rev-d4a74105e8cd49b0",
    "rev-5a488c11253e405f",
}


@pytest.fixture(scope="module")
def project():
    return load_project(CURATED)


def _ask_id(question: str, registry) -> str | None:
    matched = match_ask(analyze(question, registry), registry)
    return None if matched is None else matched[0].id


def _matched_rules(text: str, registry) -> set[str]:
    result = solve(text, registry)
    return {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


def test_review_evidence_remains_in_the_append_only_ledger(project) -> None:
    history = {
        row["id"]: row
        for line in review_path(project).read_text(encoding="utf-8").splitlines()
        if line.strip()
        for row in [json.loads(line)]
    }

    assert REVIEW_IDS <= history.keys()
    assert all(history[review_id]["review_kind"] == "ask" for review_id in REVIEW_IDS)
    assert all(history[review_id]["verdict"] == "invalid" for review_id in REVIEW_IDS)


def test_partitive_membership_ask_requires_membership_grammar(project) -> None:
    assert _ask_id("How many of hours had shopper?", project.registry) is None


def test_collective_all_of_ask_requires_a_plural_object_pronoun(project) -> None:
    assert _ask_id(
        "How many eggs does all of him leave total?", project.registry
    ) is None
    assert _ask_id(
        "How many eggs do all of them have total?", project.registry
    ) == "ask/how-many-all-combined"

    answer = solve(
        "Aven has 3 eggs. Bira has 5 eggs. "
        "How many eggs do all of them have total?",
        project.registry,
    ).answer
    assert answer.committed
    assert answer.value == 8


def test_reviewed_comparative_premises_fail_their_role_boundaries(project) -> None:
    percentage = (
        "Mary wins 11 fewer percentages than trees and currently has 14 trees."
    )
    started = (
        "Violinist started 0 fewer apricots and 9 fewer rabbits than book."
    )

    assert "arithmetic/anchored-relation-conjoined-anchor" not in _matched_rules(
        percentage, project.registry
    )
    assert "arithmetic/anchored-relation-conjoined-measures" not in _matched_rules(
        started, project.registry
    )


def test_relation_saturation_does_not_restate_its_existing_anchor(project) -> None:
    result = solve(
        "Cato has 2 fewer apples than trees and currently has 14 trees. "
        "What is the number of Cato's trees?",
        project.registry,
    )
    tree_facts = [
        fact
        for fact in result.store.by_kind(Quantity)
        if fact.entity == "cato" and fact.measure == "tree"
    ]

    assert result.answer.committed
    assert result.answer.value == 14
    assert [(fact.value, fact.verb) for fact in tree_facts] == [(14, "have")]


def test_relation_saturation_never_materializes_a_negative_count(project) -> None:
    result = solve(
        "The book has 20 fewer rabbits than apples and had 13 apples. "
        "How many rabbits in all?",
        project.registry,
    )

    assert not result.answer.committed
    assert not any(
        fact.measure == "rabbit" and fact.value < 0
        for fact in result.store.by_kind(Quantity)
    )


def test_reviewed_answerable_seed_now_uses_direct_relevant_evidence(project) -> None:
    candidate = generate_ask_scenario(
        project,
        seed=4716671778855412,
        scenario_mode="answerable",
    )

    assert candidate.target_ask == "ask/what-average-combined"
    item = candidate.requested_bindings["item"]
    measure = candidate.query["measure"]
    assert item not in {"amounts", "numbers"}
    assert candidate.question == f"What is the average amount of {item}?"
    assert candidate.answer["committed"] is True
    assert candidate.answer["value"] == 0.5
    assert [premise["sentence"] for premise in candidate.premises] == [
        f"Total of 1 {measure}.",
        f"John had triple Eron's {item}.",
    ]
