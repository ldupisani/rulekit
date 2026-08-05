"""Additive comparisons whose standard, or standard and measure, are elided."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import AnchorQuantity, Quantity, Relation


CURATED = Path(__file__).resolve().parents[1] / "projects" / "curated"
STATED_MEASURE_RULE = "arithmetic/anchored-relation-elided-standard"
FULLY_ELIDED_RULE = "arithmetic/anchored-relation-fully-elided"


def _matched_rules(result, sentence: int = 1) -> set[str]:
    return {
        match.match.rule.id
        for match in result.document.rule_results.get(sentence, [])
    }


def _derived_quantities(result) -> list[Quantity]:
    return [
        fact
        for fact in result.store.by_kind(Quantity)
        if fact.provenance.source == "synth/relation"
    ]


def test_additive_measure_and_standard_elision_resolves_unique_prior_quantity(
    registry,
) -> None:
    result = solve(
        "Vela has 3 apples. Neris has 5 more. "
        "How many apples does Neris have?",
        registry,
    )

    assert result.answer.value == 8
    assert _matched_rules(result) == {FULLY_ELIDED_RULE}
    relation = next(
        fact
        for fact in result.store.by_kind(Relation)
        if fact.provenance.source == FULLY_ELIDED_RULE
    )
    assert relation.standard == "$elided:standard$"
    assert relation.measure is None
    assert any(
        quantity.entity == "neris"
        and quantity.measure == "apple"
        and quantity.value == 8
        for quantity in _derived_quantities(result)
    )
    assert result.store.by_kind(AnchorQuantity) == []


def test_additive_standard_elision_keeps_the_stated_measure(registry) -> None:
    result = solve(
        "Vela has 3 apples. Neris has 5 more apples. "
        "How many apples does Neris have?",
        registry,
    )

    assert result.answer.value == 8
    assert _matched_rules(result) == {STATED_MEASURE_RULE}


def test_additive_standard_elision_observes_singular_number(registry) -> None:
    result = solve(
        "Vela has 3 apples. Neris has 1 more apple. "
        "How many apples does Neris have?",
        registry,
    )

    assert result.answer.value == 4
    assert STATED_MEASURE_RULE in _matched_rules(result)
    mismatch = solve(
        "Vela has 3 apples. Neris has 1 more apples. "
        "How many apples does Neris have?",
        registry,
    )
    assert STATED_MEASURE_RULE not in _matched_rules(mismatch)
    assert mismatch.answer.kind == "decline"


def test_fewer_uses_the_same_elided_antecedent_path(registry) -> None:
    result = solve(
        "Vela has 8 apples. Neris has 5 fewer. "
        "How many apples does Neris have?",
        registry,
    )

    assert result.answer.value == 3
    assert FULLY_ELIDED_RULE in _matched_rules(result)


def test_negative_elided_result_declines(registry) -> None:
    result = solve(
        "Vela has 3 apples. Neris has 5 fewer. "
        "How many apples does Neris have?",
        registry,
    )

    assert result.answer.kind == "decline"
    assert _derived_quantities(result) == []


def test_fully_elided_relation_without_an_antecedent_declines(registry) -> None:
    result = solve(
        "Neris has 5 more. How many apples does Neris have?",
        registry,
    )

    assert result.answer.kind == "decline"
    assert FULLY_ELIDED_RULE in _matched_rules(result, sentence=0)
    assert _derived_quantities(result) == []


def test_fully_elided_relation_with_two_prior_quantities_declines(
    registry,
) -> None:
    result = solve(
        "Vela has 3 apples. Orin has 4 balls. Neris has 5 more. "
        "How many apples does Neris have?",
        registry,
    )

    assert result.answer.kind == "decline"
    assert _derived_quantities(result) == []


def test_stated_measure_filters_the_prior_quantity_candidates(registry) -> None:
    result = solve(
        "Vela has 3 apples. Orin has 4 balls. "
        "Neris has 5 more apples. How many apples does Neris have?",
        registry,
    )

    assert result.answer.value == 8
    assert STATED_MEASURE_RULE in _matched_rules(result, sentence=2)


def test_stated_measure_with_two_prior_holders_declines(registry) -> None:
    result = solve(
        "Vela has 3 apples. Orin has 4 apples. "
        "Neris has 5 more apples. How many apples does Neris have?",
        registry,
    )

    assert result.answer.kind == "decline"
    assert _derived_quantities(result) == []


def test_self_mention_is_not_an_elided_standard(registry) -> None:
    result = solve(
        "Vela has 3 apples. Vela has 5 more. "
        "How many apples does Vela have?",
        registry,
    )

    assert _derived_quantities(result) == []


@pytest.mark.parametrize(
    "sentence",
    [
        "Vela has 3 apples. Vela buys 5 more apples. ",
        "Vela has 3 apples. Vela buys 5 more. ",
        "Vela bought 3 apples. Neris bought 5 more. ",
        "Vela has 3 apples. Neris is 5 more apples. ",
        "Vela has 3 apples. Neris is 5 more. ",
    ],
)
def test_event_changes_are_not_claimed_as_elided_comparisons(
    sentence: str, registry
) -> None:
    result = solve(
        sentence + "How many apples does Vela have?",
        registry,
    )
    matched = {
        rule_id
        for sentence_index in result.document.rule_results
        for rule_id in _matched_rules(result, sentence=sentence_index)
    }

    assert STATED_MEASURE_RULE not in matched
    assert FULLY_ELIDED_RULE not in matched


@pytest.mark.parametrize(
    ("sentence", "existing_rule"),
    [
        ("Neris has 5 more than Vela.", "arithmetic/anchored-relation-elided"),
        ("Neris has 5 more apples than Vela.", "arithmetic/anchored-relation"),
    ],
)
def test_fuller_explicit_surfaces_are_not_claimed_by_elided_rules(
    sentence: str, existing_rule: str, registry
) -> None:
    result = solve(
        f"Vela has 3 apples. {sentence} "
        "How many apples does Neris have?",
        registry,
    )
    rules = _matched_rules(result)

    assert result.answer.value == 8
    assert existing_rule in rules
    assert STATED_MEASURE_RULE not in rules
    assert FULLY_ELIDED_RULE not in rules


@pytest.mark.parametrize(
    ("rule_id", "has_unbound"),
    [(STATED_MEASURE_RULE, False), (FULLY_ELIDED_RULE, True)],
)
def test_additive_elided_rules_generate_matcher_confirmed_specimens(
    rule_id: str, has_unbound: bool,
) -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id=rule_id,
        seed=0,
    )

    assert candidate.target_status == "matched"
    assert rule_id in {match.rule_id for match in candidate.actual_matches}
    unbound = [
        premise
        for premise in candidate.premises
        if premise.kind == "where" and premise.expression.startswith("unbound(")
    ]
    assert len(unbound) == int(has_unbound)
    assert all(premise.status == "passed" for premise in unbound)
