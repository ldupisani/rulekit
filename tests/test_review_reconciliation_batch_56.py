"""Generated-ask review reconciliation: complete noun phrases and roles."""

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
    "rev-ef482ff2b2b74098",
    "rev-69054edc764f4826",
    "rev-49def8aadbe945eb",
    "rev-74bdb8af1c7e45a8",
    "rev-03d2fe12e0dc4863",
    "rev-a951a8dda347467a",
    "rev-0b229fc50e604df8",
    "rev-5059d68598c74c27",
    "rev-da37de65df254ef5",
    "rev-d59711ecf9eb406f",
    "rev-eb7c22d6e28d4f58",
    "rev-32ddc3a11c014d71",
    "rev-f1dac6561b214554",
    "rev-7fe5f1d70bc34ec6",
    "rev-aee0f236dbe94eed",
}
REVIEWED_QUESTIONS = (
    "How many would John left?",
    "How much clay does his lose combined?",
    "How much wool did Mary and Bira enroll in total?",
    "How much money does anything spend in total?",
    "How many more pounds of paper did Fia arrive than John?",
    "How many dogs do all of them cost combined?",
    "How much paper does my have combined?",
    "What is area of Mary in 16?",
    "How many times did all 18 students have?",
    "How much clay did him buy together?",
    "How many pounds of sand eat there?",
    "What is area of John in 30?",
    "Is Eron population?",
    "How many coins do all 1 bird own?",
    "Is Eron pantry?",
)
POSITIVE_ASKS = (
    ("ask/how-many-entity-elided-measure", "How many would John have?"),
    ("ask/how-much-combined", "How much clay do they have combined?"),
    (
        "ask/how-much-combined-named",
        "How much clay did Mary and Bira have in total?",
    ),
    (
        "ask/how-many-more-partitive",
        "How many more pounds of paper did Fia buy than John?",
    ),
    (
        "ask/how-many-all-combined",
        "How many dogs do all of them have combined?",
    ),
    (
        "ask/reference-attribute-year",
        "What is the area of Japan in 2020?",
    ),
    (
        "ask/how-many-plural-combined-cardinal-subject",
        "How many coins do all 2 birds own?",
    ),
    ("ask/how-many-there", "How many pounds of sand are there?"),
    ("ask/is-membership", "Is Eron a teacher?"),
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


@pytest.mark.parametrize(("ask_id", "question"), POSITIVE_ASKS)
def test_repaired_asks_keep_grammatical_positive_controls(
    project, ask_id: str, question: str
) -> None:
    assert _ask_id(question, project.registry) == ask_id


@pytest.mark.parametrize("ask_id", sorted({row[0] for row in POSITIVE_ASKS}))
def test_repaired_asks_remain_strictly_generatable(project, ask_id: str) -> None:
    for seed in range(3):
        candidate = generate_ask_scenario(
            project,
            ask_id=ask_id,
            seed=seed,
            scenario_mode="ask_only",
        )
        assert _ask_id(candidate.question, project.registry) == ask_id


def test_cardinal_subject_generation_requires_a_real_group(project) -> None:
    for seed in range(8):
        candidate = generate_ask_scenario(
            project,
            ask_id="ask/how-many-plural-combined-cardinal-subject",
            seed=seed,
            scenario_mode="ask_only",
        )
        assert int(candidate.target_bindings["who"].split()[0]) >= 2


def test_reference_year_generation_uses_complete_lookup_grammar(project) -> None:
    candidate = generate_ask_scenario(
        project,
        ask_id="ask/reference-attribute-year",
        seed=56,
        scenario_mode="ask_only",
    )

    assert candidate.question.startswith("What is the ")
    assert 1000 <= int(candidate.target_bindings["y"]) <= 9999


def test_membership_generation_always_contains_an_indefinite_article(project) -> None:
    for seed in range(6):
        candidate = generate_ask_scenario(
            project,
            ask_id="ask/is-membership",
            seed=seed,
            scenario_mode="ask_only",
        )
        assert " a " in candidate.question.casefold()
