"""Review-led subject boundary for leading GroupTotal premises.

Synthetic examples pin the general split: named/action subjects retain scoped
totals, while existential ``there`` requires an agreeing copula and emits an
unscoped holding total.
"""

import json
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import (
    GenerationError,
    generate_candidate,
    list_rule_availability,
    retest_candidate,
)
from rulekit.generation.reviews import review_path
from rulekit.kernel.engine import solve
from rulekit.kernel.model import GroupTotal


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
REVIEW_ID = "rev-f18095e000a9418b"
SCOPED_RULES = {
    "arithmetic/group-total-leading",
    "arithmetic/group-total-leading-marker",
}
EXISTENTIAL_RULES = {
    "arithmetic/group-total-leading-existential",
    "arithmetic/group-total-leading-marker-existential",
}
BOUNDARY_RULES = SCOPED_RULES | EXISTENTIAL_RULES


def _matches(text: str, registry) -> set[str]:
    result = solve(text, registry)
    return {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


def _totals(text: str, registry) -> list[GroupTotal]:
    return solve(text, registry).store.by_kind(GroupTotal)


def test_review_evidence_is_preserved_and_now_retests_absent() -> None:
    project = load_project(CURATED)
    history = [
        json.loads(line)
        for line in review_path(project).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    review = next(
        item for item in history if item["id"] == REVIEW_ID
    )

    assert review["sentence"] == "Altogether there drops 2 coins."
    assert review["verdict"] == "invalid"
    assert review["target_rule"] == (
        "arithmetic/group-total-leading-marker"
    )

    retest = retest_candidate(
        project,
        rule_id=review["target_rule"],
        sentence=review["sentence"],
        seed=review["seed"],
        requested_bindings=review["requested_bindings"],
    )
    assert retest.target_status == "absent"
    assert not (BOUNDARY_RULES & _matches(review["sentence"], project.registry))
    assert not any(fact["type"] == "GroupTotal" for fact in retest.facts)


@pytest.mark.parametrize(
    ("text", "rule_id", "scope", "verb"),
    [
        (
            "In total they sold 12 coins.",
            "arithmetic/group-total-leading",
            "they",
            "sell",
        ),
        (
            "Together they sold 12 coins.",
            "arithmetic/group-total-leading-marker",
            "they",
            "sell",
        ),
        (
            "Total blue has 40 birds.",
            "arithmetic/group-total-leading-marker",
            "blue",
            "have",
        ),
    ],
)
def test_action_and_named_group_totals_remain_scoped(
    text: str, rule_id: str, scope: str, verb: str
) -> None:
    project = load_project(CURATED)
    totals = _totals(text, project.registry)

    assert _matches(text, project.registry) & BOUNDARY_RULES == {rule_id}
    assert len(totals) == 1
    assert totals[0].scope == scope
    assert totals[0].verb == verb


@pytest.mark.parametrize(
    ("text", "rule_id", "measure", "value"),
    [
        (
            "In total there are 12 coins.",
            "arithmetic/group-total-leading-existential",
            "coin",
            12,
        ),
        (
            "Altogether there is 1 coin.",
            "arithmetic/group-total-leading-marker-existential",
            "coin",
            1,
        ),
        (
            "Combined there were 8 birds.",
            "arithmetic/group-total-leading-marker-existential",
            "bird",
            8,
        ),
    ],
)
def test_existential_group_totals_are_unscoped_holdings(
    text: str, rule_id: str, measure: str, value: float
) -> None:
    project = load_project(CURATED)
    totals = _totals(text, project.registry)

    assert _matches(text, project.registry) & BOUNDARY_RULES == {rule_id}
    assert len(totals) == 1
    assert totals[0].measure == measure
    assert totals[0].value == value
    assert totals[0].scope is None
    assert totals[0].verb == "have"


@pytest.mark.parametrize(
    "text",
    [
        "In total there is 2 coins.",
        "In total there are 1 coin.",
        "Together there drops 2 coins.",
        "Average there are 2 coins.",
    ],
)
def test_existential_total_requires_agreement_copula_and_totality_marker(
    text: str,
) -> None:
    registry = load_project(CURATED).registry

    assert not (BOUNDARY_RULES & _matches(text, registry))
    assert not _totals(text, registry)


def test_scope_split_rules_remain_realisable_after_g5j_expansion() -> None:
    availability = {
        item.id: item
        for item in list_rule_availability(load_project(CURATED))
    }

    assert len(availability) == 95
    assert sum(item.supported for item in availability.values()) == 95
    assert all(availability[rule_id].supported for rule_id in BOUNDARY_RULES)


@pytest.mark.parametrize("rule_id", sorted(EXISTENTIAL_RULES))
def test_existential_rules_generate_agreeing_unscoped_totals(
    rule_id: str,
) -> None:
    project = load_project(CURATED)

    for seed in range(24):
        candidate = generate_candidate(project, rule_id=rule_id, seed=seed)
        assert candidate.target_status == "matched"
        assert candidate.generator_version == "g6-reviewed-premise-boundaries"
        assert candidate.requested_bindings["verb"] in {
            "is",
            "are",
            "was",
            "were",
        }
        fact = next(
            fact for fact in candidate.facts if fact["type"] == "GroupTotal"
        )
        assert "scope" not in fact["fields"]
        assert fact["fields"]["verb"] == "have"
        assert not candidate.sentence.startswith("Average ")


@pytest.mark.parametrize("rule_id", sorted(SCOPED_RULES))
def test_scoped_generator_cannot_bind_existential_there(
    rule_id: str,
) -> None:
    project = load_project(CURATED)

    with pytest.raises(GenerationError):
        generate_candidate(
            project,
            rule_id=rule_id,
            seed=91,
            max_attempts=1,
            locked_bindings={"who": "there"},
        )

    candidate = generate_candidate(
        project,
        rule_id=rule_id,
        seed=91,
        max_attempts=1,
        locked_bindings={
            "who": "they",
            "verb": "sold",
            "item": "2 coins",
        },
    )
    exclusion = next(
        premise
        for premise in candidate.premises
        if "slot_not_category" in premise.expression
    )
    assert exclusion.status == "passed"
    assert exclusion.reason == (
        "who='they' was not in category 'existential'"
    )
