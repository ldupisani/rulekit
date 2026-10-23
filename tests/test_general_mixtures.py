"""Invented, curated-only composition and conservation examples across materials."""
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import MixtureEvidence


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/curated")).registry


MATERIALS = [
    ("alloy", "tin", "kilograms", "mass"),
    ("bronze", "copper", "grams", "weight"),
    ("cereal", "raisins", "grams", "mass"),
    ("oil blend", "sunflower oil", "kilograms", "mass"),
    ("gas mixture", "helium", "moles", "moles"),
    ("brine", "salt", "liters", "volume"),
    ("resin solution", "resin", "grams", "mass"),
]
SHARES = [
    "The {material} is 20% {component} by {basis}.",
    "The {material} contains 20 percent {component} by {basis}.",
    "The {material} has 20% {component} by {basis}.",
    "The {material} has a {component} content of 20% by {basis}.",
    "The {component} content of the {material} is 20% by {basis}.",
    "20% of the {material} is {component} by {basis}.",
]
ASKS = [
    "How many {unit} of {component} are in the {material}?",
    "How much {component} is in the {material}?",
    "How many {unit} of {component} remain in the {material}?",
]


@pytest.mark.parametrize("material,component,unit,basis", MATERIALS)
@pytest.mark.parametrize("share", SHARES)
@pytest.mark.parametrize("ask", ASKS)
def test_material_independent_paraphrases(reg, material, component, unit, basis, share, ask):
    fields = dict(material=material, component=component, unit=unit, basis=basis)
    text = f"Nora has 50 {unit} of {material}. " + share.format(**fields) + " " + ask.format(**fields)
    result = solve(text, reg)
    assert result.answer.kind == "number", result.answer.reason
    assert result.answer.value == pytest.approx(10)
    shares = [e for e in result.store.by_kind(MixtureEvidence) if e.kind == "share"]
    assert len(shares) == 1 and shares[0].basis


@pytest.mark.parametrize("text,expected", [
    ("Nora has 750 grams of cereal. The cereal is 20% raisins by mass. "
     "How many grams of raisins are in the cereal?", 150),
    ("Nora has 2 kilograms of oil blend. The oil blend contains 15% sunflower oil by mass. "
     "How much sunflower oil is in the oil blend?", .3),
    ("Nora has 10 moles of gas mixture. The gas mixture is 30% helium by moles. "
     "How many moles of helium are in the gas mixture?", 3),
])
def test_component_amounts_across_sample_sizes(reg, text, expected):
    result = solve(text, reg)
    assert result.answer.value == pytest.approx(expected), result.answer.reason


@pytest.mark.parametrize("sample", [
    "The alloy weighs 5 kilograms.",
    "Nora obtained 5 kilograms of alloy.",
    "A tank contains 5 kilograms of alloy.",
])
@pytest.mark.parametrize("ask,expected", [
    ("How many grams of tin are in the alloy?", 600),
    ("What mass of tin is in the alloy?", .6),
    ("What weight of tin remains in the alloy?", .6),
    ("What percentage of the alloy is tin by mass?", 12),
])
def test_mass_quantity_and_percentage_questions(reg, sample, ask, expected):
    result = solve(f"{sample} The alloy contains 12% tin by mass. {ask}", reg)
    assert result.answer.value == pytest.approx(expected), result.answer.reason


@pytest.mark.parametrize("sample", [
    "Nora has 5 kilograms of alloy that is 12% tin by mass.",
    "A tank contains 5 kilograms of alloy which is 12% tin by mass.",
])
def test_relative_composition(reg, sample):
    result = solve(sample + " How many grams of tin are in the alloy?", reg)
    assert result.answer.value == pytest.approx(600), result.answer.reason


RESIN = "Nora has 200 grams of resin solution in ethanol. The resin solution is 15% resin by mass. "


@pytest.mark.parametrize("recovery", [
    "How many grams of resin will be left after all the ethanol is removed without losing resin?",
    "How much resin will remain when the ethanol is removed without losing any resin?",
    "What mass of resin will Nora get after all the ethanol is removed without losing resin?",
    "Nora removes all ethanol from the resin solution without losing resin. How many grams of resin remain in the resin solution?",
])
def test_explicit_nonaqueous_recovery(reg, recovery):
    result = solve(RESIN + recovery, reg)
    assert result.answer.value == pytest.approx(30), result.answer.reason


BLEND = ("A bucket contains 2 kilograms of brine. A tank contains 3 kilograms of brine. "
         "The brine in the bucket is 10% salt by mass. The brine in the tank is 20% salt by mass. ")


@pytest.mark.parametrize("action", [
    "Nora mixes the brine in the bucket with the brine in the tank.",
    "Nora combines the brine in the bucket with the brine in the tank.",
    "The brine in the bucket is mixed with the brine in the tank.",
])
@pytest.mark.parametrize("ask,expected", [
    ("What percentage of the mixture is salt?", 16),
    ("How many grams of salt are in the mixture?", 800),
])
def test_explicit_blending_of_distinct_samples(reg, action, ask, expected):
    result = solve(BLEND + action + " " + ask, reg)
    assert result.answer.value == pytest.approx(expected), result.answer.reason


BASE = "Nora has 2 kilograms of brine. The brine contains 20% salt by mass. "


@pytest.mark.parametrize("action,ask,expected", [
    ("Nora adds 2 kilograms of pure water to the brine.", "What percentage of the brine is salt?", 10),
    ("Nora added 500 grams of pure salt to the brine.", "What percentage of the brine is salt?", 36),
    ("The brine is homogeneous. Nora removes 1 kilogram of brine.", "How many grams of salt remain in the brine?", 200),
    ("The brine is uniform. Nora removed 500 grams of brine.", "What percentage of the brine is salt?", 20),
    ("Nora removes 1 kilogram of water from the brine without losing salt.", "What percentage of the brine is salt?", 40),
    ("Nora removes all water from the brine without losing salt.", "How many grams of salt remain in the brine?", 400),
    ("Nora adds 2 kilograms of pure water to the brine. The brine is homogeneous. Nora removes 1 kilogram of brine.", "How many grams of salt remain in the brine?", 300),
])
def test_ordered_component_accounting(reg, action, ask, expected):
    result = solve(BASE + action + " " + ask, reg)
    assert result.answer.value == pytest.approx(expected), result.answer.reason


def test_volume_addition_requires_explicit_additivity(reg):
    base = "Nora has 2 liters of brine. The brine is 20% salt by volume. "
    action = "Nora adds 2 liters of pure water to the brine. What percentage of the brine is salt?"
    assert not solve(base + action, reg).answer.committed
    answer = solve(base + "Volumes are additive. " + action, reg).answer
    assert answer.value == pytest.approx(10), answer.reason


@pytest.mark.parametrize("text", [
    "Nora has 2 liters of brine. The brine is 20% salt by mass. How many ml of salt are in the brine?",
    "Nora has 2 kilograms of alloy. The alloy is 20% tin by volume. How many grams of tin are in the alloy?",
    "Nora has 2 kilograms of alloy. The alloy is 20% tin by mass. What volume of tin is in the alloy?",
    "Nora has 2 kilograms of alloy. The alloy is 20% tin by mass. How many ml of tin are in the alloy?",
    "Nora has 2 kilograms of alloy. The alloy is 120% tin by mass. How much tin is in the alloy?",
    RESIN + "How much resin will remain when the ethanol evaporates?",
    RESIN + "How much resin will remain when the water is removed without losing resin?",
    RESIN + "How much resin will remain when the ethanol is removed without losing salt?",
    RESIN + "How much resin will remain when some ethanol is removed without losing resin?",
    BASE + "Nora removes 1 kilogram of brine. How much salt is in the brine?",
    BASE + "The brine is homogeneous. Nora removes 3 kilograms of brine. How much salt is in the brine?",
    BASE + "Nora adds 2 kilograms of water to the brine. What percentage of the brine is salt?",
    BASE + "The brine is homogeneous. Nora adds 2 kilograms of pure water to the brine. Nora removes 1 kilogram of brine. How much salt is in the brine?",
    BASE + "Nora removes 2 kilograms of water from the brine without losing salt. How much salt is in the brine?",
    BASE + "Nora removes all water from the brine without losing salt. What percentage of the brine is salt?",
    BLEND + "What percentage of the brine is salt?",
    BLEND + "Nora mixes the brine with the brine. What percentage of the mixture is salt?",
    BLEND + "Nora mixes the brine in the bucket with the brine in the bucket. What percentage of the mixture is salt?",
    BLEND + "Nora mixes the brine in the bucket with the brine in the tank. How much salt is in the brine in the bucket?",
    BLEND.replace("The brine in the tank is 20% salt by mass.", "") + "What percentage of the brine is salt?",
    "Nora has 0 kilograms of alloy. The alloy is 20% tin by mass. What percentage of the alloy is tin?",
    BASE + "Nora has 4 apples. How many apples does Nora have?",
])
def test_precision_boundaries(reg, text):
    assert not solve(text, reg).answer.committed


def test_unspecified_basis_keeps_explicit_elementary_convention(reg):
    result = solve("Nora has 3 liters of brine. The brine is 20% salt. How much salt is in the brine?", reg)
    assert result.answer.value == pytest.approx(.6)
    assert "elementary" in result.answer.reason
    assert next(e for e in result.store.by_kind(MixtureEvidence) if e.kind == "share").basis == ""


def test_labeled_containers_remain_distinct(reg):
    # Write the labels explicitly rather than relying on unqualified tank mentions.
    text = ("Tank A contains 2 kilograms of brine. Tank B contains 3 kilograms of brine. "
            "The brine in tank A is 10% salt by mass. The brine in tank B is 20% salt by mass. "
            "Nora mixes the brine in tank A with the brine in tank B. "
            "What percentage of the mixture is salt?")
    answer = solve(text, reg).answer
    assert answer.value == pytest.approx(16), answer.reason


@pytest.mark.parametrize("holder", ["tank B", "tank"])
def test_unknown_or_ambiguous_labeled_sample_declines(reg, holder):
    prefix = ("Tank A contains 2 kilograms of brine. "
              "The brine in tank A is 20% salt by mass. ")
    if holder == "tank":
        prefix += "Tank B contains 3 kilograms of brine. The brine in tank B is 30% salt by mass. "
    answer = solve(prefix + f"How many grams of salt are in the brine in {holder}?", reg).answer
    assert not answer.committed


@pytest.mark.parametrize("rule_id", [
    "mixture-weighed-sample", "mixture-uniformity", "mixture-blending",
    "mixture-pure-addition", "mixture-proportional-withdrawal",
    "mixture-complete-separation", "mixture-selective-removal",
    "contained-mixture-relative-composition", "mixture-volume-additivity",
    "mixture-passive-blending", "mixture-counted-sample",
])
def test_general_mixture_generated_premises_round_trip(rule_id):
    from rulekit.generation import generate_candidate
    candidate = generate_candidate(load_project(Path("projects/curated")),
                                   rule_id="arithmetic/" + rule_id, seed=281)
    assert candidate.target_status == "matched", candidate
    assert not candidate.deficiencies, candidate.deficiencies
    assert candidate.facts and all(f["type"] == "MixtureEvidence" for f in candidate.facts)


@pytest.mark.parametrize("share", [
    "The bead mixture contains 20% glass beads by count.",
    "The bead mixture is 20% glass beads by count.",
    "20% of the bead mixture is glass beads by count.",
])
def test_count_basis(reg, share):
    result = solve("The bead mixture contains 100 beads. " + share +
                   " How many glass beads are in the bead mixture?", reg)
    assert result.answer.value == pytest.approx(20), result.answer.reason


@pytest.mark.parametrize("text", [
    "The bead mixture contains 3 beads. The bead mixture is 50% glass beads by count. How many glass beads are in the bead mixture?",
    "Nora has 100 grams of bead mixture. The bead mixture is 20% glass beads by mass. How many glass beads are in the bead mixture?",
    "The bead mixture contains 100 beads. The bead mixture is 20% glass beads by mass. How many glass beads are in the bead mixture?",
])
def test_count_basis_cannot_be_mass_or_fractional_items(reg, text):
    assert not solve(text, reg).answer.committed


def test_combination_does_not_inherit_a_source_identity(reg):
    text = ("Nora has 2 kilograms of alloy. The alloy is 10% tin by mass. "
            "Mira has 3 kilograms of bronze. The bronze is 20% tin by mass. "
            "Nora mixes the alloy with the bronze. ")
    assert not solve(text + "How many grams of tin are in the alloy?", reg).answer.committed
    answer = solve(text + "How many grams of tin are in the mixture?", reg).answer
    assert answer.value == pytest.approx(800), answer.reason
