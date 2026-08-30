"""Review batch 66: grammatical generation and positive semantic roles."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import TotalityTransfer


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
GSM8K = ROOT / "projects" / "gsm8k"


@pytest.fixture(scope="module")
def curated():
    return load_project(CURATED)


@pytest.fixture(scope="module")
def gsm8k():
    return load_project(GSM8K)


def _matched_rules(text: str, registry) -> set[str]:
    result = solve(text, registry)
    return {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


@pytest.mark.parametrize(
    ("span", "article"),
    (("hour", "an"), ("year", "a")),
)
def test_wage_generation_chooses_the_natural_indefinite_allomorph(
    curated, span: str, article: str
) -> None:
    candidate = generate_candidate(
        curated,
        rule_id="arithmetic/activity-scoped-wage-rate",
        seed=66,
        locked_bindings={"span": span},
    )

    assert f" {article} {span} " in candidate.sentence.casefold()


@pytest.mark.parametrize(
    "sentence",
    (
        "Cato makes 80 dollars a hour for babysitting.",
        "Aven earns 8 dollars an year for gardening.",
    ),
)
def test_reviewed_article_mismatches_remain_readable(curated, sentence: str) -> None:
    assert "arithmetic/activity-scoped-wage-rate" in _matched_rules(
        sentence, curated.registry
    )


def test_price_anaphor_preserves_reviewed_reading_but_generates_agreement(
    curated,
) -> None:
    rule_id = "arithmetic/anaphoric-price-standard"
    assert rule_id in _matched_rules("Area are triple that cost.", curated.registry)

    candidate = generate_candidate(
        curated,
        rule_id=rule_id,
        seed=66,
        locked_bindings={"who": "area"},
    )
    assert candidate.requested_bindings["verb"] in {"is", "was", "costs"}


@pytest.mark.parametrize(
    "sentence",
    (
        "Bottle says thrice the amount of marbles into my garden as bag.",
        "Head conducted double the amount of benches as their parent Dena.",
        "Puzzle knows twice the amount of numbers during october as your violinist Eron.",
    ),
)
def test_number_of_frame_requires_a_positive_quantity_verb(
    curated, sentence: str
) -> None:
    assert "arithmetic/times-the-number-of" not in _matched_rules(
        sentence, curated.registry
    )


def test_number_of_frame_keeps_compatible_quantity_events(curated) -> None:
    sentence = "The teacher has twice the amount of students as the university."
    assert "arithmetic/times-the-number-of" in _matched_rules(
        sentence, curated.registry
    )


def test_number_of_frame_treats_catching_as_quantitative_acquisition(gsm8k) -> None:
    result = solve(
        "Cato catches twice the amount of rabbits as Dena who caught 2. "
        "Eron catches three times the amount of rabbits as Cato. "
        "How many rabbits did Eron catch?",
        gsm8k.registry,
    )

    assert result.answer.value == pytest.approx(12.0)


def test_fraction_as_many_rejects_unlicensed_participial_event(curated) -> None:
    sentence = (
        "The teacher checking three fourths as many shoppers into your vessel "
        "as the barrel."
    )
    assert "arithmetic/fraction-as-many" not in _matched_rules(
        sentence, curated.registry
    )


def test_fraction_as_many_keeps_compatible_quantity_event(curated) -> None:
    sentence = "The teacher ate three fourths as many apples as the child."
    assert "arithmetic/fraction-as-many" in _matched_rules(
        sentence, curated.registry
    )


@pytest.mark.parametrize("seeker", ("wallet", "shoe"))
def test_capacity_goal_common_noun_seeker_must_be_animate(
    curated, seeker: str
) -> None:
    sentence = (
        f"The {seeker} intended to know how many animals he might fit into "
        "the bag."
    )
    assert "arithmetic/container-capacity-inquiry-frame" not in _matched_rules(
        sentence, curated.registry
    )


@pytest.mark.parametrize("seeker", ("the brother", "Bira"))
def test_capacity_goal_keeps_people_and_proper_names(curated, seeker: str) -> None:
    sentence = (
        f"{seeker} intends to know how many pages she might fit into a storeroom."
    )
    assert "arithmetic/container-capacity-inquiry-frame" in _matched_rules(
        sentence, curated.registry
    )


@pytest.mark.parametrize(
    "rule_id",
    (
        "arithmetic/container-package-groups-totality-transfer",
        "arithmetic/container-package-contents-totality-transfer",
    ),
)
def test_package_totality_generation_supplies_matching_package_context(
    curated, rule_id: str
) -> None:
    candidate = generate_candidate(curated, rule_id=rule_id, seed=66)
    package = candidate.requested_bindings["packages"].casefold()

    assert len(candidate.context_before) == 1
    assert package in candidate.context_before[0].casefold()
    assert candidate.target_status in {"matched", "shadowed"}
    if "item" in candidate.requested_bindings:
        assert (
            candidate.requested_bindings["item"].casefold()
            in candidate.context_before[0].casefold()
        )


@pytest.mark.parametrize(
    "transfer",
    (
        "she puts both beakers of coins in the jar",
        "she puts both bags of cards in the jar",
    ),
)
def test_explicit_package_transfer_must_match_prior_package_and_content(
    curated, transfer: str
) -> None:
    result = solve(
        "Bira is wondering how many coins she can fit in a jar. "
        "She buys 4 large bags with 25 coins, and 3 small bags of 10 coins. "
        f"If {transfer}, how many coins does the jar contain?",
        curated.registry,
    )
    assert not result.answer.committed


def test_explicit_package_transfer_preserves_surface_roles_without_amount(
    curated,
) -> None:
    result = solve(
        "Bira is wondering how many coins she can fit in a jar. "
        "She buys 4 large bags with 25 coins, and 3 small bags of 10 coins. "
        "If she puts both bags of coins in the jar, "
        "how many coins does the jar contain?",
        curated.registry,
    )
    transfers = list(result.store.by_kind(TotalityTransfer))

    assert result.answer.value == pytest.approx(130.0)
    assert len(transfers) == 1
    assert transfers[0].package == "bag"
    assert transfers[0].content == "coin"
