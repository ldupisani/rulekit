"""Generated-ask review reconciliation: coordinated and role-safe asks."""

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
    "rev-f592516dcdc14773",
    "rev-166b3088a97842d2",
    "rev-50fe1acb6a324aac",
    "rev-dda53333d7ea43f8",
    "rev-caf90a313e9740d1",
    "rev-8c3a8a0145024b54",
    "rev-781b2f04bafc4a9f",
    "rev-7fba1ee2fb2a4169",
    "rev-8a752cb90aad4f66",
    "rev-65849d8d0d0a4615",
    "rev-48784641423a4102",
    "rev-aad83616f099447b",
    "rev-13ed8340e44a44fb",
    "rev-dee18e039ba54e0e",
}
REVIEWED_QUESTIONS = (
    "What was the difference in the number of prices they spend?",
    "How much money does she enroll in total?",
    "How many students do Cato and Cato receive in all?",
    "How many cupboards did the 40 be altogether?",
    "How much rest will they win in all?",
    "How many grapes do Eron and Fia begin combined?",
    "How much sand do Aven and Bira be combined?",
    "How many sciences does february own to start with?",
    "How many percentages do Cato's guardians own?",
    "Is Dena benches?",
    "How many minutes of cards earning there?",
    "How many pounds of sand did Aven and Cato travel combined?",
    "Compute combined age of 5?",
    "How many envelope would it take for december to have all of animals?",
)
POSITIVE_ASKS = (
    (
        "ask/what-is-the-difference-pronoun",
        "What was the difference in the number of books they have?",
    ),
    ("ask/how-much-combined", "How much money does she have in total?"),
    (
        "ask/how-many-combined-named-in-all",
        "How many students do Cato and Dena receive in all?",
    ),
    (
        "ask/how-many-combined-cardinal-pronoun",
        "How many cupboards did the 40 have altogether?",
    ),
    (
        "ask/how-much-combined-in-all",
        "How much money will they win in all?",
    ),
    (
        "ask/how-many-combined-named",
        "How many courses do Eron and Fia begin combined?",
    ),
    (
        "ask/how-much-combined-named",
        "How much sand do Aven and Bira have combined?",
    ),
    (
        "ask/how-many-entity-common-noun-start-state",
        "How many books does the university own to start with?",
    ),
    (
        "ask/how-many-entity-possessed",
        "How many books do Cato's guardians own?",
    ),
    ("ask/is-membership", "Is Dena a teacher?"),
    ("ask/how-many-there", "How many pounds of sand are there?"),
    (
        "ask/how-many-combined-named-partitive",
        "How many pounds of sand did Aven and Cato have combined?",
    ),
    (
        "ask/imperative-combined-dimension",
        "Compute combined age of the 5?",
    ),
    (
        "ask/how-many-timeunit-take-span-totality-item",
        "How many hours would it take for the teacher to have all of the animals?",
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
def test_reviewed_surfaces_are_no_longer_recognized(project, question: str) -> None:
    assert _ask_id(question, project.registry) is None
    assert not solve(question, project.registry).answer.committed


@pytest.mark.parametrize(("ask_id", "question"), POSITIVE_ASKS)
def test_narrowed_asks_keep_grammatical_positive_controls(
    project, ask_id: str, question: str
) -> None:
    assert _ask_id(question, project.registry) == ask_id


@pytest.mark.parametrize("ask_id", sorted({ask_id for ask_id, _ in POSITIVE_ASKS}))
def test_narrowed_asks_remain_strictly_generatable(project, ask_id: str) -> None:
    candidate = generate_ask_scenario(
        project,
        ask_id=ask_id,
        seed=53,
        scenario_mode="ask_only",
    )

    assert _ask_id(candidate.question, project.registry) == ask_id


@pytest.mark.parametrize(
    "ask_id",
    (
        "ask/how-many-combined-named-in-all",
        "ask/how-many-combined-named-partitive",
        "ask/how-much-combined-named",
    ),
)
def test_new_coordinated_ask_families_generate_plural_do_support(
    project, ask_id: str
) -> None:
    for seed in range(8):
        candidate = generate_ask_scenario(
            project,
            ask_id=ask_id,
            seed=seed,
            scenario_mode="ask_only",
        )

        assert " does " not in f" {candidate.question.lower()} "
