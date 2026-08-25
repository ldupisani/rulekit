"""G5k: sentence-wide absent-category realization."""

from collections import Counter
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import (
    GenerationError,
    generate_candidate,
    list_rule_availability,
)
from rulekit.generation.exploration import exploration_status


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"

NEWLY_SUPPORTED = {
    "arithmetic/anaphoric-multiplier-standard",
    "arithmetic/anaphoric-multiplier-standard-many",
    "arithmetic/anaphoric-multiplier-standard-much",
    "arithmetic/anaphoric-price-standard",
    "arithmetic/existential-premise",
    "arithmetic/existential-premise-bare",
    "arithmetic/existential-premise-bare-conjoined",
    "arithmetic/temporal-offset-age-past",
    "arithmetic/temporal-offset-times-as-old-as-past",
    "arithmetic/times-as-old-as",
}

STILL_BLOCKED = {
    "arithmetic/temporal-offset-age-future",
    "arithmetic/temporal-offset-age-future-intensified",
    "arithmetic/temporal-offset-times-as-old-as-future",
}


def _write_invented_project(root: Path) -> None:
    pack = root / "pack"
    pack.mkdir()
    (root / "project.yaml").write_text(
        """\
format: rulekit/project@1
name: invented-absent-generation
packs: [./pack]
"""
    )
    (root / "generation.yaml").write_text(
        """\
format: rulekit/generation@1
names: [Luma]
"""
    )
    (pack / "pack.yaml").write_text(
        """\
format: rulekit/pack@1
name: invented-absent
version: 0.1.0
"""
    )
    (pack / "lexicon.yaml").write_text(
        """\
format: rulekit/lexicon@1
entries:
  bad: {senses: [noun]}
  safe: {senses: [noun]}
"""
    )
    (pack / "categories.yaml").write_text(
        """\
format: rulekit/categories@1
categories:
  hazard: {parent: noun}
members:
  hazard: [bad]
"""
    )
    (pack / "rules.yaml").write_text(
        """\
format: rulekit/rules@1
rules:
  - id: invented/safe
    phase: read
    match:
      sentence:
        - {slot: item, type: noun}
    where:
      - absent: {cat: hazard}
    emits:
      - fact: atom
        entity: "{item}"
        pred: sampled

  - id: invented/impossible-literal
    phase: read
    match:
      sentence:
        - {lit: bad}
    where:
      - absent: {cat: hazard}
    emits:
      - fact: atom
        entity: bad
        pred: sampled
"""
    )


def test_g5k_profiles_the_complete_absent_predicate_class() -> None:
    project = load_project(CURATED)
    predicates = [
        predicate.absent["cat"]
        for rule in project.registry.rules
        for predicate in rule.where
        if predicate.absent is not None
    ]

    assert len(
        {
            rule.id
            for rule in project.registry.rules
            if any(predicate.absent is not None for predicate in rule.where)
        }
    ) == 21
    assert Counter(predicates) == {
        "aggregate": 4,
        "multiplier_marker": 3,
        "partitive": 6,
        "relational_marker": 6,
        "temporal_marker": 3,
        "conjunction": 2,
        "partition_remnant": 1,
        "sequential_partition_remainder": 1,
    }


def test_g5k_unlocks_exactly_the_preregistered_frontier() -> None:
    project = load_project(CURATED)
    availability = {
        item.id: item for item in list_rule_availability(project)
    }

    assert len(availability) == 156
    assert sum(item.supported for item in availability.values()) == 147
    assert sum(not item.supported for item in availability.values()) == 9
    assert all(availability[rule_id].supported for rule_id in NEWLY_SUPPORTED)
    # G5s subsequently supplied the future-modal domain for this historical
    # G5k frontier, so these rules must remain unlocked.
    assert all(availability[rule_id].supported for rule_id in STILL_BLOCKED)
    assert all(
        "where predicate 'absent'" not in blocker
        for item in availability.values()
        for blocker in item.blockers
    )
    assert len(exploration_status(project)["fillers"]) == 368


@pytest.mark.parametrize("rule_id", sorted(NEWLY_SUPPORTED))
def test_every_new_absent_rule_generates_a_reviewable_match(
    rule_id: str,
) -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id=rule_id,
        seed=0,
    )

    assert candidate.generator_version == "g6-strict-boundary-modes"
    assert candidate.target_status == "matched"
    absent_rows = [
        row
        for row in candidate.premises
        if row.kind == "where" and row.expression.startswith("absent(")
    ]
    assert absent_rows
    assert all(row.status == "passed" for row in absent_rows)
    assert all(
        row.reason.startswith("no analyzed unit belonged to category ")
        for row in absent_rows
    )
    assert all(
        "rule-where" in {source["kind"] for source in row.sources}
        for row in absent_rows
    )


def test_absent_category_filters_broad_domains_and_exploration(
    tmp_path: Path,
) -> None:
    _write_invented_project(tmp_path)
    project = load_project(tmp_path)

    candidate = generate_candidate(
        project,
        rule_id="invented/safe",
        seed=73,
    )
    fillers = {
        item["identity"]: item for item in exploration_status(project)["fillers"]
    }

    assert candidate.target_status == "matched"
    assert candidate.requested_bindings == {"item": "safe"}
    assert set(fillers) == {"safe"}
    with pytest.raises(GenerationError, match="constraints left no filler"):
        generate_candidate(
            project,
            rule_id="invented/safe",
            seed=73,
            max_attempts=2,
            locked_bindings={"item": "bad"},
        )


def test_absent_category_blocks_an_unavoidable_literal(
    tmp_path: Path,
) -> None:
    _write_invented_project(tmp_path)
    availability = {
        item.id: item
        for item in list_rule_availability(load_project(tmp_path))
    }

    assert availability["invented/impossible-literal"].blockers == (
        "no project-backed filler remains for 'bad' outside absent "
        "categories 'hazard'",
    )
