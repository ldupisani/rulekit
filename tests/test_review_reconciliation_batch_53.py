"""Generated-ask review reconciliation: modern grammatical slot boundaries."""

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
    "rev-25e815713dc345bd",
    "rev-bdffcb6488d9459d",
    "rev-e081fc057c1c4593",
    "rev-ebe3379c98914bb8",
    "rev-362f4bd847cb463b",
    "rev-a0df5082e0e046bf",
    "rev-d80c3c2748cf4e7d",
    "rev-29a4459b5c734cf2",
    "rev-44e19f445b614e40",
    "rev-25b933aa32764e0d",
}
REVIEWED_QUESTIONS = (
    "How many pounds of wool enroll there in total?",
    "How much younger earned number than themselves topic?",
    "Compute average age of 11?",
    "How many storerooms does pencils left in total?",
    "How much money does january are left?",
    "How many pounds of papers were bought total on storerooms?",
    "What are the average amount of ball they earning?",
    "How many combined populations do hours left?",
    "How many more topics than numbers did the sticker be?",
    "How many pounds did bird cost in 3 businesses?",
)
POSITIVE_ASKS = (
    (
        "ask/how-many-there-combined",
        "How many pounds of wool are there in total?",
    ),
    (
        "ask/how-much-age-comparative-than",
        "How much younger is Dena than Cato?",
    ),
    (
        "ask/imperative-average-dimension",
        "Compute average age of the 11?",
    ),
    (
        "ask/how-many-plural-combined",
        "How many books do the teachers have in total?",
    ),
    (
        "ask/how-much-money-entity-left",
        "How much money does the teacher have left?",
    ),
    (
        "ask/how-many-passive-combined",
        "How many pounds of paper were bought in total in the storerooms?",
    ),
    (
        "ask/what-average-combined",
        "What is the average number of students they teach?",
    ),
    (
        "ask/how-many-plural-combined-prenominal-marker",
        "How many combined books do the teachers have?",
    ),
    (
        "ask/how-many-more-label-comparative-held",
        "How many more cupboards than tomatoes did Dena have?",
    ),
    (
        "ask/how-many-rate-span",
        "How many apples does Dena eat in 20 minutes?",
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
def test_each_narrowed_ask_remains_strictly_generatable(project, ask_id: str) -> None:
    candidate = generate_ask_scenario(
        project,
        ask_id=ask_id,
        seed=53,
        scenario_mode="ask_only",
    )

    assert _ask_id(candidate.question, project.registry) == ask_id


@pytest.mark.parametrize(
    "question",
    (
        "How many pounds of wool enroll there?",
        "How many books does all boys have in total?",
        "How many books does the three boys have?",
        "How much does january earn in 3 businesses?",
    ),
)
def test_adjacent_legacy_ask_shapes_share_the_modern_boundaries(
    project, question: str
) -> None:
    assert _ask_id(question, project.registry) is None


@pytest.mark.parametrize(
    ("question", "ask_id"),
    (
        (
            "How many pencils could the teacher buy with 10 dollars?",
            "ask/how-many-capacity",
        ),
        (
            "How many minutes would it take Dena to buy 3 apples?",
            "ask/how-many-timeunit-take-span",
        ),
        ("How much does the envelope cost?", "ask/how-much-item-cost"),
        ("How much do the envelopes cost?", "ask/how-much-item-cost"),
        (
            "How much does each head cost?",
            "ask/how-much-each-item-cost",
        ),
        (
            "Compute the age of the teacher?",
            "ask/imperative-single-dimension",
        ),
        (
            "How many fewer hamsters does Mary have than Dena?",
            "ask/how-many-more",
        ),
        (
            "How much more money does Mary have than Dena?",
            "ask/how-much-noun-more-than",
        ),
    ),
)
def test_modernized_legacy_asks_keep_grammatical_controls(
    project, question: str, ask_id: str
) -> None:
    assert _ask_id(question, project.registry) == ask_id


@pytest.mark.parametrize(
    "question",
    (
        "How many pencils should minute buy?",
        "How many minute would it take monday to buy 3 apples?",
        "How much do envelope cost?",
        "How much do each heads cost?",
        "Compute the age of the Wednesday and shopper?",
        "How many younger hamsters does Mary have than Dena?",
        "How much younger money does Mary have than Dena?",
    ),
)
def test_modernized_legacy_asks_reject_old_broad_slot_combinations(
    project, question: str
) -> None:
    assert _ask_id(question, project.registry) is None


def test_legacy_self_comparison_still_routes_to_the_safe_consumer(project) -> None:
    question = "How many fewer hamsters does Mary have than Mary?"

    assert _ask_id(question, project.registry) == "ask/how-many-more"
    answer = solve(question, project.registry).answer
    assert not answer.committed
    assert "self-comparison" in (answer.reason or "")


def test_rejection_only_ask_slots_are_never_generated(project) -> None:
    for ask_id, omitted_slot in (
        ("ask/imperative-combined-dimension", "bare_n"),
        ("ask/imperative-average-dimension", "bare_n"),
        ("ask/imperative-single-dimension", "other"),
    ):
        for seed in range(12):
            candidate = generate_ask_scenario(
                project,
                ask_id=ask_id,
                seed=seed,
                scenario_mode="ask_only",
            )
            assert omitted_slot not in candidate.target_bindings


def test_rejection_only_ask_slot_cannot_be_locked(project) -> None:
    with pytest.raises(GenerationError, match="generation-omitted"):
        generate_ask_scenario(
            project,
            ask_id="ask/imperative-single-dimension",
            seed=53,
            scenario_mode="ask_only",
            locked_bindings={"other": "shopper"},
        )


def test_generation_category_keeps_the_reader_slots_plural_morphology(
    project,
) -> None:
    candidate = generate_ask_scenario(
        project,
        ask_id="ask/how-many-capacity",
        seed=53,
        scenario_mode="ask_only",
    )

    assert _ask_id(candidate.question, project.registry) == "ask/how-many-capacity"
