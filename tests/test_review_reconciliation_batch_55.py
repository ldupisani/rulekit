"""Generated-ask review reconciliation: role-aware modern ask generation."""

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
REVIEW_IDS = {
    "rev-1b0f60f6626b4a72",
    "rev-17f5202dc8cf48eb",
    "rev-81c3a7986b494c90",
    "rev-504be6195d4449d0",
    "rev-8d7752ccf2fa463c",
    "rev-ef0a5abf0ca24e06",
    "rev-1f03ae685db5491d",
    "rev-04daa7b7df5b4c3d",
}
REVIEWED_QUESTIONS = (
    "How many pounds of sand receive there in total in universities?",
    "How many hours does it take for hamster to teach 19 pounds?",
    "How many years does it take for cat to begin 5 years?",
    "How many dollars did no 8 cats earn?",
    "How much will Aven be?",
    "What is the difference in amounts they arrive?",
    "How many apples must the animal begin in 5 hours?",
    "How many friends do no 15 hamsters own?",
)
POSITIVE_ASKS = (
    (
        "ask/how-many-there-combined",
        "How many pounds of sand are there in total in universities?",
    ),
    (
        "ask/how-many-timeunit-take-span",
        "How many hours does it take for the teacher to make 19 toys?",
    ),
    (
        "ask/how-many-plural-combined-cardinal-subject",
        "How many dollars did all 8 teachers earn?",
    ),
    ("ask/how-much-bare-entity", "How much will Aven have?"),
    (
        "ask/what-is-the-difference-pronoun",
        "What is the difference in apples they have?",
    ),
    (
        "ask/how-many-rate-span-modal",
        "How many apples can the animal eat in 5 hours?",
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
def test_reviewed_surfaces_never_commit(project, question: str) -> None:
    assert not solve(question, project.registry).answer.committed


@pytest.mark.parametrize(
    "question",
    (
        "How many hours does it take for hamster to teach 19 pounds?",
        "How many years does it take for cat to begin 5 years?",
        "How many dollars did no 8 cats earn?",
        "How many apples must the animal begin in 5 hours?",
        "How many friends do no 15 hamsters own?",
    ),
)
def test_role_or_quantifier_failures_are_not_recognized(project, question: str) -> None:
    assert _ask_id(question, project.registry) is None


@pytest.mark.parametrize(("ask_id", "question"), POSITIVE_ASKS)
def test_narrowed_asks_keep_grammatical_positive_controls(
    project, ask_id: str, question: str
) -> None:
    assert _ask_id(question, project.registry) == ask_id


@pytest.mark.parametrize("ask_id", sorted({row[0] for row in POSITIVE_ASKS}))
def test_each_reviewed_ask_generates_role_compatible_questions(
    project, ask_id: str
) -> None:
    for seed in range(4):
        candidate = generate_ask_scenario(
            project,
            ask_id=ask_id,
            seed=seed,
            scenario_mode="ask_only",
        )
        assert _ask_id(candidate.question, project.registry) == ask_id


def test_existential_generation_uses_a_plural_copula(project) -> None:
    for seed in range(6):
        candidate = generate_ask_scenario(
            project,
            ask_id="ask/how-many-there-combined",
            seed=seed,
            scenario_mode="ask_only",
        )
        assert candidate.target_bindings["verb"] in {"are", "were"}


def test_cardinal_subject_generation_never_prefixes_no(project) -> None:
    for seed in range(8):
        candidate = generate_ask_scenario(
            project,
            ask_id="ask/how-many-plural-combined-cardinal-subject",
            seed=seed,
            scenario_mode="ask_only",
        )
        assert candidate.target_bindings.get("q") != "no"


def test_bare_currency_generation_does_not_use_copular_be(project) -> None:
    for seed in range(6):
        candidate = generate_ask_scenario(
            project,
            ask_id="ask/how-much-bare-entity",
            seed=seed,
            scenario_mode="ask_only",
        )
        assert candidate.target_bindings["verb"] != "be"
