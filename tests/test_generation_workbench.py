"""G1 generation is deterministic, honest about blockers, and firewalled."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from rulekit.data.project import load_project
from rulekit.generation import (
    ReviewRecord,
    append_review,
    delete_review,
    generate_candidate,
    list_rule_availability,
    read_reviews,
    update_review,
)
from rulekit.generation.reviews import _raw_reviews, review_path


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


def _review(candidate, verdict: str = "unclear", note: str = "") -> ReviewRecord:
    return ReviewRecord(
        candidate_id=candidate.id,
        sentence=candidate.sentence,
        target_rule=candidate.target_rule,
        seed=candidate.seed,
        registry_fingerprint=candidate.registry_fingerprint,
        verdict=verdict,
        note=note,
    )


def _seeded(tmp_path: Path):
    _write_project(tmp_path)
    project = load_project(tmp_path)
    candidate = generate_candidate(project, rule_id="invented/simple", seed=5)
    return project, candidate


def test_editing_a_review_supersedes_without_destroying_the_original(
    tmp_path: Path,
) -> None:
    project, candidate = _seeded(tmp_path)
    first = append_review(project, _review(candidate, "unclear", "unsure"))

    corrected = update_review(project, first["id"], "invalid", "decided")

    live = read_reviews(project)
    assert [r["id"] for r in live] == [corrected["id"]]
    assert live[0]["verdict"] == "invalid"
    assert live[0]["note"] == "decided"
    assert corrected["supersedes"] == first["id"]
    # the ledger keeps both rows: the correction is an APPEND, not a rewrite
    raw = _raw_reviews(project)
    assert [r["id"] for r in raw] == [first["id"], corrected["id"]]
    assert raw[0]["verdict"] == "unclear"


def test_editing_preserves_what_was_actually_reviewed(tmp_path: Path) -> None:
    project, candidate = _seeded(tmp_path)
    first = append_review(project, _review(candidate, "valid"))

    corrected = update_review(project, first["id"], "invalid", "")

    # only the human judgment may move; the reviewed artefact stays pinned
    for field in ("candidate_id", "sentence", "target_rule", "seed",
                  "registry_fingerprint"):
        assert corrected[field] == first[field]


def test_deleting_a_review_appends_a_tombstone(tmp_path: Path) -> None:
    project, candidate = _seeded(tmp_path)
    first = append_review(project, _review(candidate, "valid"))

    delete_review(project, first["id"])

    assert read_reviews(project) == []
    raw = _raw_reviews(project)
    assert len(raw) == 2
    assert raw[0]["verdict"] == "valid"  # original untouched on disk
    assert raw[1]["tombstones"] == first["id"]


def test_an_edited_review_can_still_be_deleted(tmp_path: Path) -> None:
    """The tombstone must target the live row, not the spent original."""

    project, candidate = _seeded(tmp_path)
    first = append_review(project, _review(candidate, "unclear"))
    corrected = update_review(project, first["id"], "valid", "")

    delete_review(project, corrected["id"])

    assert read_reviews(project) == []
    assert len(_raw_reviews(project)) == 3


def test_a_superseded_review_cannot_be_edited_or_deleted(tmp_path: Path) -> None:
    """Otherwise a stale designer tab would resurrect a spent verdict."""

    project, candidate = _seeded(tmp_path)
    first = append_review(project, _review(candidate, "unclear"))
    update_review(project, first["id"], "valid", "")

    with pytest.raises(KeyError):
        update_review(project, first["id"], "invalid", "")
    with pytest.raises(KeyError):
        delete_review(project, first["id"])
    with pytest.raises(KeyError):
        delete_review(project, "rev-does-not-exist")


def test_rows_written_before_ids_existed_stay_addressable(tmp_path: Path) -> None:
    """Legacy history predates the id field; folding must not orphan it."""

    _write_project(tmp_path)
    project = load_project(tmp_path)
    path = review_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '{"candidate_id": "gen-legacy", "note": "", "project": "p", "seed": 1,'
        ' "registry_fingerprint": "abcdef0123456789",'
        ' "sentence": "A synthetic legacy row.", "target_rule": "probe/rule",'
        ' "timestamp": "2026-01-01T00:00:00+00:00", "verdict": "unclear"}\n',
        encoding="utf-8",
    )

    live = read_reviews(project)
    assert len(live) == 1
    legacy_id = live[0]["id"]
    # the derived id must be stable across reads, or edits would miss it
    assert read_reviews(project)[0]["id"] == legacy_id

    update_review(project, legacy_id, "valid", "triaged")
    assert [r["verdict"] for r in read_reviews(project)] == ["valid"]


def test_history_limit_counts_live_reviews_not_spent_corrections(
    tmp_path: Path,
) -> None:
    project, candidate = _seeded(tmp_path)
    kept = append_review(project, _review(candidate, "valid"))
    noisy = append_review(project, _review(candidate, "unclear"))
    for _ in range(5):
        noisy = update_review(project, noisy["id"], "unclear", "again")

    live = read_reviews(project, limit=2)
    assert {r["id"] for r in live} == {kept["id"], noisy["id"]}


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
