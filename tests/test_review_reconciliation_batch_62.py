"""Malformed relation premises and ambiguous/location asks from review batch 62."""

import json
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.generation.reviews import review_path
from rulekit.generation.sample import GenerationError
from rulekit.kernel.engine import solve


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
REVIEW_IDS = {
    "rev-466cb53b8aa0415a",
    "rev-6c3e69d5d20a4789",
    "rev-7eaf126bfdc94435",
    "rev-b6c05c67a7c94ade",
    "rev-3ade0636ac5c449c",
    "rev-72bf66fc0942433c",
}


@pytest.fixture(scope="module")
def project():
    return load_project(CURATED)


def _matched_rules(text: str, registry) -> set[str]:
    result = solve(text, registry, tracing=False)
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


@pytest.mark.parametrize(
    "sentence",
    [
        "The dog placing 8 more buckets than their librarian Mary.",
        "The bird starts 10 fewer birds during august than the key.",
        "Dena hoping 20 fewer ages than their guardian Cato.",
        "Dena hopes 20 fewer ages than Cato.",
    ],
)
def test_anchored_relation_rejects_reviewed_grammar_and_role_errors(
    project, sentence: str
) -> None:
    assert "arithmetic/anchored-relation" not in _matched_rules(
        sentence, project.registry
    )


def test_anchored_relation_keeps_finite_and_role_compatible_comparisons(
    project,
) -> None:
    sentence = "The dog placed 8 more buckets than their librarian Mary."
    result = solve(sentence, project.registry, tracing=False)

    assert "arithmetic/anchored-relation" in _matched_rules(
        sentence, project.registry
    )
    assert result.document.gaps == []


def test_strict_generation_cannot_reproduce_nonfinite_review(project) -> None:
    with pytest.raises(GenerationError):
        generate_candidate(
            project,
            rule_id="arithmetic/anchored-relation",
            seed=1,
            locked_bindings={
                "who": "the dog",
                "verb": "placing",
                "n": "8",
                "dir": "more",
                "item": "buckets",
                "appos_det": "their",
                "appos_role": "librarian",
                "std": "Mary",
            },
        )


def test_elided_measure_sees_unresolved_relation_measure(project) -> None:
    result = solve(
        "Eron sold 3 eggs and twice as many teachers as the hamster. "
        "How many will Eron sell?",
        project.registry,
        tracing=False,
    )

    assert not result.answer.committed
    assert "holds 2 measures" in result.answer.reason


def test_possessed_place_requires_place_scoped_evidence(project) -> None:
    unsupported = solve(
        "Aven has 13 apples. "
        "How many apples were there in Aven's university?",
        project.registry,
        tracing=False,
    )
    supported = solve(
        "Aven's university has 13 apples. "
        "How many apples were there in Aven's university?",
        project.registry,
        tracing=False,
    )

    assert not unsupported.answer.committed
    assert supported.answer.value == 13.0
