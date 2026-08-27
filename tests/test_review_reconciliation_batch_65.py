"""Review batch 65: goal predicates do not become quantity events."""

import json
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.generation.reviews import review_path
from rulekit.kernel.engine import solve


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
REVIEWS = {
    "rev-6e3dae0e57034eef": (
        "arithmetic/fraction-as-many",
        "The university hopes eighth as many cookies in january as their guardian Fia.",
    ),
    "rev-ef4370cb6db04d0f": (
        "arithmetic/as-many",
        "The pantry saving as many friends with its remainder as the vessel.",
    ),
    "rev-080068877e2b490f": (
        "arithmetic/times-as-many-conjunct",
        "The teacher requires 2 universities in the university and thrice as many containers as the weight.",
    ),
}
CONJUNCT_RULE = "arithmetic/times-as-many-conjunct"


@pytest.fixture(scope="module")
def curated():
    return load_project(CURATED)


def _matched_rules(text: str, registry) -> set[str]:
    result = solve(text, registry)
    return {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


def test_latest_invalid_reviews_remain_in_the_append_only_ledger(curated) -> None:
    rows = {
        row["id"]: row
        for line in review_path(curated).read_text(encoding="utf-8").splitlines()
        if line.strip()
        for row in [json.loads(line)]
    }

    assert REVIEWS.keys() <= rows.keys()
    for review_id, (rule_id, sentence) in REVIEWS.items():
        assert rows[review_id]["verdict"] == "invalid"
        assert rows[review_id]["target_rule"] == rule_id
        assert rows[review_id]["sentence"] == sentence


@pytest.mark.parametrize("rule_id, sentence", tuple(REVIEWS.values()))
def test_goal_predicates_do_not_match_general_quantity_comparisons(
    curated, rule_id: str, sentence: str
) -> None:
    assert rule_id not in _matched_rules(sentence, curated.registry)


@pytest.mark.parametrize("surface", ("hopes", "saving", "requires"))
def test_goal_predicate_exclusion_is_inherited_category_data(
    curated, surface: str
) -> None:
    assert curated.registry.word_in_category(surface, "goal_predicate")
    assert curated.registry.word_in_category(
        surface, "non_quantity_object_verb"
    )


@pytest.mark.parametrize(
    "sentence",
    (
        "The teacher ate 2 cookies and thrice as many pencils as the student.",
        "The teacher has 2 universities and thrice as many containers as the student.",
        "The area has 2 universities and thrice as many containers as the weight.",
    ),
)
def test_conjunct_requires_compatible_consumption_themes_holders_and_standard(
    curated, sentence: str
) -> None:
    assert CONJUNCT_RULE not in _matched_rules(sentence, curated.registry)


@pytest.mark.parametrize(
    "sentence",
    (
        "The teacher ate 2 cookies and thrice as many apples as the student.",
        "The teacher has 2 students and thrice as many courses as the university.",
    ),
)
def test_compatible_conjunct_comparisons_remain_open(curated, sentence: str) -> None:
    assert CONJUNCT_RULE in _matched_rules(sentence, curated.registry)


def test_compatible_conjunct_still_generates_and_round_trips(curated) -> None:
    candidate = generate_candidate(
        curated,
        rule_id=CONJUNCT_RULE,
        seed=65,
        locked_bindings={
            "who": "the teacher",
            "verb": "has",
            "item1": "2 students",
            "k": "thrice",
            "item2": "courses",
            "std": "the university",
        },
    )

    assert candidate.sentence == (
        "The teacher has 2 students and thrice as many courses as the university."
    )
    assert candidate.target_status in {"matched", "shadowed"}
