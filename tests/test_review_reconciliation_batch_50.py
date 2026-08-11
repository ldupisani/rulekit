"""Generated-ask review reconciliation: clause roles and plausible frames."""

import json
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_ask_scenario
from rulekit.generation.reviews import review_path
from rulekit.kernel.engine import analyze, solve
from rulekit.kernel.patterns import match_ask


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
GSM8K = ROOT / "projects" / "gsm8k"
REVIEW_IDS = {
    "rev-1bf86d2bc92d4ba6",
    "rev-479951030fa84ab9",
    "rev-466a74c615304647",
    "rev-d12a06977c774eca",
    "rev-e97e26420d14496e",
    "rev-61c479b00e55498a",
    "rev-8c4dd60c3c7e41a1",
    "rev-54d9f067762644c6",
    "rev-dbc3d9f96ed04e89",
    "rev-2d727a89b68444bb",
    "rev-f48a292845ba4e2a",
    "rev-9e62b041425145d7",
}
REVIEWED_QUESTIONS = (
    "How many total prices do everyone travel?",
    "How many violinists did John's drum have?",
    "How much rest in all?",
    "How much numbers in cats does book travel?",
    "What is difference into trees Aven and Mary enrolled?",
    "How many years old are Dena?",
    "What own cost of 2 heads?",
    "How many year slower does friend finish its age than paper?",
    "How many total populations would her travel?",
    "What were the difference between rabbits they make?",
    "Is Bira amount?",
    "How many marbles has there in Aven's tree?",
)
POSITIVE_ASKS = (
    (
        "ask/how-many-combined-prenominal-marker",
        "A zoo has 6 penguins and 8 bears. How many total animals did they have?",
    ),
    (
        "ask/how-many-entity-possessed",
        "How many flowers did Dena's garden have?",
    ),
    (
        "ask/how-much-combined-in-all",
        "Aven has 6 dollars. Bira has 4 dollars. How much money did they have in all?",
    ),
    (
        "ask/how-much-noun-entity",
        "How much money does the teacher have?",
    ),
    (
        "ask/what-is-the-difference-named",
        "What is the difference between the number of trees Aven and Mary enrolled?",
    ),
    ("ask/how-many-years-old-is", "How many years old is Dena?"),
    ("ask/what-is-the-cost-of-quantity", "What is the cost of 2 heads?"),
    (
        "ask/how-many-unit-task-completion-comparative-than",
        "How many minutes faster did Aven finish the task than Bira?",
    ),
    (
        "ask/what-is-the-difference-pronoun",
        "What is the difference between the number of rabbits they make?",
    ),
    ("ask/is-membership", "Is Bira a teacher?"),
    (
        "ask/how-many-there-in-possessed-place",
        "How many marbles are there in Aven's garden?",
    ),
)


@pytest.fixture(scope="module")
def project():
    return load_project(CURATED)


@pytest.fixture(scope="module")
def gsm_project():
    return load_project(GSM8K)


def _ask_id(question: str, registry) -> str | None:
    matched = match_ask(analyze(question, registry), registry)
    return None if matched is None else matched[0].id


def _ask_id_from_text(text: str, registry) -> str | None:
    result = solve(text, registry)
    matched = match_ask(result.question, registry) if result.question else None
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


@pytest.mark.parametrize(("ask_id", "question"), POSITIVE_ASKS)
def test_each_narrowed_ask_keeps_a_grammatical_positive_control(
    project, ask_id: str, question: str
) -> None:
    assert _ask_id_from_text(question, project.registry) == ask_id


@pytest.mark.parametrize("ask_id", sorted({ask_id for ask_id, _ in POSITIVE_ASKS}))
def test_each_narrowed_ask_remains_strictly_generatable(
    project, ask_id: str
) -> None:
    candidate = generate_ask_scenario(
        project,
        ask_id=ask_id,
        seed=50,
        scenario_mode="ask_only",
    )

    assert _ask_id(candidate.question, project.registry) == ask_id


def test_completion_question_keeps_a_declared_real_world_task(gsm_project) -> None:
    result = solve(
        "Cora took 1 hour to finish the homework while "
        "Dax took 30 minutes to finish it. "
        "How many minutes slower did Cora finish the homework than Dax?",
        gsm_project.registry,
    )

    assert result.answer.value == 30
