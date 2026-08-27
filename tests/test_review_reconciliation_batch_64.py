"""Review batch 64: fractions require a plausible verb/pool frame."""

import json
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import GenerationError, generate_candidate
from rulekit.generation.reviews import review_path
from rulekit.kernel.engine import solve


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
GSM8K = ROOT / "projects" / "gsm8k"
RULE_ID = "arithmetic/fraction-of-pool"
REVIEWS = {
    "rev-a10f6d20d2b64f27": (
        "unclear",
        "Dena adds ninth of the shopper.",
    ),
    "rev-012aa7ce8c9a4dd8": (
        "unclear",
        "Fia began seven tenths of the wednesday.",
    ),
    "rev-77ee099c4b48450a": (
        "invalid",
        "Cato read eight ninths of the pear.",
    ),
    "rev-1e908d458327404f": (
        "invalid",
        "Dena raises four sevenths of the rabbit.",
    ),
    "rev-84be29588dd34a15": (
        "unclear",
        "Aven ate ninth of the rabbit.",
    ),
}


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


def test_latest_fraction_reviews_remain_in_the_append_only_ledger(curated) -> None:
    rows = {
        row["id"]: row
        for line in review_path(curated).read_text(encoding="utf-8").splitlines()
        if line.strip()
        for row in [json.loads(line)]
    }

    assert REVIEWS.keys() <= rows.keys()
    for review_id, (verdict, sentence) in REVIEWS.items():
        assert rows[review_id]["verdict"] == verdict
        assert rows[review_id]["target_rule"] == RULE_ID
        assert rows[review_id]["sentence"] == sentence


@pytest.mark.parametrize(
    "sentence",
    tuple(sentence for _verdict, sentence in list(REVIEWS.values())[:4]),
)
def test_reviewed_role_and_collection_number_failures_no_longer_match(
    curated, sentence: str
) -> None:
    assert RULE_ID not in _matched_rules(sentence, curated.registry)


def test_reader_keeps_the_reviewed_bare_unit_fraction_compatible(curated) -> None:
    # Review feedback deliberately did not justify removing the historical
    # reader surface. Authoring stops producing it, but reading remains broad.
    sentence = REVIEWS["rev-84be29588dd34a15"][1]
    assert RULE_ID in _matched_rules(sentence, curated.registry)


@pytest.mark.parametrize(
    "sentence",
    (
        "Dena adds one ninth of the shoppers.",
        "Dena adds half of the sugar.",
        "Dena adds half of the pear.",
        "Fia began seven tenths of the business.",
        "Cato read eight ninths of the book.",
        "Dena raises four sevenths of the rabbits.",
        "Dena raises half of the money.",
        "Aven ate one ninth of the rabbit.",
    ),
)
def test_plural_collection_material_and_divisible_object_frames_remain_open(
    curated, sentence: str
) -> None:
    assert RULE_ID in _matched_rules(sentence, curated.registry)


def test_role_number_requirements_are_category_owned_data(curated) -> None:
    registry = curated.registry

    assert registry.selectional_role_number(
        "collection_addition_quantity_verb", "theme"
    ) == "plural"
    assert registry.selectional_role_number(
        "livestock_raising_quantity_verb", "theme"
    ) == "plural"
    assert registry.selectional_role_number(
        "material_addition_quantity_verb", "theme"
    ) is None
    assert registry.word_in_category("rabbit", "edible_quantity_object")


def test_extension_owned_transfer_object_uses_the_same_fraction_frame(gsm8k) -> None:
    assert gsm8k.registry.word_in_category(
        "seashell", "transferable_quantity_object"
    )
    assert RULE_ID in _matched_rules(
        "Aven sold half of the seashells.", gsm8k.registry
    )


def test_strict_generation_uses_an_explicit_unit_fraction(curated) -> None:
    bindings = {
        "who": "Aven",
        "verb": "ate",
        "item": "rabbit",
    }
    candidate = generate_candidate(
        curated,
        rule_id=RULE_ID,
        seed=64,
        locked_bindings={**bindings, "f": "one ninth"},
    )

    assert candidate.sentence == "Aven ate one ninth of the rabbit."
    assert candidate.target_status in {"matched", "shadowed"}
    with pytest.raises(GenerationError, match="no filler for f"):
        generate_candidate(
            curated,
            rule_id=RULE_ID,
            seed=64,
            locked_bindings={**bindings, "f": "ninth"},
        )
