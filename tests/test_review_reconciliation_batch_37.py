"""Review-led affine role boundaries for the 2026-08-10 evening batch."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate, retest_candidate
from rulekit.kernel.engine import solve


CURATED = Path(__file__).resolve().parents[1] / "projects" / "curated"


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


REVIEWED_REJECTIONS = [
    (
        "arithmetic/affine-item-relation-clause",
        "Friday arrived $16 less than thrice the money Fia arrived in 10 years.",
    ),
    (
        "arithmetic/affine-item-relation-clause",
        "Storeroom traveled $18 more than double the money John travels.",
    ),
    (
        "arithmetic/affine-item-relation-clause",
        "Toward left 4 dollars less than once the money Aven left in 4 hours.",
    ),
    (
        "arithmetic/affine-item-relation-clause",
        "Coin wanting $6 more than double the money Eron wanted.",
    ),
    (
        "arithmetic/affine-item-relation-clause",
        "Dog walked 8 dollars less than once the money Fia walked in 18 years.",
    ),
    (
        "arithmetic/affine-item-relation-clause",
        "Remainder dropped $10 less than twice the money Dena dropped.",
    ),
    (
        "arithmetic/affine-frame-relation-clause",
        "The pantry owns 4 fewer than twice the number of cards their librarian Bira owns in 16 years.",
    ),
    (
        "arithmetic/affine-frame-relation-clause",
        "The animal eats 1 fewer year than double the number of years his librarian Fia ate in 3 minutes.",
    ),
    (
        "arithmetic/affine-frame-relation-clause",
        "The teacher drops 1 fewer garden than twice the number of gardens your teacher Mary dropped in 50 hours.",
    ),
    (
        "arithmetic/affine-frame-relation-clause",
        "The cupboard taught 3 fewer than triple the number of puzzles my violinist Cato taught.",
    ),
    (
        "arithmetic/affine-frame-relation-clause",
        "The bench owns 1 fewer course than double the amount of courses her child Aven owns in 19 minutes.",
    ),
    (
        "arithmetic/affine-frame-relation-clause",
        "The garden taught 90 more than thrice the number of apples the bird teach.",
    ),
    (
        "arithmetic/affine-frame-relation-clause",
        "John drops 1 more area than thrice the number of areas Mary drops in 80 years.",
    ),
    (
        "arithmetic/affine-frame-relation-clause",
        "The hamster enrolls 10 fewer than double the number of times my violinist John enrolls.",
    ),
    (
        "arithmetic/affine-frame-relation-clause",
        "The cat has 1 fewer puzzle than twice the number of puzzles Bira has in 17 hours.",
    ),
    (
        "arithmetic/affine-frame-relation-clause",
        "The head teaches 4 fewer than double the amount of grapes their shopper Dena teach in 80 minutes.",
    ),
    (
        "arithmetic/affine-frame-relation",
        "Bench finish 50 fewer than thrice the number of keys that alpaca finish in 1 hour.",
    ),
    (
        "arithmetic/affine-frame-relation",
        "Garden finishes 1 more coin than double the amount of coins that their librarian Aven finish.",
    ),
    (
        "arithmetic/affine-frame-relation",
        "Pantry finish 1 fewer cupboard than thrice the number of cupboards that your friend Mary finished in 17 years.",
    ),
    (
        "arithmetic/affine-fraction-as-many",
        "The violinist finish 60 more than four fifths as many violinists at the tree as Cato.",
    ),
    (
        "arithmetic/affine-fraction-as-many",
        "The storeroom finishes 2 less than five sixths as many keys with the remainder as the violinist.",
    ),
    (
        "arithmetic/affine-fraction-as-many",
        "The pantry had 40 fewer than three tenths as many times as their shopper Aven.",
    ),
    (
        "arithmetic/affine-fraction-as-many",
        "John enrolled 3 less than four fourths as many pounds about your topic as the student.",
    ),
    (
        "arithmetic/affine-fraction-as-many",
        "The garden finished 40 less than three thirds as many minutes at the garden as the gardener.",
    ),
    (
        "arithmetic/affine-fraction-as-many",
        "The cupboard left 50 fewer than three sevenths as many cans at his tree as your teacher Mary.",
    ),
]


@pytest.mark.parametrize(("rule_id", "sentence"), REVIEWED_REJECTIONS)
def test_reviewed_affine_surfaces_are_absent(
    rule_id: str, sentence: str, project
) -> None:
    candidate = retest_candidate(
        project,
        rule_id=rule_id,
        sentence=sentence,
        seed=37,
        origin="generated",
    )

    assert candidate.target_status == "absent"
    assert rule_id not in _matched_rules(sentence, project.registry)


@pytest.mark.parametrize(
    ("rule_id", "sentence"),
    [
        (
            "arithmetic/affine-item-relation-clause",
            "Cato has 4 dollars less than twice the money Dena has.",
        ),
        (
            "arithmetic/affine-frame-relation",
            "The teacher finished 1 fewer puzzle than twice the number of puzzles that John finished.",
        ),
        (
            "arithmetic/affine-frame-relation-clause",
            "The teacher taught 4 fewer than twice the number of courses Mary taught.",
        ),
        (
            "arithmetic/affine-fraction-as-many",
            "The teacher ate 3 fewer than one half as many apples as the gardener.",
        ),
    ],
)
def test_affine_role_boundaries_keep_plausible_neighbours(
    rule_id: str, sentence: str, project
) -> None:
    assert rule_id in _matched_rules(sentence, project.registry)


@pytest.mark.parametrize(
    "rule_id",
    [
        "arithmetic/affine-frame-relation",
        "arithmetic/affine-frame-relation-clause",
        "arithmetic/affine-item-relation-clause",
        "arithmetic/affine-fraction-as-many",
    ],
)
def test_reconciled_affine_rules_still_generate_strict_matches(
    rule_id: str, project
) -> None:
    candidate = generate_candidate(project, rule_id=rule_id, seed=37)

    assert candidate.target_status == "matched"
    assert rule_id in {match.rule_id for match in candidate.actual_matches}
