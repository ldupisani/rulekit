"""Review-led finite-form, object-role, and PP attachment boundaries."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate, retest_candidate
from rulekit.kernel.engine import solve


CURATED = Path(__file__).resolve().parents[1] / "projects" / "curated"
GSM8K = Path(__file__).resolve().parents[1] / "projects" / "gsm8k"


@pytest.fixture(scope="module")
def project():
    return load_project(CURATED)


@pytest.fixture(scope="module")
def gsm8k_project():
    return load_project(GSM8K)


def _matched_rules(text: str, registry) -> set[str]:
    result = solve(text, registry)
    return {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


REVIEWED_REJECTIONS = [
    (
        "arithmetic/anaphoric-multiplier-conjunct-many",
        "The shopper finds 20 puzzles instead of my october and thrice this many.",
        1589782911650843,
    ),
    (
        "arithmetic/anaphoric-multiplier-conjunct-many",
        "Aven finished 8 heads beneath the friend and once this many.",
        1589782911650841,
    ),
    (
        "arithmetic/anaphoric-multiplier-conjunct-many",
        "The student finish 9 areas and thrice that many.",
        1589782911650840,
    ),
    (
        "arithmetic/affine-times-as-much",
        "Dena teaching 9 more than thrice as much rest in the area as Cato.",
        1589782911650816,
    ),
    (
        "arithmetic/affine-times-as-much",
        "Aven finishes 2 more than thrice as much rest as Cato.",
        1589782911650810,
    ),
    (
        "arithmetic/affine-times-as-much",
        "Cato wins 70 less than thrice as much clay about the topic as Aven.",
        1589782911650808,
    ),
    (
        "arithmetic/affine-frame-relation",
        (
            "University left 1 more science than twice the number of sciences "
            "that alpaca left."
        ),
        1589782911650747,
    ),
]


@pytest.mark.parametrize(("rule_id", "sentence", "seed"), REVIEWED_REJECTIONS)
def test_latest_reviewed_surfaces_retest_absent(
    project, rule_id: str, sentence: str, seed: int
) -> None:
    candidate = retest_candidate(
        project,
        rule_id=rule_id,
        sentence=sentence,
        seed=seed,
        origin="generated",
    )

    assert candidate.target_status == "absent"
    assert rule_id not in _matched_rules(sentence, project.registry)


@pytest.mark.parametrize(
    ("rule_id", "sentence"),
    [
        (
            "arithmetic/anaphoric-multiplier-conjunct-many",
            "The shopper finds 20 puzzles in the garden and thrice this many.",
        ),
        (
            "arithmetic/anaphoric-multiplier-conjunct-many",
            "Aven finished 8 puzzles in the university and once this many.",
        ),
        (
            "arithmetic/anaphoric-multiplier-conjunct-many",
            "The students finish 9 puzzles and thrice that many.",
        ),
        (
            "arithmetic/affine-times-as-much",
            "Aven has 2 more than thrice as much rest as Cato.",
        ),
        (
            "arithmetic/affine-times-as-much",
            "Cato wins 70 less than thrice as much money as Aven.",
        ),
        (
            "arithmetic/affine-times-as-much",
            "Cato has 70 less than thrice as much clay as Aven.",
        ),
        (
            "arithmetic/affine-frame-relation",
            (
                "The student left 1 more apple than twice the number of apples "
                "that alpaca left."
            ),
        ),
        (
            "arithmetic/affine-frame-relation",
            (
                "Cato sold 6 more books than three times the number of books "
                "that Dena sold."
            ),
        ),
    ],
)
def test_review_boundaries_keep_complete_valid_neighbours(
    project, rule_id: str, sentence: str
) -> None:
    assert rule_id in _matched_rules(sentence, project.registry)


def test_finish_forms_declare_ordinary_subject_agreement(project) -> None:
    assert project.registry.lexicon["finish"].number == "plural"
    assert project.registry.lexicon["finishes"].number == "singular"
    assert "arithmetic/anaphoric-multiplier-conjunct-many" not in _matched_rules(
        "The student finish 9 puzzles and thrice that many.",
        project.registry,
    )


def test_win_and_departure_roles_are_pack_declared(project, gsm8k_project) -> None:
    registry = project.registry
    assert registry.word_in_category("win", "win_quantity_verb")
    assert registry.word_in_category("money", "winnable_quantity_object")
    assert not registry.word_in_category("clay", "winnable_quantity_object")
    assert registry.word_in_category("apple", "transferable_quantity_object")
    assert not registry.word_in_category("science", "transferable_quantity_object")
    assert gsm8k_project.registry.word_in_category(
        "bar", "transferable_quantity_object"
    )


@pytest.mark.parametrize(
    "preposition",
    ["at", "during", "by"],
)
def test_temporal_prepositions_accept_declared_timeperiods(
    project, preposition: str
) -> None:
    registry = project.registry
    assert registry.attribute_applies_to(preposition, "year")


def test_temporal_anaphoric_conjuncts_retain_duration_and_point_adjuncts(
    gsm8k_project,
) -> None:
    rule_id = "arithmetic/anaphoric-multiplier-conjunct-many"
    sentence = (
        "Aven catches 8 birds during the day and twice this many at night."
    )
    assert rule_id in _matched_rules(sentence, gsm8k_project.registry)


@pytest.mark.parametrize(
    ("rule_id", "seed"),
    [
        ("arithmetic/anaphoric-multiplier-conjunct-many", 1589782911650843),
        ("arithmetic/affine-times-as-much", 1589782911650816),
        ("arithmetic/affine-frame-relation", 1589782911650747),
    ],
)
def test_reviewed_rules_still_generate_a_strict_retained_candidate(
    project, rule_id: str, seed: int
) -> None:
    candidate = generate_candidate(project, rule_id=rule_id, seed=seed)
    assert candidate.target_rule == rule_id
    assert candidate.target_status in {"matched", "shadowed"}
    assert candidate.sentence not in {
        sentence for target, sentence, _review_seed in REVIEWED_REJECTIONS
        if target == rule_id
    }
