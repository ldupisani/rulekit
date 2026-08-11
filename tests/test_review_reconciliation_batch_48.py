"""Generated-ask review reconciliation: countability, voice, and roles."""

import json
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import GenerationError, generate_ask_scenario
from rulekit.generation.reviews import review_path
from rulekit.kernel.engine import analyze, solve
from rulekit.kernel.patterns import match_ask


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
REVIEW_IDS = {
    "rev-2a434650cbd340bc",
    "rev-7835aa061bc34278",
    "rev-53ed2a0b6d1449aa",
    "rev-003b55738ae1409b",
}
REVIEWED_QUESTIONS = (
    "How many benches of marble owns enrolls combined excepting cupboards?",
    "How many litter did Aven, Cato, Eron, and Fia enroll individually?",
    "How many course is between garden to begin with?",
    "How many costs lighter buying pound than sunday?",
)
REVIEWED_BINDINGS = (
    (
        "ask/how-many-passive-combined",
        {
            "agg": "combined",
            "be": "owns",
            "grp": "cupboards",
            "item": "benches",
            "p2": "excepting",
            "substance": "marble",
            "verb": "enrolls",
        },
    ),
    (
        "ask/how-many-individually-named-list-postverbal",
        {
            "aux": "did",
            "holders": "Aven, Cato, Eron, and Fia",
            "item": "litter",
            "marker": "individually",
            "verb": "enroll",
        },
    ),
    (
        "ask/how-many-in-place-start-state",
        {
            "item": "course",
            "marker": "begin",
            "place": "garden",
            "prep": "between",
            "verb": "is",
        },
    ),
    (
        "ask/how-many-unit-dimension-comparative-than",
        {
            "a": "pound",
            "aux": "buying",
            "b": "sunday",
            "dir": "lighter",
            "item": "costs",
        },
    ),
)


@pytest.fixture(scope="module")
def project():
    return load_project(CURATED)


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
    assert all(history[review_id]["review_kind"] == "ask" for review_id in REVIEW_IDS)
    assert all(history[review_id]["verdict"] == "invalid" for review_id in REVIEW_IDS)


@pytest.mark.parametrize("question", REVIEWED_QUESTIONS)
def test_reviewed_ask_surfaces_are_no_longer_recognized(
    project, question: str
) -> None:
    assert _ask_id(question, project.registry) is None
    assert not solve(question, project.registry).answer.committed


@pytest.mark.parametrize(("ask_id", "bindings"), REVIEWED_BINDINGS)
def test_generator_cannot_recreate_reviewed_bindings(
    project, ask_id: str, bindings: dict[str, str]
) -> None:
    with pytest.raises(GenerationError):
        generate_ask_scenario(
            project,
            ask_id=ask_id,
            seed=48,
            scenario_mode="ask_only",
            locked_bindings=bindings,
        )


def test_passive_total_requires_voice_object_and_partitive_compatibility(
    project,
) -> None:
    assert _ask_id(
        "How many books were bought in total?", project.registry
    ) == "ask/how-many-passive-combined"
    assert _ask_id(
        "How many pounds of clay were bought in total?", project.registry
    ) == "ask/how-many-passive-combined"
    assert _ask_id(
        "How many benches of marble were bought in total?", project.registry
    ) is None

    result = solve(
        "Cato bought 5 books. Fia bought 7 books. "
        "How many books were bought in total?",
        project.registry,
    )
    assert result.answer.value == 12


def test_passive_total_group_tail_uses_a_declared_scope(project) -> None:
    assert _ask_id(
        "How many books were bought in total in the two cupboards?",
        project.registry,
    ) == "ask/how-many-passive-combined"


def test_individual_ask_distinguishes_count_and_mass_heads(project) -> None:
    assert _ask_id(
        "How many apples did Aven, Cato, Eron, and Fia own individually?",
        project.registry,
    ) == "ask/how-many-individually-named-list-postverbal"
    assert _ask_id(
        "How many litter did Aven, Cato, Eron, and Fia own individually?",
        project.registry,
    ) is None


def test_start_state_requires_plural_agreement_and_an_interior_location(
    project,
) -> None:
    assert _ask_id(
        "How many courses are in the garden to begin with?", project.registry
    ) == "ask/how-many-in-place-start-state"
    assert _ask_id(
        "How many course is in the garden to begin with?", project.registry
    ) is None


def test_dimension_difference_requires_units_copula_and_distinct_holders(
    project,
) -> None:
    assert _ask_id(
        "How many pounds lighter is Cato than Fia?", project.registry
    ) == "ask/how-many-unit-dimension-comparative-than"
    assert _ask_id(
        "How many costs lighter is Cato than Fia?", project.registry
    ) is None
    assert _ask_id(
        "How many pounds lighter is Cato than Cato?", project.registry
    ) is None


@pytest.mark.parametrize(
    "ask_id",
    [
        "ask/how-many-passive-combined",
        "ask/how-many-individually-named-list-postverbal",
        "ask/how-many-in-place-start-state",
        "ask/how-many-unit-dimension-comparative-than",
    ],
)
def test_narrowed_asks_remain_generatable(project, ask_id: str) -> None:
    candidate = generate_ask_scenario(
        project,
        ask_id=ask_id,
        seed=700,
        scenario_mode="ask_only",
    )

    assert _ask_id(candidate.question, project.registry) == ask_id
