"""G5m: exact distinct-measure-key realization."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.data.schemas import MatchToken
from rulekit.generation import (
    GenerationError,
    generate_candidate,
    generate_minimal_pair,
    list_rule_availability,
)
from rulekit.generation.exploration import exploration_status
from rulekit.generation.sample import (
    _Filler,
    _allowed_fillers,
    _distinct_measure_groups,
)


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"

EXPECTED_GROUPS = {
    "arithmetic/anchored-relation": (("item", "std"),),
    "arithmetic/anchored-relation-conjoined-measures": (
        ("item", "std"),
        ("item2", "std"),
    ),
    "arithmetic/anchored-relation-possessive-kinship-standard": (
        ("item", "std"),
    ),
    "arithmetic/anchored-relation-postfix": (("item", "std"),),
}


def _write_invented_project(root: Path) -> None:
    pack = root / "pack"
    pack.mkdir()
    (root / "project.yaml").write_text(
        """\
format: rulekit/project@1
name: invented-distinct-measure-generation
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
name: invented-distinct-measure
version: 0.1.0
"""
    )
    (pack / "lexicon.yaml").write_text(
        """\
format: rulekit/lexicon@1
entries:
  alpha: {senses: [noun]}
  beta: {senses: [noun]}
  gamma: {senses: [noun]}
"""
    )
    (pack / "categories.yaml").write_text(
        """\
format: rulekit/categories@1
categories:
  alpha_only: {parent: noun}
  beta_only: {parent: noun}
members:
  alpha_only: [alpha]
  beta_only: [beta]
"""
    )
    (pack / "rules.yaml").write_text(
        """\
format: rulekit/rules@1
rules:
  - id: invented/distinct-measure
    phase: read
    match:
      sentence:
        - {slot: left, type: noun}
        - {lit: versus}
        - {slot: right, cat: beta_only}
    where:
      - distinct_measure: [left, right]
    emits:
      - fact: atom
        entity: "{left}"
        pred: compared

  - id: invented/impossible-distinct-measure
    phase: read
    match:
      sentence:
        - {slot: left, cat: alpha_only}
        - {lit: versus}
        - {slot: right, cat: alpha_only}
    where:
      - distinct_measure: [left, right]
    emits:
      - fact: atom
        entity: "{left}"
        pred: compared
"""
    )


def test_g5m_profiles_the_complete_distinct_measure_class() -> None:
    project = load_project(CURATED)
    rules = {
        rule.id: rule
        for rule in project.registry.rules
        if any(
            predicate.distinct_measure is not None
            for predicate in rule.where
        )
    }

    assert set(rules) == set(EXPECTED_GROUPS)
    assert sum(len(groups) for groups in EXPECTED_GROUPS.values()) == 5
    assert {
        rule_id: _distinct_measure_groups(rule)
        for rule_id, rule in rules.items()
    } == EXPECTED_GROUPS


def test_g5m_unlocks_exactly_the_preregistered_frontier() -> None:
    project = load_project(CURATED)
    availability = {
        item.id: item for item in list_rule_availability(project)
    }

    assert len(availability) == 95
    assert sum(item.supported for item in availability.values()) == 95
    assert sum(not item.supported for item in availability.values()) == 0
    assert all(
        availability[rule_id].supported for rule_id in EXPECTED_GROUPS
    )
    assert all(
        "where predicate 'distinct_measure'" not in blocker
        for item in availability.values()
        for blocker in item.blockers
    )
    assert len(exploration_status(project)["fillers"]) == 147


@pytest.mark.parametrize("rule_id", sorted(EXPECTED_GROUPS))
def test_every_distinct_measure_rule_generates_exact_distinct_keys(
    rule_id: str,
) -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id=rule_id,
        seed=0,
    )
    rows = [
        row
        for row in candidate.premises
        if (
            row.kind == "where"
            and row.expression.startswith("distinct_measure(")
        )
    ]

    assert candidate.generator_version == "g6-g5u-adverbs"
    assert candidate.target_status == "matched"
    assert len(rows) == len(EXPECTED_GROUPS[rule_id])
    assert all(row.status == "passed" for row in rows)
    assert all("were distinct measure keys" in row.reason for row in rows)
    assert all(
        "rule-where" in {source["kind"] for source in row.sources}
        for row in rows
    )


def test_qualifier_and_label_are_parts_of_the_measure_key(
    tmp_path: Path,
) -> None:
    _write_invented_project(tmp_path)
    project = load_project(tmp_path)
    same = _Filler(
        "red apples",
        "apple",
        label="inventory",
        qualifier="red",
    )
    different_qualifier = _Filler(
        "green apples",
        "apple",
        label="inventory",
        qualifier="green",
    )
    different_label = _Filler(
        "red apples",
        "apple",
        label="shipment",
        qualifier="red",
    )

    allowed = _allowed_fillers(
        MatchToken(slot="right", type="noun"),
        [same, different_qualifier, different_label],
        {"left": same},
        project.registry,
        {},
        {},
        [],
        [],
        [],
        [],
        (("left", "right"),),
        [],
        [],
        (),
    )

    assert allowed == [different_qualifier, different_label]


def test_locked_measure_keys_cannot_collapse_and_probes_stay_realisable(
    tmp_path: Path,
) -> None:
    _write_invented_project(tmp_path)
    project = load_project(tmp_path)
    candidate = generate_candidate(
        project,
        rule_id="invented/distinct-measure",
        seed=73,
        locked_bindings={"left": "alpha", "right": "beta"},
    )
    fillers = {
        item["identity"]: item for item in exploration_status(project)["fillers"]
    }

    assert candidate.target_status == "matched"
    assert candidate.requested_bindings == {
        "left": "alpha",
        "right": "beta",
    }
    assert set(fillers) == {"alpha", "beta", "gamma"}
    assert {
        placement["slot"] for placement in fillers["beta"]["placements"]
    } == {"right"}
    pair = generate_minimal_pair(
        project,
        rule_id="invented/distinct-measure",
        base_seed=74,
        original_bindings=candidate.requested_bindings,
        reroll_slot="left",
    )
    assert pair.target_status == "matched"
    assert pair.requested_bindings == {
        "left": "gamma",
        "right": "beta",
    }
    with pytest.raises(GenerationError, match="constraints left no filler"):
        generate_candidate(
            project,
            rule_id="invented/distinct-measure",
            seed=73,
            max_attempts=2,
            locked_bindings={"left": "beta", "right": "beta"},
        )


def test_impossible_measure_key_domain_remains_honestly_blocked(
    tmp_path: Path,
) -> None:
    _write_invented_project(tmp_path)
    availability = {
        item.id: item
        for item in list_rule_availability(load_project(tmp_path))
    }

    assert availability["invented/impossible-distinct-measure"].blockers == (
        "no project-backed distinct measure assignment exists for left/right",
    )
