"""Synthetic measured-mixture component and complete solvent-removal cases."""
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import analyze, solve


@pytest.fixture(scope="module", params=["curated", "gsm8k"])
def reg(request):
    return load_project(Path("projects") / request.param).registry


def story(sample="Mira collects 3 liters of brine.", share="The brine is 15% salt.",
          ask="How many milliliters of salt will Mira get when all the water evaporates?"):
    return f"{sample} {share} {ask}"


@pytest.mark.parametrize("text, expected", [
    (story(), 450),
    (story(share="The water is 15% salt."), 450),
    (story(share="The brine is 25% sugar.", ask="How many ml of sugar will Mira get when all the water evaporates?"), 750),
    (story(sample="Mira has 800 milliliters of brine.", ask="How many liters of salt are in the brine?"), 0.12),
    (story(ask="How many milliliters of salt are in the brine?"), 450),
    (story(share="The brine is 0% salt."), 0),
    (story(share="The brine is 100% salt."), 3000),
    ("Jack is stranded on an island. He collects 4 liters of brine in a bucket. "
     "If the brine is 30% sugar, how many ml of sugar will Jack get when all the water evaporates?", 1200),
])
def test_component_volume(reg, text, expected):
    result = solve(text, reg)
    assert result.answer.kind == "number", result.answer.reason
    assert result.answer.value == pytest.approx(expected)


@pytest.mark.parametrize("text", [
    story(share="The brine is 115% salt."),
    story(share="The brine is 15% salt. She removes some salt."),
    story(share="The brine is 15% salt. She drinks the brine."),
    story(share="She adds water. The brine is 15% salt."),
    story(share="The seawater is 15% salt."),
    story(share="The brine is not 15% salt."),
    story(share="The brine is 15% salt by weight."),
    story(sample="Mira collects 3 kilograms of brine."),
    story(sample="Mira wants 3 liters of brine."),
    story(sample="Mira collects 3 liters of brine. Mira collects 3 liters of brine."),
    story(share="The brine is 15% salt. The brine is 25% salt."),
    story(share="The brine is 15% salt. Mira loses 1 liter of brine."),
    story(ask="How many ml of salt will Nora get when all the water evaporates?"),
    story(ask="How many ml of salt will Mira get when some water evaporates?"),
    story(ask="How many ml of salt will Mira get when all the salt evaporates?"),
    story(ask="How many grams of salt will Mira get when all the water evaporates?"),
    story(ask="How many ml of sugar will Mira get when all the water evaporates?"),
    story(ask="How many ml of water will Mira get when all the water evaporates?"),
    story(ask="How many ml of salt are in the seawater?"),
])
def test_unsupported_or_ambiguous_mixtures_decline(reg, text):
    assert not solve(text, reg).answer.committed


@pytest.mark.parametrize("text, sense", [
    ("Jack is stranded.", "name"),
    ("A jack is old.", "noun"),
    ("The Jack is old.", "noun"),
    ("jack is old.", "noun"),
    ("Jacks are old.", "noun"),
])
def test_declared_name_noun_homograph(reg, text, sense):
    reading = analyze(text, reg)
    unit = next(u for u in reading.units if u.features.get("lemma") == "jack")
    assert unit.sense() == sense


def test_other_consumers_cannot_ignore_mixture_evidence(reg):
    result = solve(
        "Mira collects 3 liters of brine. The brine is 15% salt. "
        "Mira has 5 apples. How many apples does Mira have?", reg,
    )
    assert not result.answer.committed
    assert "mixture amount or share was not used" in result.answer.reason


def test_background_vocabulary_is_shared(reg):
    result = solve(
        "Mira is stranded on a desert island. She wants salt to season her fish. "
        "She collects 5 liters of brine in a bucket. "
        "If the water is 12% salt, how many ml of salt will Mira get "
        "when all the water evaporates?", reg,
    )
    assert result.answer.kind == "number", result.answer.reason
    assert result.answer.value == pytest.approx(600)
    assert not result.deficiencies()



@pytest.mark.parametrize("ending", ["the water evaporates", "all the water evaporates"])
def test_completed_evaporation_does_not_require_explicit_totality(reg, ending):
    result = solve(
        "Mira wants some salt. She collects 4 liters of brine. "
        "If the water is 15% salt, how many ml of salt will Mira get "
        f"when {ending}?", reg,
    )
    assert result.answer.kind == "number", result.answer.reason
    assert result.answer.value == pytest.approx(600)


@pytest.mark.parametrize("ending", [
    "some water evaporates", "half the water evaporates",
    "20% of the water evaporates", "the water does not evaporate",
    "the water is evaporating",
])
def test_partial_negated_or_ongoing_evaporation_does_not_license_recovery(reg, ending):
    result = solve(story(ask=f"How many ml of salt will Mira get when {ending}?"), reg)
    assert not result.answer.committed


@pytest.mark.parametrize("unit, expected", [("liters", 0.6), ("ml", 600)])
@pytest.mark.parametrize("totality", ["", "all "])
def test_component_left_after_evaporation(reg, unit, expected, totality):
    result = solve(story(ask=(
        f"How many {unit} of salt will be left when {totality}the water evaporates?"
    ), sample="Mira collects 4 liters of brine."), reg)
    assert result.answer.kind == "number", result.answer.reason
    assert result.answer.value == pytest.approx(expected)


@pytest.mark.parametrize("ask", [
    "How many liters of salt will be left when some water evaporates?",
    "How many liters of salt will be left when half the water evaporates?",
    "How many liters of salt will not be left when the water evaporates?",
    "How many liters of water will be left when the water evaporates?",
    "How many liters of sugar will be left when the water evaporates?",
    "How many grams of salt will be left when the water evaporates?",
])
def test_residue_ask_preserves_recovery_boundaries(reg, ask):
    assert not solve(story(ask=ask), reg).answer.committed


@pytest.mark.parametrize("component", ["salt", "sugar"])
@pytest.mark.parametrize("source", ["brine", "water"])
@pytest.mark.parametrize("verb", ["has", "had"])
def test_component_content_percentage(reg, component, source, verb):
    result = solve(
        "Nora wants some salt. She collects 5 liters of brine. "
        f"If the {source} {verb} 12% {component} content, how many liters "
        f"of {component} will be left when the water evaporates?", reg,
    )
    assert result.answer.kind == "number", result.answer.reason
    assert result.answer.value == pytest.approx(0.6)
    assert not result.deficiencies()


@pytest.mark.parametrize("share", [
    "The water has 120% salt content.",
    "The water does not have 15% salt content.",
    "The water has 15% content.",
    "The water has 15% salt content by weight.",
    "The seawater has 15% salt content.",
    "The water has 15% sugar content.",
])
def test_content_share_retains_component_identity_and_boundaries(reg, share):
    assert not solve(story(share=share), reg).answer.committed


def test_component_content_generation_round_trips():
    from rulekit.generation import generate_candidate

    candidate = generate_candidate(
        load_project(Path("projects/curated")),
        rule_id="arithmetic/mixture-component-content-share", seed=281,
        locked_bindings={"composition": "salt content"},
    )
    assert candidate.target_status == "matched"
    assert not candidate.deficiencies
    assert len(candidate.facts) == 1
    assert candidate.facts[0]["type"] == "MixtureEvidence"
    assert candidate.facts[0]["fields"]["component"] == "salt"
