"""Generated-ask review reconciliation: grammar, roles, and evidence scope."""

import json
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import GenerationError, generate_ask_scenario
from rulekit.generation.reviews import review_path
from rulekit.kernel.engine import analyze, solve
from rulekit.kernel.model import GroupTotal, Quantity
from rulekit.kernel.patterns import match_ask


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
GSM8K = ROOT / "projects" / "gsm8k"
REVIEW_IDS = {
    "rev-c09cb9609f9e45c8",
    "rev-cc3b01bf0db049e4",
    "rev-9f4ffd666c1c4bfb",
    "rev-c64b2a36e499492f",
    "rev-d68a069dd56745e0",
    "rev-6f0dc187732c4c83",
}
REVIEWED_SCENARIOS = (
    "Eron has 70 years during the june and thrice that many. "
    "How old did Eron be amid 15 roses?",
    "The university has 6 fewer minutes amidst the violinist than the teacher "
    "and currently was 60 teachers. The september owns 15 fewer minutes. "
    "How many minutes of books in all?",
    "Cato owns 5 hamsters in the friday and twice this many. "
    "Fia owns 50 hamsters and once that many. Mary owns 90 hamsters with the "
    "remainder and thrice this many. "
    "How many hamster do Cato, Fia, and Mary owns average?",
    "The friend finished 90 older students than the pear and currently had 0 "
    "pears. The book owns 50 more students during the october. "
    "How many student altogether?",
    "The area had 3 fewer dollars than the librarian and currently owns 60 "
    "librarians. The march owns 17 more dollars. How many dollar in all?",
    "The child arrives 15 pantries less than her shopper Fia. "
    "Together themselves arrive 60 pantries. "
    "How much pantries does somebody arrived altogether?",
)
MALFORMED_QUESTIONS = (
    "How old did Eron be amid 15 roses?",
    "How many minutes of books in all?",
    "How many hamster do Cato, Fia, and Mary owns average?",
    "How many student altogether?",
    "How many dollar in all?",
    "How much pantries does somebody arrived altogether?",
)


def test_review_evidence_remains_in_the_append_only_ledger() -> None:
    project = load_project(CURATED)
    history = {
        row["id"]: row
        for line in review_path(project).read_text(encoding="utf-8").splitlines()
        if line.strip()
        for row in [json.loads(line)]
    }

    assert REVIEW_IDS <= history.keys()
    assert all(history[review_id]["review_kind"] == "ask" for review_id in REVIEW_IDS)
    assert all(history[review_id]["verdict"] == "invalid" for review_id in REVIEW_IDS)


@pytest.mark.parametrize("question", MALFORMED_QUESTIONS)
def test_reviewed_ask_surfaces_are_no_longer_recognized(question: str) -> None:
    registry = load_project(CURATED).registry

    assert match_ask(analyze(question, registry), registry) is None


@pytest.mark.parametrize("text", REVIEWED_SCENARIOS)
def test_reviewed_scenarios_now_decline(text: str) -> None:
    result = solve(text, load_project(CURATED).registry)

    assert not result.answer.committed


def test_projected_age_requires_a_future_modal_temporal_frame_and_age_unit() -> None:
    result = solve(
        "Eron is 19 years old. How old will Eron be in 15 years?",
        load_project(CURATED).registry,
    )

    assert result.answer.value == 34


def test_combined_named_list_keeps_plural_measure_bare_verb_and_sum_marker() -> None:
    result = solve(
        "Cato owns 5 hamsters. Fia owns 7 hamsters. Mary owns 9 hamsters. "
        "How many hamsters do Cato, Fia, and Mary own together?",
        load_project(CURATED).registry,
    )

    assert result.answer.value == 21


def test_how_much_total_keeps_a_declared_mass_quantity() -> None:
    result = solve(
        "Cato has 5 money. Fia has 7 money. "
        "How much money do they have altogether?",
        load_project(CURATED).registry,
    )

    assert result.answer.value == 12


def test_partitive_ask_requires_a_declared_measure_substance_pair() -> None:
    project = load_project(GSM8K)
    valid = solve(
        "Ravi has 5 pairs of shoes. Nita has 7 pairs of shoes. "
        "How many pairs of shoes do they have in all?",
        project.registry,
    )
    invalid = solve(
        "Ravi has 5 minutes of books. Nita has 7 minutes of books. "
        "How many minutes of books do they have in all?",
        project.registry,
    )

    assert valid.answer.value == 12
    assert not invalid.answer.committed


def test_generator_observes_the_narrowed_ask_contracts() -> None:
    project = load_project(CURATED)
    candidate = generate_ask_scenario(
        project,
        ask_id="ask/how-many-combined-named-list",
        seed=7,
        scenario_mode="ask_only",
        locked_bindings={
            "item": "hamsters",
            "aux": "do",
            "holders": "Cato, Fia, and Mary",
            "verb": "own",
            "agg": "together",
        },
    )

    assert candidate.question == (
        "How many hamsters do Cato, Fia, and Mary own together?"
    )
    with pytest.raises(GenerationError):
        generate_ask_scenario(
            project,
            ask_id="ask/how-much-combined",
            seed=7,
            scenario_mode="ask_only",
            locked_bindings={
                "item": "pantries",
                "aux": "does",
                "who": "somebody",
                "verb": "arrived",
                "agg": "altogether",
            },
        )


def test_non_quantity_arrival_object_produces_no_arithmetic_fact() -> None:
    result = solve(
        "Together themselves arrive 60 pantries.",
        load_project(CURATED).registry,
    )

    assert result.store.by_kind(Quantity) == []
    assert result.store.by_kind(GroupTotal) == []


def test_declined_conjoined_anchor_cannot_leak_an_unrelated_measure() -> None:
    result = solve(
        "The area had 3 fewer dollars than the librarian and currently owns "
        "60 librarians. How many dollars does the area have?",
        load_project(CURATED).registry,
    )

    assert not result.answer.committed
    assert not any(
        quantity.measure == "dollar" and quantity.value == 57
        for quantity in result.store.by_kind(Quantity)
    )


def test_valid_conjoined_measure_anchor_remains_supported() -> None:
    result = solve(
        "Marcus has 3 more ribbons than candles and currently has 7 candles. "
        "How many ribbons does Marcus have?",
        load_project(GSM8K).registry,
    )

    assert result.answer.value == 10


def test_independent_coordinated_relation_clauses_remain_supported() -> None:
    result = solve(
        "Cato has 3 more apples than Fia, and Dena has 2 fewer apples than "
        "Fia. Fia has 10 apples. "
        "How many apples do Cato and Dena have together?",
        load_project(GSM8K).registry,
    )

    assert result.answer.value == 21


def test_irregular_plural_measure_remains_available_to_combined_asks() -> None:
    result = solve(
        "Cato has 20 dice. Fia has twice as many dice as Cato. "
        "How many dice do Cato and Fia have together?",
        load_project(GSM8K).registry,
    )

    assert result.answer.value == 60
