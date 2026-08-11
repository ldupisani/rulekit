"""Generated-ask review reconciliation: grammatical quantity questions."""

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
    "rev-c251201f193d466b",
    "rev-9b0c7c76bf2e4281",
    "rev-b0c6ad7cb7444b20",
    "rev-da3a7dcafc20445e",
    "rev-9fc577d01b5e4288",
    "rev-fa9a82a2621c4406",
    "rev-02ea2aeb12834005",
    "rev-94b6079def804ff8",
    "rev-10535f0af3c54cd8",
    "rev-f3d726d5db4d4bba",
    "rev-a8439c9ec4104fe6",
    "rev-4ee0d642c874495d",
}
REVIEWED_QUESTIONS = (
    "How many times might wednesday sell in 90 inches?",
    "How many ages does Bira and Mary each get?",
    "How many amounts does it take for Bira to need 12 sciences?",
    "How many universities did Eron and Mary take total?",
    "How many teachers small were Cato?",
    "How many pounds of papers eats regarding population?",
    "How much do child ran in 18 minutes?",
    "Is Mary february?",
    "How many hamsters did violet fish arrive?",
    "How many pears should pantry cost in 14 rabbits?",
    "How many does Fia be?",
    "How many hours would violinist is to start with?",
)
POSITIVE_ASKS = (
    (
        "ask/how-many-rate-span-modal",
        "How many apples can Dena buy in 15 hours?",
    ),
    (
        "ask/how-many-each-named-list",
        "How many books do Bira and Mary each have?",
    ),
    (
        "ask/how-many-timeunit-take-span",
        "How many hours does it take Bira to buy 12 apples?",
    ),
    (
        "ask/how-many-combined-named",
        "How many books did Eron and Mary have total?",
    ),
    (
        "ask/how-many-unit-dimension-is",
        "How many inches tall was Cato?",
    ),
    (
        "ask/how-many-in-place-partitive",
        "How many pounds of paper are in the pantry?",
    ),
    (
        "ask/how-much-rate-span",
        "How much does the teacher spend in 18 minutes?",
    ),
    ("ask/is-membership", "Is Mary a teacher?"),
    (
        "ask/how-many-entity-qualified",
        "How many hamsters did violet fish have?",
    ),
    ("ask/how-many-entity-elided-measure", "How many does Fia have?"),
    (
        "ask/how-many-entity-common-noun-start-state",
        "How many hours would the violinist have to start with?",
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
def test_each_narrowed_ask_keeps_a_grammatical_positive_control(
    project, ask_id: str, question: str
) -> None:
    assert _ask_id(question, project.registry) == ask_id


@pytest.mark.parametrize("ask_id", sorted({ask_id for ask_id, _ in POSITIVE_ASKS}))
def test_each_narrowed_ask_remains_strictly_generatable(
    project, ask_id: str
) -> None:
    candidate = generate_ask_scenario(
        project,
        ask_id=ask_id,
        seed=52,
        scenario_mode="ask_only",
    )

    assert _ask_id(candidate.question, project.registry) == ask_id


@pytest.mark.parametrize(
    "ask_id",
    (
        "ask/how-many-combined-named",
        "ask/how-many-combined-named-list",
        "ask/how-many-each-named-list",
        "ask/how-many-each-named-list-postverbal",
    ),
)
def test_coordinated_ask_generation_uses_plural_do_support(
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
