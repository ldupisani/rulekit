"""Invented equal-part projections, distinct from observed completion."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_ask_scenario, generate_candidate
from rulekit.kernel.engine import diagnose, solve
from rulekit.kernel.model import BatchEvidence, Rate


@pytest.fixture(scope="module")
def project():
    return load_project(Path("projects/curated"))


def portion_question(policy="If she can eat the rest of the pizza at the same pace, ", *, equal=True):
    adjective = "equal " if equal else ""
    return (f"Fia eats a pizza cut into six {adjective}pieces. "
            "She finished the first piece in four minutes. " + policy
            + "How long would it take to eat the whole pizza?")


POLICIES = [
    "If she can eat the rest of the pizza at the same pace, ",
    "Assuming she can eat the rest of the pizza at the same pace, ",
    "She can eat the rest of the pizza at the same pace. ",
]


@pytest.mark.parametrize("policy", POLICIES)
def test_missing_equal_sizes_is_semantic_evidence_not_a_grammar_deficiency(project, policy):
    result = solve(portion_question(policy, equal=False), project.registry)
    assert result.answer.kind == "decline"
    assert "not stated to be equal in size" in result.answer.reason
    assert result.deficiencies() == []
    assert diagnose(result)["kind"] == "insufficient"
    proof = result.answer.proof
    assert proof.steps[0].rule == "missing-equal-part-sizes"
    assert dict(proof.steps[0].conclusion.fields)["established"] is False
    assert len(proof.steps[0].evidence) == 3


@pytest.mark.parametrize("policy", POLICIES)
def test_explicit_equal_sizes_support_all_three_continuation_forms(project, policy):
    result = solve(portion_question(policy), project.registry)
    assert result.value == 24
    assert result.deficiencies() == []
    assert result.answer.proof.steps[0].rule == "equal-parts-unchanged-rate"
    assert "Projected" in result.answer.reason
    assert len(result.assumptions) == (0 if policy.startswith("She") else 1)
    continuation = next(r for r in result.store.by_kind(BatchEvidence)
                        if r.kind == "uniform-rate-continuation")
    assert continuation.provenance.assumption == bool(result.assumptions)
    assert not list(result.store.by_kind(Rate))
    # The measured part remains the only observed duration.
    assert [r.kind for r in result.store.by_kind(BatchEvidence)].count("process-part-duration") == 1


@pytest.mark.parametrize("before,after,expected", [
    ("whole pizza?", "rest of the pizza?", 20),
    ("How long", "How many seconds", 1440),
    ("How long", "How long in hours", 0.4),
    ("would it", "will it", 24),
    ("would it", "would Fia", 24),
    ("same pace", "same speed", 24),
    ("same pace", "same rate", 24),
    ("can eat", "could eat", 24),
    ("whole pizza", "entire pizza", 24),
    ("whole pizza", "full pizza", 24),
    ("six equal pieces", "six equal red pieces", 24),
    ("pizza cut", "cake sliced", 24),
])
def test_projection_paraphrases_and_units(project, before, after, expected):
    text = portion_question().replace(before, after)
    # Preserve the whole's identity when varying the opening's vocabulary.
    if before == "pizza cut":
        text = text.replace("pizza", "cake")
    result = solve(text, project.registry)
    assert result.value == pytest.approx(expected), result.answer.reason
    assert result.deficiencies() == []


def project_question():
    return ("Cato's project was divided into five equal parts. "
            "He finished the first part of his project in 12 minutes. "
            "Assuming he can finish the rest of his project at the same pace, "
            "how long would it take to finish the whole project?")


@pytest.mark.parametrize("before,after,expected", [
    ("project", "project", 60),
    ("project", "task", 60),
    ("whole project?", "rest of the project?", 48),
    ("how long", "how many hours", 1),
    ("was divided into", "had", 60),
])
def test_generic_process_partition_reuses_observed_part_and_duration_models(project, before, after, expected):
    result = solve(project_question().replace(before, after), project.registry)
    assert result.value == expected, result.answer.reason
    assert result.deficiencies() == []


@pytest.mark.parametrize("before,after", [
    ("six equal pieces", "six pieces"),
    ("six equal pieces", "six large pieces"),
    ("six equal pieces", "six unequal pieces"),
    ("six equal pieces", "six overlapping pieces"),
    ("six equal pieces", "6.5 equal pieces"),
    ("six equal pieces", "one equal piece"),
    ("first piece", "second piece"),
    ("first piece", "first slice"),
    ("four minutes", "zero minutes"),
    ("four minutes", "at most four minutes"),
    ("She finished", "Cato finished"),
    ("If she can", "If Cato can"),
    ("rest of the pizza at", "rest of the cake at"),
    ("can eat", "might eat"),
    ("can eat", "should eat"),
    ("can eat", "cannot eat"),
    ("can eat", "can not eat"),
    ("same pace", "faster pace"),
    ("whole pizza?", "whole cake?"),
    ("would it take to eat", "did it take to eat"),
    ("would it take to eat", "would it take to buy"),
    ("would it", "would Cato"),
    ("four minutes.", "four minutes. She has two apples."),
    ("Fia eats", "Fia buys"),
    ("Fia eats", "Fia's eats"),
])
def test_projection_requires_consistent_scope_and_explicit_rate_policy(project, before, after):
    assert not solve(portion_question().replace(before, after), project.registry).answer.committed


def test_one_timed_part_alone_never_establishes_a_rate(project):
    result = solve(portion_question(policy=""), project.registry)
    assert not result.answer.committed
    assert "does not establish a constant rate" in result.answer.reason
    # A prior hypothetical solve cannot supply the missing policy.
    assert solve(portion_question(), project.registry).value == 24
    assert not solve(portion_question(policy=""), project.registry).answer.committed


def test_assumption_is_visible_in_the_cli_trace(project, monkeypatch, capsys):
    from types import SimpleNamespace
    from rulekit import cli

    monkeypatch.setattr(cli, "_registry", lambda args: (project, project.registry))
    assert cli.cmd_solve(SimpleNamespace(text=portion_question(), reference_year=None,
                                        json=False, trace=True)) == 0
    output = capsys.readouterr().out
    assert "number: 24" in output
    assert "question-assumption" in output


def test_core_arithmetic_pack_combination_has_no_physics_dependency():
    from rulekit.data.packs import load_packs
    from rulekit.data.registry import compile_registry

    registry = compile_registry(load_packs([Path("packs/core-english"), Path("packs/arithmetic")]))
    assert solve(portion_question(), registry).value == 24


@pytest.mark.parametrize("replacement", [
    "Assuming she might eat the rest of the pizza at the same pace, ",
    "Assuming she can eat the rest of the cake at the same pace, ",
    "Assuming she can eat the rest of the pizza at the same pace and Cato has two apples, ",
])
def test_participial_introducer_cannot_hide_unlicensed_or_unread_conditions(project, replacement):
    result = solve(portion_question(replacement), project.registry)
    assert not result.answer.committed


@pytest.mark.parametrize("rule_id", [
    "arithmetic/partitioned-activity-opening",
    "arithmetic/component-part-duration",
    "arithmetic/unchanged-rate-continuation",
])
def test_new_premise_grammars_round_trip_through_generation(project, rule_id):
    candidate = generate_candidate(project, rule_id=rule_id, seed=4500)
    assert candidate.target_status == "matched"
    if rule_id.endswith("continuation"):
        assert candidate.context_before


@pytest.mark.parametrize("scope", ["whole", "remaining"])
@pytest.mark.parametrize("suffix", ["", "-unit", "-named"])
def test_projected_duration_asks_round_trip_and_compose(project, scope, suffix):
    locks = {"modal": "would", "take": "take", "inf": "to", "activity": "eat",
             "whole": "the whole pizza" if scope == "whole" else "the pizza"}
    if suffix == "-unit":
        locks["unit"] = "minutes"
    else:
        locks["long"] = "long"
    if suffix == "-named":
        locks["who"] = "Fia"
    else:
        locks["dummy"] = "it"
    if scope == "remaining":
        locks["rest"] = "the rest"
    candidate = generate_ask_scenario(
        project, ask_id=f"ask/projected-{scope}-duration{suffix}", seed=231,
        scenario_mode="ask_only", locked_bindings=locks)
    assert candidate.consumer == "uniform-partition-duration"
    premises = portion_question(POLICIES[2]).rsplit("How long", 1)[0]
    result = solve(premises + candidate.question, project.registry)
    assert result.value == (24 if scope == "whole" else 20), result.answer.reason
    assert result.deficiencies() == []
