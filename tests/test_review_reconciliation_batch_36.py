"""Review-led boundaries for the 2026-08-10 afternoon curated batch."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.data.schemas import WherePredicate
from rulekit.generation import generate_candidate, retest_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Goal


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


@pytest.mark.parametrize(
    ("rule_id", "sentence"),
    [
        (
            "arithmetic/goal-desire-quantity",
            "John wanted to arrive 19 gardens.",
        ),
        (
            "arithmetic/temporal-offset-times-as-old-as-future-std-now",
            (
                "In 4 years Fia do be once as old as her librarian Mary "
                "today."
            ),
        ),
        (
            "arithmetic/percent-change-event-count",
            "Topic travels two tenths more dollars.",
        ),
        (
            "arithmetic/partition-attribute-of-noun",
            "2 of marbles spent large.",
        ),
        (
            "arithmetic/affine-fraction-as-many",
            (
                "The topic leaving 3 fewer than two sevenths as many "
                "pantries at its garden as the bench."
            ),
        ),
        (
            "arithmetic/affine-fraction-as-many",
            (
                "The book leaving 16 less than three sixths as many "
                "librarians at the garden as the gardener."
            ),
        ),
        (
            "arithmetic/affine-frame-relation",
            (
                "Guardian enrolled 80 fewer than triple the number of "
                "courses that John enrolling in 50 years."
            ),
        ),
        (
            "arithmetic/affine-frame-relation",
            (
                "Pencil leaves 1 fewer marble than triple the amount of "
                "marbles that toward leaving."
            ),
        ),
        (
            "arithmetic/affine-frame-relation",
            (
                "February teaches 1 more inch than twice the amount of "
                "inches that your child Dena teaches in 90 years."
            ),
        ),
        (
            "arithmetic/affine-frame-relation",
            (
                "Card owns 18 fewer than double the number of plums that "
                "storeroom owns."
            ),
        ),
        (
            "arithmetic/affine-frame-relation",
            (
                "Tree has 1 fewer area than once the number of areas that "
                "percentage had."
            ),
        ),
        (
            "arithmetic/affine-frame-relation",
            (
                "Cookie had 1 fewer apricot than double the number of "
                "apricots that your librarian John has in 9 years."
            ),
        ),
    ],
)
def test_live_reviewed_surfaces_no_longer_match_target(
    rule_id: str, sentence: str, project
) -> None:
    candidate = retest_candidate(
        project,
        rule_id=rule_id,
        sentence=sentence,
        seed=36,
        origin="generated",
    )

    assert candidate.target_status == "absent"
    assert rule_id not in _matched_rules(sentence, project.registry)


def test_arrival_goal_requires_and_preserves_its_governed_destination(
    project,
) -> None:
    rule_id = "arithmetic/goal-desire-quantity"
    sentence = "John wanted to arrive at 19 gardens."

    assert rule_id in _matched_rules(sentence, project.registry)
    result = solve(sentence, project.registry)
    goal = next(fact for fact in result.facts() if isinstance(fact, Goal))
    assert goal.entity == "john"
    assert goal.measure == "garden"
    assert goal.value == 19


def test_category_requires_bound_is_an_explicit_schema_predicate() -> None:
    predicate = WherePredicate(
        category_requires_bound={
            "slot": "verb",
            "cat": "arrival_motion_verb",
            "bound": "goal_prep",
        }
    )

    assert predicate.category_requires_bound is not None
    assert predicate.category_requires_bound.bound == "goal_prep"


def test_bound_rejects_category_is_an_explicit_schema_predicate() -> None:
    predicate = WherePredicate(
        bound_rejects_category={
            "bound": "echo_span",
            "slot": "echo_verb",
            "cat": "state",
        }
    )

    assert predicate.bound_rejects_category is not None
    assert predicate.bound_rejects_category.slot == "echo_verb"


@pytest.mark.parametrize(
    "rule_id",
    [
        "arithmetic/temporal-offset-times-as-old-as-future",
        "arithmetic/temporal-offset-times-as-old-as-future-std-now",
        "arithmetic/temporal-offset-age-future",
        "arithmetic/temporal-offset-age-future-intensified",
    ],
)
def test_future_age_premises_require_declared_future_modals(
    rule_id: str, project
) -> None:
    rule = next(rule for rule in project.registry.rules if rule.id == rule_id)
    aux = next(
        token for token in rule.match["sentence"] if token.slot == "aux"
    )

    assert aux.cat == "future_modal"
    assert aux.type is None


def test_future_age_standard_pinned_to_today_keeps_valid_modal(project) -> None:
    rule_id = "arithmetic/temporal-offset-times-as-old-as-future-std-now"
    sentence = (
        "In 4 years Fia will be once as old as her librarian Mary today."
    )

    assert rule_id in _matched_rules(sentence, project.registry)


@pytest.mark.parametrize(
    "rule_id",
    ["arithmetic/percent-change-event", "arithmetic/percent-change-event-count"],
)
def test_currency_change_rules_declare_motion_role_boundaries(
    rule_id: str, project
) -> None:
    rule = next(rule for rule in project.registry.rules if rule.id == rule_id)
    licences = {
        (
            predicate.verb_role_compatible.roles[0],
            predicate.verb_role_compatible.role_cat,
        )
        for predicate in rule.where
        if predicate.verb_role_compatible is not None
        and predicate.verb_role_compatible.verb_cat
        == "motion_comparison_verb"
    }

    assert licences == {
        ("who", "motion_participant"),
        ("item", "motion_comparison_measure"),
    }


def test_currency_change_keeps_ordinary_nonmotion_neighbour(project) -> None:
    rule_id = "arithmetic/percent-change-event-count"
    sentence = "The teacher owns two tenths more dollars."

    assert rule_id in _matched_rules(sentence, project.registry)


@pytest.mark.parametrize(
    ("rule_id", "sentence"),
    [
        (
            "arithmetic/affine-fraction-as-many",
            (
                "The teacher has 3 fewer than two sevenths as many birds "
                "as the gardener."
            ),
        ),
        (
            "arithmetic/affine-frame-relation",
            (
                "The guardian enrolled 80 fewer than triple the number of "
                "courses that John enrolled in 50 years."
            ),
        ),
        (
            "arithmetic/affine-frame-relation",
            (
                "The teacher owns 18 fewer than double the number of plums "
                "that John owns."
            ),
        ),
    ],
)
def test_new_review_boundaries_keep_grammatical_neighbours(
    rule_id: str, sentence: str, project
) -> None:
    assert rule_id in _matched_rules(sentence, project.registry)


def test_affine_review_boundaries_are_pack_declared(project) -> None:
    rules = {rule.id: rule for rule in project.registry.rules}

    for rule_id in {
        "arithmetic/affine-times-as-many",
        "arithmetic/affine-fraction-as-many",
    }:
        rule = rules[rule_id]
        verb = next(
            token for token in rule.match["sentence"] if token.slot == "verb"
        )
        assert verb.finite_form is True
        licences = {
            (
                tuple(predicate.verb_role_compatible.roles),
                predicate.verb_role_compatible.role_cat,
            )
            for predicate in rule.where
            if predicate.verb_role_compatible is not None
            and predicate.verb_role_compatible.verb_cat
            == "motion_comparison_verb"
        }
        assert licences == {
            (("who",), "motion_participant"),
            (("std",), "motion_participant"),
            (("item",), "motion_comparison_measure"),
        }

    frame = rules["arithmetic/affine-frame-relation"]
    frame_tokens = {
        token.slot: token
        for token in frame.match["sentence"]
        if token.slot in {"who", "verb", "std", "echo_verb"}
    }
    assert frame_tokens["who"].common_noun_cat == "quantity_holder"
    assert frame_tokens["std"].common_noun_cat == "quantity_holder"
    assert frame_tokens["verb"].finite_form is True
    assert frame_tokens["echo_verb"].finite_form is True
    state_span_boundary = next(
        predicate.bound_rejects_category
        for predicate in frame.where
        if predicate.bound_rejects_category is not None
    )
    assert state_span_boundary.bound == "echo_span"
    assert state_span_boundary.slot == "echo_verb"
    assert state_span_boundary.cat == "state"
    assert project.registry.word_in_category("leaves", "quantity_event_verb")
    assert project.registry.word_in_category("owns", "animate_subject_verb")


@pytest.mark.parametrize(
    "rule_id",
    [
        "arithmetic/goal-desire-quantity",
        "arithmetic/temporal-offset-times-as-old-as-future-std-now",
        "arithmetic/percent-change-event-count",
        "arithmetic/affine-fraction-as-many",
        "arithmetic/affine-frame-relation",
    ],
)
def test_reconciled_rules_still_generate_strict_matches(
    rule_id: str, project
) -> None:
    candidate = generate_candidate(project, rule_id=rule_id, seed=36)

    assert candidate.target_status == "matched"
    assert rule_id in {match.rule_id for match in candidate.actual_matches}
