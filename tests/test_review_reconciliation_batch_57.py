"""Review-led boundaries for premise batch 57.

The batch exposed agreement, semantic-role, complement-number, possessive,
calendar-coordinate, and review-evidence boundaries.  Tests use invented
positive neighbours as well as the reviewed negative surfaces.
"""

import json
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.generation.reviews import review_path
from rulekit.kernel.engine import solve


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
INVALID_REVIEW_IDS = {
    "rev-a36f6cbde61944e1",
    "rev-a19f6940fa444336",
    "rev-c7f5ad33d0ea4506",
    "rev-39ee2409cf024ee8",
    "rev-469a1c5db0464b4a",
    "rev-99f67b60be1d453d",
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


def test_review_rows_remain_in_the_append_only_ledger(project) -> None:
    rows = {
        row["id"]: row
        for line in review_path(project).read_text(encoding="utf-8").splitlines()
        if line.strip()
        for row in [json.loads(line)]
    }

    assert INVALID_REVIEW_IDS <= rows.keys()
    assert all(rows[review_id]["verdict"] == "invalid" for review_id in INVALID_REVIEW_IDS)


@pytest.mark.parametrize(
    ("text", "rule_id"),
    (
        (
            "The garden traveled three ninths as many drums in october.",
            "arithmetic/fraction-as-many-elided-standard",
        ),
        (
            "The shopper began thrice as many as the area.",
            "arithmetic/times-as-many-elided",
        ),
        (
            "Total thursday won 15 violinists.",
            "arithmetic/group-total-leading-marker",
        ),
        (
            "The bench had 7 less amounts at my university than ages and was 2 ages.",
            "arithmetic/anchored-relation-conjoined-anchor",
        ),
        (
            "The librarian is 2 years old in 10.",
            "arithmetic/stated-age-at-year",
        ),
        (
            "Aven sell Fia 14 populations.",
            "arithmetic/transfer-ditransitive",
        ),
    ),
)
def test_reviewed_invalid_premises_no_longer_match(
    project, text: str, rule_id: str
) -> None:
    assert rule_id not in _matched_rules(text, project.registry)


@pytest.mark.parametrize(
    ("text", "rule_id"),
    (
        (
            "The student gave five sixths as many trees in the garden.",
            "arithmetic/fraction-as-many-elided-standard",
        ),
        (
            "The shopper began thrice as many as Dena.",
            "arithmetic/times-as-many-elided",
        ),
        (
            "Combined the book had 3 hamsters.",
            "arithmetic/group-total-leading-marker",
        ),
        (
            "Together they sold 12 coins.",
            "arithmetic/group-total-leading-marker",
        ),
        (
            "Total blue has 40 birds.",
            "arithmetic/group-total-leading-marker",
        ),
        (
            "Fia has 17 fewer birds than cats and currently has 4 cats.",
            "arithmetic/anchored-relation-conjoined-anchor",
        ),
        (
            "The librarian was 2 years old in 1999.",
            "arithmetic/stated-age-at-year",
        ),
        (
            "Aven sold Fia 14 apples.",
            "arithmetic/transfer-ditransitive",
        ),
        (
            "Aven sold 14 apples to Fia.",
            "arithmetic/transfer-prepositional",
        ),
    ),
)
def test_general_boundaries_keep_grammatical_positive_neighbours(
    project, text: str, rule_id: str
) -> None:
    assert rule_id in _matched_rules(text, project.registry)


def test_past_verbs_are_number_neutral_but_present_forms_still_agree(project) -> None:
    assert "arithmetic/group-total-leading-marker" in _matched_rules(
        "Together they sold 12 coins.", project.registry
    )
    assert "arithmetic/group-total-leading-marker" not in _matched_rules(
        "Together they sells 12 coins.", project.registry
    )


def test_sequential_partition_requires_plural_bare_course_destinations(project) -> None:
    bad = (
        "In a university with 5 students four eighths enroll in science course "
        "six sevenths of the remaining enroll in humanities courses and the "
        "rest enroll in business course."
    )
    good = bad.replace("science course ", "science courses ").replace(
        "business course.", "business courses."
    )

    rule_id = "arithmetic/sequential-percent-remainder-partition"
    assert rule_id not in _matched_rules(bad, project.registry)
    assert rule_id in _matched_rules(good, project.registry)


@pytest.mark.parametrize(
    ("invalid", "valid", "rule_id"),
    (
        (
            "Dena finished five sixths as much as its gardener Cato.",
            "Dena finished five sixths as much as their gardener Cato.",
            "arithmetic/fraction-as-much-elided",
        ),
        (
            "In 80 years Bira would be once as old as its child Aven.",
            "In 80 years Bira would be once as old as their child Aven.",
            "arithmetic/temporal-offset-times-as-old-as-future",
        ),
    ),
)
def test_animate_appositive_roles_reject_inanimate_possessives(
    project, invalid: str, valid: str, rule_id: str
) -> None:
    assert rule_id not in _matched_rules(invalid, project.registry)
    assert rule_id in _matched_rules(valid, project.registry)


def test_cross_measure_same_holder_comparison_remains_supported(project) -> None:
    assert "arithmetic/times-as-many-conjunct-elided-standard" in _matched_rules(
        "The head has 7 cats and thrice as many businesses.",
        project.registry,
    )


@pytest.mark.parametrize(
    "rule_id",
    (
        "arithmetic/transfer-ditransitive",
        "arithmetic/fraction-as-many-elided-standard",
        "arithmetic/times-as-many-elided",
        "arithmetic/group-total-leading-marker",
        "arithmetic/anchored-relation-conjoined-anchor",
        "arithmetic/sequential-percent-remainder-partition",
        "arithmetic/stated-age-at-year",
    ),
)
def test_repaired_rules_remain_strictly_generatable(project, rule_id: str) -> None:
    candidate = generate_candidate(project, rule_id=rule_id, seed=57)
    assert candidate.target_status in {"matched", "shadowed"}


def test_generated_calendar_year_and_destinations_use_the_authored_bounds(project) -> None:
    dated = generate_candidate(
        project,
        rule_id="arithmetic/stated-age-at-year",
        seed=5701,
    )
    year = int(dated.target_bindings["calendar_year"])
    assert 1000 <= year <= 9999

    partition = generate_candidate(
        project,
        rule_id="arithmetic/sequential-percent-remainder-partition",
        seed=5702,
    )
    assert all(
        partition.target_bindings[name].endswith("courses")
        for name in ("first_destination", "second_destination", "rest_destination")
    )
