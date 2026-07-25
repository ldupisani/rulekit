"""G1 generation is deterministic, honest about blockers, and firewalled."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from rulekit.data.project import load_project
from rulekit.generation import (
    ReviewRecord,
    append_review,
    generate_candidate,
    list_rule_availability,
    read_reviews,
)


def _write_project(root: Path) -> None:
    pack = root / "pack"
    pack.mkdir(parents=True)
    (root / "project.yaml").write_text(
        """\
format: rulekit/project@1
name: invented-generation
packs: [./pack]
"""
    )
    (root / "generation.yaml").write_text(
        """\
format: rulekit/generation@1
names: [Luma, Navo, Pera]
"""
    )
    (pack / "pack.yaml").write_text(
        """\
format: rulekit/pack@1
name: invented
version: 0.1.0
"""
    )
    (pack / "lexicon.yaml").write_text(
        """\
format: rulekit/lexicon@1
entries:
  dax: {senses: [verb]}
  jel: {senses: [adjective]}
  miv: {senses: [noun], plural: mivs}
  zor: {senses: [noun], plural: zors}
"""
    )
    (pack / "categories.yaml").write_text(
        """\
format: rulekit/categories@1
categories:
  invented_action: {parent: verb}
members:
  invented_action: [dax]
"""
    )
    (pack / "rules.yaml").write_text(
        """\
format: rulekit/rules@1
rules:
  - id: invented/simple
    phase: read
    description: a flat invented premise
    match:
      sentence:
        - {slot: who, type: name}
        - {slot: verb, cat: invented_action}
        - {slot: item, type: noun}
    emits:
      - fact: predication
        subject: "{who}"
        verb: "{verb}"
        dobj: "{item}"

  - id: invented/condensed
    phase: read
    match:
      sentence:
        - {slot: quality, type: adjective}
        - {slot: item, type: noun}
    emits:
      - fact: predication
        subject: "{item}"
        verb: quality
        dobj: "{quality}"

  - id: invented/span
    phase: read
    match:
      sentence:
        - {lit: vek}
        - {slot: phrase, span: true}
    emits:
      - fact: atom
        entity: sample
        pred: example
"""
    )


def test_same_seed_is_identical_across_fresh_project_loads(tmp_path: Path) -> None:
    _write_project(tmp_path)

    first = generate_candidate(
        load_project(tmp_path), rule_id="invented/simple", seed=8128
    )
    second = generate_candidate(
        load_project(tmp_path), rule_id="invented/simple", seed=8128
    )

    assert first.to_json() == second.to_json()
    assert first.target_status == "matched"
    assert first.target_rule in {
        match.rule_id for match in first.actual_matches
    }
    assert first.sentence.endswith(".")
    assert first.facts


def test_every_rule_is_listed_and_unsupported_rules_name_the_blocker(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    availability = {
        rule.id: rule
        for rule in list_rule_availability(load_project(tmp_path))
    }

    assert set(availability) == {
        "invented/simple",
        "invented/condensed",
        "invented/span",
    }
    assert availability["invented/simple"].supported
    assert availability["invented/condensed"].supported
    assert not availability["invented/span"].supported
    assert "span capture is deferred beyond G1" in availability[
        "invented/span"
    ].blockers


def test_failed_round_trip_remains_an_inspectable_candidate(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)

    candidate = generate_candidate(
        load_project(tmp_path),
        rule_id="invented/condensed",
        seed=3,
        max_attempts=2,
    )

    assert candidate.sentence == "Jel zor."
    assert candidate.target_status == "absent"
    assert candidate.target_bindings == {}
    assert candidate.attempts == 2


def test_seeded_random_rule_selection_is_reproducible(tmp_path: Path) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)

    assert generate_candidate(project, seed=21).to_json() == generate_candidate(
        load_project(tmp_path), seed=21
    ).to_json()


def test_reviews_can_only_use_the_fixed_project_path(tmp_path: Path) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)
    candidate = generate_candidate(
        project, rule_id="invented/simple", seed=5
    )
    review = ReviewRecord(
        candidate_id=candidate.id,
        sentence=candidate.sentence,
        target_rule=candidate.target_rule,
        seed=candidate.seed,
        registry_fingerprint=candidate.registry_fingerprint,
        verdict="invalid",
        note="The premise is deliberately under review.",
    )

    durable = append_review(project, review)

    path = tmp_path / "generation" / "reviews.jsonl"
    assert path.exists()
    assert read_reviews(project) == [durable]
    with pytest.raises(ValidationError):
        ReviewRecord.model_validate(
            {
                **review.model_dump(),
                "path": str(tmp_path / "elsewhere.jsonl"),
            }
        )
    assert not (tmp_path / "elsewhere.jsonl").exists()


def test_designer_exposes_the_generation_review_loop() -> None:
    root = Path("src/rulekit/server/static")
    html = (root / "index.html").read_text()
    js = (root / "app.js").read_text()

    assert 'id="view-generate"' in html
    assert 'id="generation-rule"' in html
    assert 'data-verdict="valid"' in html
    assert 'data-verdict="invalid"' in html
    assert 'data-verdict="unclear"' in html
    assert "/api/generation/candidate" in js
    assert "/api/generation/review" in js
