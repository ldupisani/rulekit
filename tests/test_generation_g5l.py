"""G5l: matcher-confirmed omission for unbound optional sentinels."""

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
from rulekit.generation.sample import (
    _flat_sentence,
    _unbound_optional_paths,
)


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"

EXPECTED_PATHS = {
    "arithmetic/group-total-trailing-in-all": {
        (3,): ("collection_seen",),
        (4,): ("partitive_seen",),
    },
    "arithmetic/anchored-relation": {
        (9, 1): ("standard_tail_item",),
        (10,): ("conjunction_seen",),
    },
    "arithmetic/anchored-relation-fully-elided": {
        (4,): ("item_seen",),
    },
    "arithmetic/anaphoric-multiplier-conjunct-many": {
        (8,): ("item2_seen",),
    },
    "arithmetic/anaphoric-multiplier-standard-many": {
        (5,): ("direct_std_seen",),
    },
    "arithmetic/anaphoric-multiplier-standard-much": {
        (5,): ("direct_std_seen",),
    },
    "arithmetic/anaphoric-multiplier-standard-as-many": {
        (5,): ("direct_std_seen",),
        (6,): ("item_std_seen",),
    },
    "arithmetic/anaphoric-multiplier-standard-as-much": {
        (5,): ("direct_std_seen",),
        (6,): ("item_std_seen",),
    },
    "arithmetic/fraction-as-many-elided-standard": {
        (7,): ("std_seen",),
    },
    "arithmetic/fraction-as-much-elided-standard": {
        (7,): ("std_seen",),
    },
    "arithmetic/existential-premise-bare": {
        (4,): ("tail_prep_seen",),
        (5,): ("item2_seen",),
    },
    "arithmetic/percent-change-event": {
        (5,): ("std_seen",),
    },
    "arithmetic/percent-change-event-count": {
        (5,): ("std_seen",),
    },
    "arithmetic/realized-progress-anaphoric-multiplier": {
        (15,): ("standard_seen",),
    },
    "arithmetic/realized-progress-deictic-anaphoric-multiplier": {
        (15,): ("standard_seen",),
    },
    "arithmetic/times-as-many-conjunct-elided-item": {
        (8,): ("item2_seen",),
        (9,): ("std_seen",),
    },
    "arithmetic/times-as-many-conjunct-elided-standard": {
        (9,): ("std_seen",),
    },
    "arithmetic/times-as-many-elided-standard": {
        (7,): ("std_seen",),
    },
    "arithmetic/times-as-much-elided-standard": {
        (7,): ("std_seen",),
    },
}


def _write_invented_project(root: Path) -> None:
    pack = root / "pack"
    pack.mkdir()
    (root / "project.yaml").write_text(
        """\
format: rulekit/project@1
name: invented-unbound-generation
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
name: invented-unbound
version: 0.1.0
"""
    )
    (pack / "lexicon.yaml").write_text(
        """\
format: rulekit/lexicon@1
entries:
  prefix: {senses: [adjective]}
  tail: {senses: [noun]}
"""
    )
    (pack / "rules.yaml").write_text(
        """\
format: rulekit/rules@1
rules:
  - id: invented/nested-unbound
    phase: read
    match:
      sentence:
        - {lit: base}
        - opt:
            - {slot: prefix, type: adjective}
            - opt:
                - {lit: beyond}
                - {slot: tail, type: noun}
    where:
      - unbound: [tail]
    emits:
      - fact: atom
        entity: base
        pred: sampled

  - id: invented/required-unbound
    phase: read
    match:
      sentence:
        - {slot: tail, type: noun}
    where:
      - unbound: [tail]
    emits:
      - fact: atom
        entity: tail
        pred: sampled
"""
    )


def test_g5l_profiles_the_complete_unbound_branch_class() -> None:
    project = load_project(CURATED)
    rules = {
        rule.id: rule
        for rule in project.registry.rules
        if any(predicate.unbound is not None for predicate in rule.where)
    }
    sentinels = Counter(
        name
        for rule in rules.values()
        for predicate in rule.where
        for name in (predicate.unbound or ())
    )

    assert set(rules) == set(EXPECTED_PATHS)
    assert sentinels == {
        "collection_seen": 1,
        "partitive_seen": 1,
        "standard_tail_item": 1,
        "conjunction_seen": 1,
        "direct_std_seen": 4,
        "item_seen": 1,
        "item2_seen": 3,
        "item_std_seen": 2,
        "standard_seen": 2,
        "std_seen": 8,
        "tail_prep_seen": 1,
    }
    assert {
        rule_id: _unbound_optional_paths(
            rule, _flat_sentence(rule) or []
        )
        for rule_id, rule in rules.items()
    } == EXPECTED_PATHS


def test_g5l_unlocks_exactly_the_preregistered_frontier() -> None:
    project = load_project(CURATED)
    availability = {
        item.id: item for item in list_rule_availability(project)
    }

    assert len(availability) == 648
    assert sum(item.supported for item in availability.values()) == 569
    assert sum(not item.supported for item in availability.values()) == 79
    assert all(
        availability[rule_id].supported for rule_id in EXPECTED_PATHS
    )
    assert all(
        "where predicate 'unbound'" not in blocker
        for item in availability.values()
        for blocker in item.blockers
    )
    assert len(exploration_status(project)["fillers"]) == 2554


@pytest.mark.parametrize("rule_id", sorted(EXPECTED_PATHS))
def test_every_unbound_rule_generates_only_its_valid_elided_shape(
    rule_id: str,
) -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id=rule_id,
        seed=0,
    )
    forced_rows = [
        row
        for row in candidate.premises
        if (
            row.slot_type == "optional"
            and "negative-lookahead branch" in row.reason
        )
    ]
    unbound_rows = [
        row
        for row in candidate.premises
        if row.kind == "where" and row.expression.startswith("unbound(")
    ]

    assert candidate.generator_version == "g6-strict-boundary-modes"
    assert candidate.target_status == "matched"
    assert len(forced_rows) == len(EXPECTED_PATHS[rule_id])
    assert all(row.binding == "omitted" for row in forced_rows)
    assert len(unbound_rows) == 1
    assert unbound_rows[0].status == "passed"
    for sentinel in {
        name
        for names in EXPECTED_PATHS[rule_id].values()
        for name in names
    }:
        assert sentinel not in candidate.requested_bindings
        assert sentinel not in candidate.target_bindings
        assert f"{sentinel}=unbound" in unbound_rows[0].binding
        assert repr(sentinel) in unbound_rows[0].reason


def test_nested_unbound_omits_only_the_nearest_branch_and_filters_probes(
    tmp_path: Path,
) -> None:
    _write_invented_project(tmp_path)
    project = load_project(tmp_path)
    candidate = generate_candidate(
        project,
        rule_id="invented/nested-unbound",
        seed=73,
        locked_bindings={"prefix": "prefix"},
    )
    optional_rows = [
        row for row in candidate.premises if row.slot_type == "optional"
    ]
    fillers = {
        item["identity"]: item for item in exploration_status(project)["fillers"]
    }

    assert candidate.target_status == "matched"
    assert candidate.requested_bindings == {"prefix": "prefix"}
    assert [row.binding for row in optional_rows] == ["included", "omitted"]
    assert "negative-lookahead branch" in optional_rows[1].reason
    assert set(fillers) == {"prefix"}
    with pytest.raises(GenerationError, match="requires 'tail' to remain unbound"):
        generate_candidate(
            project,
            rule_id="invented/nested-unbound",
            seed=73,
            max_attempts=2,
            locked_bindings={"tail": "tail"},
        )


def test_unbound_required_slot_remains_honestly_blocked(
    tmp_path: Path,
) -> None:
    _write_invented_project(tmp_path)
    availability = {
        item.id: item
        for item in list_rule_availability(load_project(tmp_path))
    }

    assert availability["invented/required-unbound"].blockers == (
        "unbound slot 'tail' is not confined to optional structure",
    )
