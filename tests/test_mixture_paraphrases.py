"""Curated-only cross-product of reusable mixture grammar constructions."""
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/curated")).registry


SAMPLES = [
    "Nora collects 3 liters of brine.",
    "Nora collected 3 litres of brine.",
    "Nora has 3 liters of brine in a bucket.",
    "Nora obtained 3 liters of brine.",
]
SHARES = [
    "The brine is 20% salt.",
    "The brine contains 20% salt.",
    "The brine has 20 percent salt.",
    "The brine has 20% salt content.",
    "The brine has a salt content of 20%.",
    "The salt content of the brine is 20%.",
    "20% of the brine is salt.",
    "The brine contains twenty percent salt by volume.",
]
ASKS = [
    ("How many ml of salt will Nora get when the water evaporates?", 600),
    ("How many millilitres of salt will Nora obtain after all the water evaporates?", 600),
    ("How many liters of salt does Nora get after the water evaporates?", 0.6),
    ("How many litres of salt will be left when the water evaporates?", 0.6),
    ("How many liters of salt will remain after the water evaporates?", 0.6),
    ("How many liters of salt are left after the water evaporates?", 0.6),
    ("How much salt will Nora get after the water evaporates?", 0.6),
    ("How much salt will be left when the water completely evaporates?", 0.6),
    ("How much salt will remain after the water fully evaporates?", 0.6),
    ("How much salt in ml will be left after the water evaporates?", 600),
    ("What volume of salt will remain when the water evaporates?", 0.6),
    ("How many ml of salt are in the brine?", 600),
    ("How much salt is in the brine?", 0.6),
    ("What volume of salt is in the brine?", 0.6),
]


@pytest.mark.parametrize("sample", SAMPLES)
@pytest.mark.parametrize("share", SHARES)
@pytest.mark.parametrize("ask, expected", ASKS)
def test_composable_sample_share_and_ask(reg, sample, share, ask, expected):
    result = solve(f"{sample} {share} {ask}", reg)
    assert result.answer.kind == "number", result.answer.reason
    assert result.answer.value == pytest.approx(expected)


@pytest.mark.parametrize("text, expected", [
    ("Nora gets 800 milliliters of saltwater. The saltwater contains 25% salt. "
     "How many liters of salt will remain after the water evaporates?", 0.2),
    ("A tank contains 4 liters of sugar water. The sugar water is 30% sugar by volume. "
     "How many ml of sugar will be left when the water evaporates?", 1200),
    ("Nora has 500 ml of salt water. The salt water has a salt content of 10%. "
     "How much salt will be left after the water evaporates?", 50),
    ("The brine contains 25% salt. Nora collects 4 liters of brine. "
     "How many ml of salt will remain after the water evaporates?", 1000),
    ("Nora collects 3 liters of brine that is 20% salt. "
     "How many ml of salt will remain after the water evaporates?", 600),
    ("Nora collects 5 litres of sugar water which is 12% sugar by volume. "
     "How many milliliters of sugar will be left after the water evaporates?", 600),
    ("Nora collected 4 liters of seawater. If the water contains 15% salt, "
     "how many liters of salt will be left after the water evaporates?", 0.6),
])
def test_material_units_container_relative_clause_and_premise_order(reg, text, expected):
    result = solve(text, reg)
    assert result.answer.kind == "number", result.answer.reason
    assert result.answer.value == pytest.approx(expected)


@pytest.mark.parametrize("share", [
    "The brine contains 120% salt.",
    "The brine contains 20% salt by weight.",
    "The brine does not contain 20% salt.",
    "The brine has a sugar content of 20%.",
    "The salt content of the seawater is 20%.",
    "20% of the brine is water.",
])
@pytest.mark.parametrize("ask", [
    "How many ml of salt will remain after the water evaporates?",
    "How much salt will be left when the water evaporates?",
])
def test_composition_boundaries_survive_alternative_asks(reg, share, ask):
    assert not solve(f"Nora has 3 liters of brine. {share} {ask}", reg).answer.committed


@pytest.mark.parametrize("ending", [
    "some of the water evaporates", "half the water evaporates",
    "20% of the water evaporates", "the water is evaporating",
    "the water does not evaporate", "the sugar evaporates",
])
def test_remaining_does_not_hide_partial_or_wrong_solvent_removal(reg, ending):
    assert not solve(
        "Nora has 3 liters of brine. The brine contains 20% salt. "
        f"How much salt will remain after {ending}?", reg,
    ).answer.committed


@pytest.mark.parametrize("extra", [
    "Nora removes some salt.", "Nora adds water.",
    "Nora collects 3 liters of brine.", "The brine contains 30% salt.",
])
def test_changes_and_competing_evidence_still_decline(reg, extra):
    assert not solve(
        "Nora has 3 liters of brine. The brine contains 20% salt. "
        f"{extra} How much salt will remain after the water evaporates?", reg,
    ).answer.committed


@pytest.mark.parametrize("ending", [
    "the water has evaporated", "all the water has completely evaporated",
    "the water had fully evaporated",
])
def test_completed_perfect_evaporation(reg, ending):
    result = solve(
        "Nora has 3 liters of brine. The brine contains 20% salt. "
        f"How many ml of salt will remain after {ending}?", reg,
    )
    assert result.answer.kind == "number", result.answer.reason
    assert result.answer.value == pytest.approx(600)


@pytest.mark.parametrize("ending", [
    "the water has evaporates", "the water has not evaporated",
    "some water has evaporated", "half the water has evaporated",
])
def test_perfect_does_not_license_invalid_or_partial_removal(reg, ending):
    assert not solve(
        "Nora has 3 liters of brine. The brine contains 20% salt. "
        f"How much salt will remain after {ending}?", reg,
    ).answer.committed


def test_changes_between_prior_composition_and_sampling_decline(reg):
    assert not solve(
        "The brine contains 20% salt. Nora removes some salt. "
        "Nora has 3 liters of brine. "
        "How much salt will remain after the water evaporates?", reg,
    ).answer.committed


def test_negated_relative_composition_declines(reg):
    assert not solve(
        "Nora has 3 liters of brine that is not 20% salt. "
        "How much salt will remain after the water evaporates?", reg,
    ).answer.committed


@pytest.mark.parametrize("rule_id", [
    "arithmetic/measured-mixture-container",
    "arithmetic/measured-mixture-relative-composition",
    "arithmetic/mixture-component-contained-share",
    "arithmetic/mixture-component-content-of-share",
    "arithmetic/mixture-component-content-copular-share",
    "arithmetic/mixture-component-partitive-share",
])
def test_new_constructions_generate_and_round_trip(rule_id):
    from rulekit.generation import generate_candidate

    candidate = generate_candidate(
        load_project(Path("projects/curated")), rule_id=rule_id, seed=281,
    )
    assert candidate.target_status == "matched"
    assert not candidate.deficiencies
    assert candidate.facts
    assert all(fact["type"] == "MixtureEvidence" for fact in candidate.facts)
