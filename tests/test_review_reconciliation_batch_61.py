"""Noun-membership, task-completion, and percentage-ask reviews."""

import json
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_ask_scenario, generate_candidate
from rulekit.generation.reviews import review_path
from rulekit.kernel.engine import analyze, solve
from rulekit.kernel.patterns import match_ask


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
REVIEW_IDS = {
    "rev-0f83a7bcd87a4a3f",
    "rev-a6b79e9450b64e3d",
}


@pytest.fixture(scope="module")
def project():
    return load_project(CURATED)


def _matched_rules(text: str, registry) -> set[str]:
    result = solve(text, registry)
    return {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


def _ask_id(question: str, registry) -> str | None:
    matched = match_ask(analyze(question, registry), registry)
    return None if matched is None else matched[0].id


def test_review_evidence_remains_in_the_append_only_ledger(project) -> None:
    history = {
        row["id"]: row
        for line in review_path(project).read_text(encoding="utf-8").splitlines()
        if line.strip()
        for row in [json.loads(line)]
    }

    assert REVIEW_IDS <= history.keys()
    assert all(
        history[review_id]["verdict"] == "invalid"
        for review_id in REVIEW_IDS
    )


def test_noun_membership_requires_directional_category_containment(project) -> None:
    rule_id = "arithmetic/partition-membership-of-noun"

    assert rule_id in _matched_rules(
        "9 of the animals are dogs.", project.registry
    )
    assert rule_id not in _matched_rules(
        "9 of the students are courses.", project.registry
    )
    assert rule_id not in _matched_rules(
        "9 of the dogs are animals.", project.registry
    )

    for seed in range(8):
        candidate = generate_candidate(project, rule_id=rule_id, seed=seed)
        assert candidate.target_status == "matched"
        assert project.registry.category_term_contains(
            candidate.target_bindings["coll"], candidate.target_bindings["attr"]
        )


def test_task_completion_uses_verb_owned_actor_and_theme_roles(project) -> None:
    invalid = (
        "The amount took 60 years to finish the inch while the bottle took "
        "50 years to finish it."
    )
    valid = (
        "Aven took 2 hours to finish the task while Bira took 3 hours to "
        "finish it."
    )

    assert (
        "arithmetic/coordinated-task-completion-durations"
        not in _matched_rules(invalid, project.registry)
    )
    assert "arithmetic/task-completion-duration" not in _matched_rules(
        invalid, project.registry
    )
    assert (
        "arithmetic/coordinated-task-completion-durations"
        in _matched_rules(valid, project.registry)
    )

    candidate = generate_candidate(
        project,
        rule_id="arithmetic/coordinated-task-completion-durations",
        seed=25,
    )
    assert candidate.target_status == "matched"
    assert project.registry.word_in_category(
        candidate.target_bindings["task_a"], "finishable_quantity_object"
    )


def test_sequential_percentage_ask_names_a_qualified_plural_destination(
    project,
) -> None:
    ask_id = "ask/what-percentage-sequential-partition"

    assert _ask_id(
        "What percentage of the students enroll in course?", project.registry
    ) is None
    assert _ask_id(
        "What percentage of the students enroll in science courses?",
        project.registry,
    ) == ask_id

    candidate = generate_ask_scenario(
        project,
        ask_id=ask_id,
        seed=16956212447197,
        scenario_mode="answerable",
        max_search_attempts=128,
    )

    assert candidate.answer["committed"] is True
    assert candidate.query["attribute"] in {
        "business course",
        "humanities course",
        "science course",
    }
    assert candidate.question.endswith("courses?")
    # Vocabulary growth can change the seeded search's first viable scaffold.
    # Complete, initial-share and remaining-share scaffolds can all answer
    # the named partition; retain the semantic contract rather than one
    # historical search result.
    assert len(candidate.premises) == 1
    assert candidate.premises[0]["target_rule"] in {
        "arithmetic/sequential-percent-remainder-partition",
        "arithmetic/sequential-percent-remainder-partition-initial-share",
        "arithmetic/sequential-percent-remainder-partition-remaining-share",
    }
