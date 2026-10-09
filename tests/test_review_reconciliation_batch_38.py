"""Review-led topical modifier/quantity-host boundary."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import GenerationError, generate_candidate, retest_candidate
from rulekit.kernel.engine import solve


CURATED = Path(__file__).resolve().parents[1] / "projects" / "curated"
RULE_ID = "arithmetic/affine-fraction-as-many"


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


def test_reviewed_topic_modifier_cannot_attach_to_eggs(project) -> None:
    sentence = (
        "The animal owns 18 fewer than five eighths as many eggs about the "
        "topic as my teacher John."
    )

    candidate = retest_candidate(
        project,
        rule_id=RULE_ID,
        sentence=sentence,
        seed=38,
        origin="generated",
    )

    assert candidate.target_status == "absent"
    assert RULE_ID not in _matched_rules(sentence, project.registry)


def test_reviewed_remainder_modifier_cannot_attach_to_affine_relation(
    project,
) -> None:
    sentence = (
        "The librarian leaves 10 more than two sixths as many flowers with "
        "their rest as your librarian Fia."
    )

    candidate = retest_candidate(
        project,
        rule_id=RULE_ID,
        sentence=sentence,
        seed=38,
        origin="generated",
    )

    assert candidate.target_status == "absent"
    assert RULE_ID not in _matched_rules(sentence, project.registry)


def test_reviewed_tomato_cannot_take_a_tree_surface_modifier(project) -> None:
    sentence = (
        "The guardian gave 50 fewer than three thirds as many tomatoes on "
        "his tree as John."
    )

    candidate = retest_candidate(
        project,
        rule_id=RULE_ID,
        sentence=sentence,
        seed=38,
        origin="generated",
    )

    assert candidate.target_status == "absent"
    assert RULE_ID not in _matched_rules(sentence, project.registry)


def test_reviewed_bare_number_cannot_be_a_possession_object(project) -> None:
    sentence = (
        "The bench had 12 more than three thirds as many numbers as their "
        "gardener Mary."
    )

    candidate = retest_candidate(
        project,
        rule_id=RULE_ID,
        sentence=sentence,
        seed=40,
        origin="generated",
    )

    assert candidate.target_status == "absent"
    assert RULE_ID not in _matched_rules(sentence, project.registry)


def test_reviewed_animal_cannot_be_a_teaching_subject(project) -> None:
    reviewed = (
        "The bird teach 15 more than nine tenths as many puzzles as the "
        "guardian."
    )
    grammatical_animal = (
        "The bird teaches 15 more than nine tenths as many puzzles as the "
        "guardian."
    )

    for sentence in (reviewed, grammatical_animal):
        candidate = retest_candidate(
            project,
            rule_id=RULE_ID,
            sentence=sentence,
            seed=41,
            origin="generated",
        )
        assert candidate.target_status == "absent"
        assert RULE_ID not in _matched_rules(sentence, project.registry)


def test_reviewed_pantry_cannot_possess_bare_populations(project) -> None:
    sentence = (
        "The pantry has 40 more than two eighths as many populations as his "
        "child John."
    )

    candidate = retest_candidate(
        project,
        rule_id=RULE_ID,
        sentence=sentence,
        seed=42,
        origin="generated",
    )

    assert candidate.target_status == "absent"
    assert RULE_ID not in _matched_rules(sentence, project.registry)
    assert project.registry.word_in_category(
        "population", "bare_possession_incompatible_noun"
    )


def test_reviewed_transfer_cannot_use_a_frequency_measure(project) -> None:
    sentence = (
        "The bird gave 7 less than four eighths as many times in the area as "
        "your shopper Dena."
    )

    candidate = retest_candidate(
        project,
        rule_id=RULE_ID,
        sentence=sentence,
        seed=43,
        origin="generated",
    )

    assert candidate.target_status == "absent"
    assert RULE_ID not in _matched_rules(sentence, project.registry)


def test_reviewed_quantity_holder_cannot_repeat_as_pp_location(project) -> None:
    sentence = (
        "The pantry has 10 more than nine tenths as many hamsters in my "
        "pantry as my violinist Cato."
    )

    candidate = retest_candidate(
        project,
        rule_id=RULE_ID,
        sentence=sentence,
        seed=43,
        origin="generated",
    )

    assert candidate.target_status == "absent"
    assert RULE_ID not in _matched_rules(sentence, project.registry)


@pytest.mark.parametrize(
    ("rule_id", "sentence"),
    [
        (
            "arithmetic/affine-times-as-many",
            "The pantry has 10 more than twice as many hamsters in my garden "
            "as my violinist Cato.",
        ),
        (
            RULE_ID,
            "The pantry has 10 more than nine tenths as many hamsters in my "
            "garden as my violinist Cato.",
        ),
    ],
)
def test_affine_quantity_holder_can_use_a_different_pp_location(
    project, rule_id: str, sentence: str
) -> None:
    assert rule_id in _matched_rules(sentence, project.registry)


def test_generator_enforces_distinct_holder_and_pp_location(project) -> None:
    locked = {
        "who": "the pantry",
        "verb": "has",
        "item": "hamsters",
        "pp_prep": "in",
        "pp_det": "my",
    }

    with pytest.raises(GenerationError, match="no filler for pp_obj"):
        generate_candidate(
            project,
            rule_id=RULE_ID,
            seed=43,
            max_attempts=1,
            locked_bindings={**locked, "pp_obj": "pantry"},
        )

    valid = generate_candidate(
        project,
        rule_id=RULE_ID,
        seed=43,
        max_attempts=8,
        locked_bindings={**locked, "pp_obj": "garden"},
    )
    assert valid.target_status == "matched"


def test_topic_modifier_remains_valid_for_declared_host(project) -> None:
    sentence = (
        "The teacher owns 18 fewer than five eighths as many books about the "
        "topic as John."
    )

    assert RULE_ID in _matched_rules(sentence, project.registry)


def test_undeclared_locative_modifier_remains_open(project) -> None:
    sentence = (
        "The animal owns 18 fewer than five eighths as many eggs in the "
        "pantry as John."
    )

    assert RULE_ID in _matched_rules(sentence, project.registry)


def test_tree_borne_and_non_tree_surface_neighbours_remain_valid(project) -> None:
    apple_tree = (
        "The guardian gave 50 fewer than three thirds as many apples on "
        "his tree as John."
    )
    tomato_bench = (
        "The guardian gave 50 fewer than three thirds as many tomatoes on "
        "his bench as John."
    )

    assert RULE_ID in _matched_rules(apple_tree, project.registry)
    assert RULE_ID in _matched_rules(tomato_bench, project.registry)


def test_number_remains_countable_in_an_event_frame(project) -> None:
    event = (
        "The guardian gave 12 more than three thirds as many numbers as John."
    )
    concrete_possession = (
        "The bench had 12 more than three thirds as many apples as Mary."
    )

    assert RULE_ID in _matched_rules(event, project.registry)
    assert RULE_ID in _matched_rules(concrete_possession, project.registry)


@pytest.mark.parametrize(
    "sentence",
    [
        "The teacher teaches 15 more than nine tenths as many puzzles as the guardian.",
        "The teachers teach 15 more than nine tenths as many puzzles as the guardians.",
        "The teacher taught 15 more than nine tenths as many puzzles as the guardian.",
        "John taught 15 more than nine tenths as many puzzles as Mary.",
    ],
)
def test_human_teaching_comparisons_remain_valid(sentence: str, project) -> None:
    assert RULE_ID in _matched_rules(sentence, project.registry)


def test_transfer_objects_and_motion_frequency_remain_valid(project) -> None:
    gave_apples = (
        "The bird gave 7 less than four eighths as many apples in the area as "
        "your shopper Dena."
    )
    sold_flowers = (
        "The shopper sold 7 less than four eighths as many flowers as Dena."
    )
    traveled_times = (
        "The bird traveled four eighths as many times in the area as Dena."
    )

    for sentence in (gave_apples, sold_flowers):
        assert RULE_ID in _matched_rules(sentence, project.registry)
    assert "arithmetic/fraction-as-many" in _matched_rules(
        traveled_times, project.registry
    )


def test_modifier_host_relation_is_declarative_and_separate(project) -> None:
    registry = project.registry

    assert registry.modifier_has_host_boundary("about")
    assert registry.modifier_applies_to_host("about", "book")
    assert not registry.modifier_applies_to_host("about", "egg")
    assert not registry.modifier_has_host_boundary("in")
    assert registry.attribute_applies_to("about", "topic")
    assert registry.modifier_attaches_to("on", "tree", "apple")
    assert not registry.modifier_attaches_to("on", "tree", "tomato")
    assert registry.modifier_attaches_to("on", "bench", "tomato")


def test_generator_enforces_the_same_modifier_host_boundary(project) -> None:
    valid = generate_candidate(
        project,
        rule_id=RULE_ID,
        seed=38,
        max_attempts=8,
        locked_bindings={
            "item": "books",
            "pp_prep": "about",
            "pp_obj": "topic",
        },
    )
    assert valid.target_status == "matched"

    with pytest.raises(GenerationError, match="no filler for (item|verb)"):
        generate_candidate(
            project,
            rule_id=RULE_ID,
            seed=38,
            max_attempts=1,
            locked_bindings={
                "item": "eggs",
                "pp_prep": "about",
                "pp_obj": "topic",
            },
        )
