"""Generated-ask review reconciliation: complete clause and data roles."""

import json
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import (
    GenerationError,
    generate_ask_scenario,
    list_ask_availability,
)
from rulekit.generation.reviews import review_path
from rulekit.kernel.engine import analyze, solve
from rulekit.kernel.patterns import match_ask


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
REVIEW_IDS = {
    "rev-a6e603da753a4902",
    "rev-dd0a4e4e8cef4b2a",
    "rev-7150888faae64b65",
    "rev-12d579ac47864fcb",
    "rev-f85b7d0c93844f2e",
    "rev-6ab00ae2e565484f",
    "rev-8528c3d2e5c54ef6",
    "rev-70c6dbbd77f04078",
    "rev-eef349883290405b",
    "rev-e7c01d946c5d4349",
    "rev-8b5364bbf00141ac",
    "rev-4cb8735859074f49",
    "rev-0a32566cf82b4946",
    "rev-bb83bdc763dd4f5c",
    "rev-510ef128a055418d",
    "rev-cf70e17c9ac44fb1",
    "rev-91f396c597534359",
}
REVIEWED_STANDALONE_QUESTIONS = (
    "How long does it take dollar to buy 70 violinists?",
    "How many did Dena and Cato begin combined?",
    "How many ages do each children give in total?",
    "How many pounds of wool does its travel in all?",
    "How many fewer children than cupboards make there?",
    "How old was their Mary's teacher?",
    "How many fewer cats than dogs sells there?",
    "How many grapes do 5 teach altogether?",
    "How much rest does Fia and Dena give in all?",
    "How many ages were in the university to begin with?",
    "How long is total bird?",
    "How much may toy walked in 80 keys?",
    "What have total number of hours?",
    "How many universities of hour leaving left?",
    "How long does it take money to found all of gardeners?",
    "What is average area of Fia in 2?",
)
POSITIVE_ASKS = (
    (
        "ask/how-long-take-span",
        "How long does it take Dena to buy 70 apples?",
    ),
    (
        "ask/how-many-combined-named-elided-measure",
        "How many did Dena and Cato have combined?",
    ),
    (
        "ask/how-many-plural-combined-quantified-subject",
        "How many books do all children have in total?",
    ),
    (
        "ask/how-many-combined-partitive-in-all",
        "How many pounds of wool do they have in all?",
    ),
    (
        "ask/how-many-more-label-comparative",
        "How many fewer cats than dogs are there?",
    ),
    ("ask/how-old-is-possessed", "How old was their teacher?"),
    (
        "ask/how-old-is-explicitly-possessed",
        "How old was Mary's teacher?",
    ),
    (
        "ask/how-many-combined-cardinal-pronoun",
        "How many grapes do the 5 of them have altogether?",
    ),
    (
        "ask/how-much-combined-named-in-all",
        "How much money did Fia and Dena have in all?",
    ),
    (
        "ask/how-many-in-place-start-state",
        "How many students were in the university to begin with?",
    ),
    ("ask/how-long-is-total-dimension", "How long was the total time?"),
    (
        "ask/how-much-rate-span-modal",
        "How much can Dena earn in 8 hours?",
    ),
    ("ask/what-total-combined", "What is the total number of hours?"),
    (
        "ask/how-many-left-entityless-partitive",
        "How many pounds of wool were left?",
    ),
    ("ask/how-many-left-entityless", "How many books were left?"),
    (
        "ask/how-long-take-span-totality-item",
        "How long does it take Dena to buy all of the apples?",
    ),
    (
        "ask/how-much-noun-entity",
        "How much paper would the pantry sell?",
    ),
    (
        "ask/reference-aggregate-average-year",
        "What is the average population of Europe in 2020?",
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


@pytest.mark.parametrize("question", REVIEWED_STANDALONE_QUESTIONS)
def test_reviewed_standalone_surfaces_are_no_longer_recognized(
    project, question: str
) -> None:
    assert _ask_id(question, project.registry) is None
    assert not solve(question, project.registry).answer.committed


@pytest.mark.parametrize(("ask_id", "question"), POSITIVE_ASKS)
def test_each_narrowed_ask_keeps_a_grammatical_positive_control(
    project, ask_id: str, question: str
) -> None:
    assert _ask_id(question, project.registry) == ask_id


@pytest.mark.parametrize(
    "ask_id",
    sorted(
        ask_id
        for ask_id, _ in POSITIVE_ASKS
        if ask_id != "ask/how-much-noun-entity"
    ),
)
def test_each_narrowed_ask_remains_strictly_generatable(
    project, ask_id: str
) -> None:
    candidate = generate_ask_scenario(
        project,
        ask_id=ask_id,
        seed=51,
        scenario_mode="ask_only",
    )

    assert _ask_id(candidate.question, project.registry) == ask_id


def test_uninverted_embedded_question_is_not_generated_standalone(project) -> None:
    availability = {
        item.id: item for item in list_ask_availability(project)
    }

    assert not availability["ask/how-much-noun-entity-uninverted"].supported
    assert "embedding context" in " ".join(
        availability["ask/how-much-noun-entity-uninverted"].blockers
    )
    with pytest.raises(GenerationError, match="embedding context"):
        generate_ask_scenario(
            project,
            ask_id="ask/how-much-noun-entity-uninverted",
            seed=51,
            scenario_mode="ask_only",
        )


def test_reference_generation_uses_a_complete_data_backed_query(project) -> None:
    candidate = generate_ask_scenario(
        project,
        ask_id="ask/reference-aggregate-average-year",
        seed=51,
        scenario_mode="ask_only",
    )

    assert candidate.question.startswith("What is the average ")
    assert candidate.answer["committed"]
    assert candidate.query["group"] in set(project.registry.reference_groups.values())
    assert 1000 <= int(float(candidate.query["year"])) <= 9999
