"""Review batch 63: one conjoined anchor owns one holding perspective."""

import json
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.generation.reviews import review_path
from rulekit.kernel.engine import solve


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
GSM8K = ROOT / "projects" / "gsm8k"
RULE_ID = "arithmetic/anchored-relation-conjoined-anchor"
INVALID_REVIEWS = {
    "rev-00d06e034f794475": (
        "The university putting 3 less apricots than toys and currently was "
        "8 toys."
    ),
    "rev-98b79ac055924163": (
        "The librarian bring 80 less vials at the garden than pears and "
        "currently had 0 pears."
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


def test_latest_invalid_reviews_remain_in_the_append_only_ledger(curated) -> None:
    rows = {
        row["id"]: row
        for line in review_path(curated).read_text(encoding="utf-8").splitlines()
        if line.strip()
        for row in [json.loads(line)]
    }

    assert INVALID_REVIEWS.keys() <= rows.keys()
    for review_id, sentence in INVALID_REVIEWS.items():
        assert rows[review_id]["verdict"] == "invalid"
        assert rows[review_id]["target_rule"] == RULE_ID
        assert rows[review_id]["sentence"] == sentence


@pytest.mark.parametrize("sentence", tuple(INVALID_REVIEWS.values()))
def test_reviewed_event_and_nonfinite_surfaces_no_longer_match(
    curated, sentence: str
) -> None:
    assert RULE_ID not in _matched_rules(sentence, curated.registry)


@pytest.mark.parametrize(
    "sentence",
    (
        "Fia has 17 less birds than cats and currently has 4 cats.",
        "Fia has 17 fewer birds than cats and currently had 4 cats.",
        "Fia had 17 fewer birds than cats and currently had 4 cats.",
        "Fia brought 17 fewer birds than cats and still brought 4 cats.",
    ),
)
def test_count_tense_and_holding_negative_neighbours_decline(
    gsm8k, sentence: str
) -> None:
    assert RULE_ID not in _matched_rules(sentence, gsm8k.registry)


@pytest.mark.parametrize(
    "sentence",
    (
        "Fia has 17 fewer birds than cats and currently has 4 cats.",
        "Fia had 17 fewer birds than cats and still had 4 cats.",
        "Fia owns 17 fewer birds than cats and still owns 4 cats.",
        "Fia owned 17 fewer birds than cats and still owned 4 cats.",
        "Fia had 17 fewer birds than cats and had 4 cats.",
    ),
)
def test_present_past_and_unmodified_holding_anchors_remain_supported(
    gsm8k, sentence: str
) -> None:
    assert RULE_ID in _matched_rules(sentence, gsm8k.registry)


def test_adverb_tense_compatibility_is_pack_data(curated, gsm8k) -> None:
    assert curated.registry.adverb_verb_compatibility_pairs(
        "currently", "has"
    ) == (("current_holding_anchor_adverb", "present_possession_state"),)
    assert not curated.registry.adverb_verb_compatibility_pairs(
        "currently", "had"
    )
    assert gsm8k.registry.adverb_verb_compatibility_pairs(
        "still", "had"
    ) == (("flexible_holding_anchor_adverb", "possession_state"),)


def test_strict_generation_respects_the_same_boundaries(curated) -> None:
    for seed in range(16):
        candidate = generate_candidate(curated, rule_id=RULE_ID, seed=seed)
        bindings = candidate.target_bindings

        assert candidate.target_status in {"matched", "shadowed"}
        assert bindings["verb"] == bindings["trailing_verb"]
        assert bindings["dir"].casefold() in {"fewer", "more"}
        if bindings.get("trailing_adv") == "currently":
            assert bindings["trailing_verb"].casefold() in {
                "has",
                "have",
                "own",
                "owns",
            }


def test_new_core_bare_verb_paradigms_carry_number_evidence(curated) -> None:
    lexicon = curated.registry.lexicon

    assert lexicon["bring"].number == "plural"
    assert lexicon["brings"].number == "singular"
    assert lexicon["conduct"].number == "plural"
    assert lexicon["conducts"].number == "singular"
