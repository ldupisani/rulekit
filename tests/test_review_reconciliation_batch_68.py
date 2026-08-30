"""Review batch 68: comparative routes, existential tails, and deixis."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.generation.reviews import replay_premise_review
from rulekit.kernel.engine import solve
from rulekit.kernel.facts import Quantity


CURATED = Path(__file__).resolve().parents[1] / "projects" / "curated"


@pytest.fixture(scope="module")
def curated():
    return load_project(CURATED)


def _matched_rules(text: str, registry) -> set[str]:
    result = solve(text, registry)
    return {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


@pytest.mark.parametrize(
    "sentence",
    (
        "The garden was 17 kilograms lighter.",
        "The bowl is 7 pounds heavier.",
        "Bira was 9 years older.",
    ),
)
def test_reviewed_dangling_comparative_controls_stay_supported(
    curated, sentence: str
) -> None:
    assert "arithmetic/dangling-comparative-relation" in _matched_rules(
        sentence, curated.registry
    )


@pytest.mark.parametrize(
    "sentence",
    (
        "Mary was 17 years longer.",
        "The bag is 40 weights heavier.",
    ),
)
def test_dangling_comparative_requires_one_complete_semantic_route(
    curated, sentence: str
) -> None:
    rules = _matched_rules(sentence, curated.registry)
    assert "arithmetic/dangling-comparative-relation" not in rules
    assert "arithmetic/dangling-comparative-safety" in rules


def test_measure_holder_route_uses_the_selected_comparative(curated) -> None:
    registry = curated.registry
    assert registry.measure_applies_to_holder("year", "teacher", "older")
    assert not registry.measure_applies_to_holder(
        "year", "teacher", "longer"
    )
    assert registry.measure_applies_to_holder(
        "kilogram", "garden", "lighter"
    )
    assert registry.measure_applies_to_holder("pound", "bowl", "heavier")


@pytest.mark.parametrize(
    "sentence",
    (
        "There are 6 vessels about the topic.",
        "There was 1 age into the flask.",
        "There were 14 litter on saturday.",
        "There are 16 vessels of cost.",
    ),
)
def test_reviewed_existential_overcommitments_are_rejected(
    curated, sentence: str
) -> None:
    rules = _matched_rules(sentence, curated.registry)
    assert "arithmetic/existential-premise" not in rules
    assert "arithmetic/existential-premise-bare" not in rules


@pytest.mark.parametrize(
    ("sentence", "rule_id"),
    (
        (
            "There are 6 books about the topic.",
            "arithmetic/existential-premise",
        ),
        (
            "There are 6 vessels in the flask.",
            "arithmetic/existential-premise",
        ),
        (
            "There are 30 boxes of apples.",
            "arithmetic/existential-premise-bare",
        ),
    ),
)
def test_declared_existential_attachments_stay_supported(
    curated, sentence: str, rule_id: str
) -> None:
    assert rule_id in _matched_rules(sentence, curated.registry)


def test_valid_container_partitive_retains_only_the_container_count(
    curated,
) -> None:
    result = solve("There are 30 boxes of apples.", curated.registry)
    quantities = list(result.store.by_kind(Quantity))
    assert any(
        quantity.entity == "world"
        and quantity.measure == "box"
        and quantity.value == pytest.approx(30.0)
        for quantity in quantities
    )
    assert not any(quantity.measure == "apple" for quantity in quantities)


def test_external_possessive_is_speech_anchored_not_deficient(curated) -> None:
    sentence = (
        "Aven took 70 minutes to finish my task while the librarian took "
        "90 weeks to finish it."
    )
    result = solve(sentence, curated.registry)

    assert "arithmetic/coordinated-task-completion-durations" in _matched_rules(
        sentence, curated.registry
    )
    assert not any("'my'" in gap for gap in result.deficiencies())


def test_strict_generation_respects_comparative_measure_holder_route(
    curated,
) -> None:
    for seed in range(24):
        candidate = generate_candidate(
            curated,
            rule_id="arithmetic/dangling-comparative-relation",
            seed=seed,
        )
        assert candidate.target_status in {"matched", "shadowed"}
        bindings = candidate.requested_bindings
        assert curated.registry.attribute_applies_to(
            bindings["dir"].casefold(),
            bindings["n"].casefold().split(maxsplit=1)[1],
        )


def test_positive_replay_accepts_a_removed_deficiency(monkeypatch) -> None:
    actual = {
        "target_status": "matched",
        "target_bindings": {"item": "task"},
        "actual_rule_ids": ["arithmetic/example"],
        "facts": [],
        "collisions": [],
        "deficiencies": [],
    }
    candidate = SimpleNamespace(
        target_status="matched",
        collisions=(),
        to_json=lambda: actual,
    )
    monkeypatch.setattr(
        "rulekit.generation.sample.retest_candidate",
        lambda *args, **kwargs: candidate,
    )
    project = SimpleNamespace(
        registry=SimpleNamespace(fingerprint="current")
    )
    review = {
        "target_rule": "arithmetic/example",
        "sentence": "A valid example.",
        "registry_fingerprint": "old",
        "premise_evidence": {
            **actual,
            "deficiencies": ["an obsolete diagnostic"],
        },
    }

    assert replay_premise_review(project, review)["status"] == (
        "machine_reconfirmed"
    )

    actual["deficiencies"] = ["a newly introduced diagnostic"]
    assert replay_premise_review(project, review)["status"] == "regressed"
