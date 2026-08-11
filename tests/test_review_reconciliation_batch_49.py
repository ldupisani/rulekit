"""Generated-ask review reconciliation: grammar and semantic slot boundaries."""

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
    "rev-fff91260f7864063",
    "rev-89f869d1a8b04134",
    "rev-9135e4d9a9794346",
    "rev-817dd6d775ae4bf8",
    "rev-56f1bb019b734366",
    "rev-1f85b0091d934d0b",
    "rev-f7c668590da94782",
    "rev-115b32c5e2254eef",
    "rev-b53b462791be42e7",
    "rev-ace0b1307fc54fbe",
    "rev-55c73332dd6e4644",
    "rev-3075a5ea97a24b54",
    "rev-e04a73ec8f79403d",
    "rev-dd26e4e78d5946aa",
    "rev-9ac2022c79f54b39",
    "rev-3bcbc697e800442d",
    "rev-30581ff441fd42d6",
}
REVIEWED_QUESTIONS = (
    "How many animals do Dena were in beginning?",
    "How many younger cupboards than tomatoes does pantry took?",
    "How many cupboards ran violet?",
    "How much lighter need coin than himself june in trees?",
    "How many areas received large?",
    "How many less sciences than pounds is there?",
    "What 's average amount of eggs that he teaches?",
    "How much change did cupboard receives back?",
    "How old had the alpaca in 16?",
    "What is number of Dena's hamster?",
    "How many violet stickers travels notwithstanding saturday?",
    "What owns difference between plum anything buy?",
    "How many younger amounts than numbers was there?",
    "How many papers does Bira and Mary travel all together?",
    "How much does Fia starting?",
    "How many beige eggs cost amidst area?",
    "How many toys lose not violet?",
)
POSITIVE_ASKS = (
    ("ask/how-many-entity-start-state", "How many animals did Dena have in the beginning?"),
    ("ask/how-many-more-label-comparative-held", "How many more cupboards than tomatoes did Dena have?"),
    ("ask/how-many-partition", "How many cupboards are violet?"),
    ("ask/how-much-dimension-comparative-than-unit", "How much lighter is Cato than Fia in pounds?"),
    ("ask/what-average-combined-contracted", "What's the average number of students that he teaches?"),
    ("ask/how-much-change", "How much change did Dena receive back?"),
    ("ask/how-old-at-year", "How old was the alpaca in 2016?"),
    ("ask/what-is-the-number-of-possessed", "What is the number of Dena's hamsters?"),
    ("ask/how-many-attribute-partition-in-place", "How many violet stickers are in the garden?"),
    ("ask/what-is-the-difference-pronoun", "What is the difference between the number of plums they buy?"),
    ("ask/how-many-combined-named-list-all-together", "How many books do Bira and Mary have all together?"),
    ("ask/how-much-bare-entity", "How much does Fia own?"),
    ("ask/how-many-partition-negated", "How many toys are not violet?"),
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


@pytest.mark.parametrize(("ask_id", "question"), POSITIVE_ASKS)
def test_each_narrowed_ask_keeps_a_grammatical_positive_control(
    project, ask_id: str, question: str
) -> None:
    assert _ask_id(question, project.registry) == ask_id


@pytest.mark.parametrize("ask_id", [ask_id for ask_id, _ in POSITIVE_ASKS])
def test_each_narrowed_ask_remains_strictly_generatable(
    project, ask_id: str
) -> None:
    candidate = generate_ask_scenario(
        project,
        ask_id=ask_id,
        seed=49,
        scenario_mode="ask_only",
    )

    assert _ask_id(candidate.question, project.registry) == ask_id


def test_calendar_year_bounds_apply_to_reading_and_generation(project) -> None:
    assert _ask_id("How old was Cato in 999?", project.registry) != "ask/how-old-at-year"
    assert _ask_id("How old was Cato in 10000?", project.registry) != "ask/how-old-at-year"

    candidate = generate_ask_scenario(
        project,
        ask_id="ask/how-old-at-year",
        seed=49,
        scenario_mode="ask_only",
    )
    year = int(candidate.target_bindings["target_year"])
    assert 1000 <= year <= 9999


def test_contracted_ask_rendering_attaches_the_clitic(project) -> None:
    candidate = generate_ask_scenario(
        project,
        ask_id="ask/what-average-combined-contracted",
        seed=49,
        scenario_mode="ask_only",
    )

    assert candidate.question.startswith("What's ")
    assert "What 's" not in candidate.question
