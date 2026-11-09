"""G5n: category-generic complementizer realization."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate, list_rule_availability
from rulekit.generation.exploration import exploration_status
from rulekit.generation.sample import _flat_sentence, _leaf_tokens


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"

EXPECTED_OCCURRENCES = {
    "arithmetic/affine-frame-relation": ((11,), ()),
    "arithmetic/fraction-frame-relation": ((8, 0), ((8,),)),
}


def _write_invented_project(root: Path) -> None:
    pack = root / "pack"
    pack.mkdir()
    (root / "project.yaml").write_text(
        """\
format: rulekit/project@1
name: invented-complementizer-generation
packs: [./pack]
"""
    )
    (pack / "pack.yaml").write_text(
        """\
format: rulekit/pack@1
name: invented-complementizer
version: 0.1.0
"""
    )
    (pack / "lexicon.yaml").write_text(
        """\
format: rulekit/lexicon@1
entries:
  zorch: {senses: [complementizer]}
"""
    )
    (pack / "rules.yaml").write_text(
        """\
format: rulekit/rules@1
rules:
  - id: invented/complementizer
    phase: read
    match:
      sentence:
        - {lit: signal}
        - {slot: linker, cat: complementizer}
    emits:
      - fact: atom
        entity: sample
        pred: "{linker}"
"""
    )


def test_g5n_profiles_the_complete_complementizer_category_class() -> None:
    project = load_project(CURATED)
    occurrences = {
        rule.id: (path, optional_ancestors)
        for rule in project.registry.rules
        for path, token, optional_ancestors in _leaf_tokens(
            _flat_sentence(rule) or []
        )
        if (
            token.cat is not None
            and project.registry.root_sense(token.cat) == "complementizer"
        )
    }

    assert occurrences == EXPECTED_OCCURRENCES
    assert project.registry.cat_ancestors("complementizer") == [
        "complementizer"
    ]
    assert [
        surface
        for surface, entry in sorted(project.registry.lexicon.items())
        if (
            "complementizer" in entry.senses
            and project.registry.word_in_category(
                surface, "complementizer"
            )
        )
    ] == ["that"]


def test_g5n_unlocks_exactly_the_preregistered_frontier() -> None:
    project = load_project(CURATED)
    availability = {
        item.id: item for item in list_rule_availability(project)
    }

    assert len(availability) == 934
    assert sum(item.supported for item in availability.values()) == 833
    assert sum(not item.supported for item in availability.values()) == 101
    assert all(
        availability[rule_id].supported
        for rule_id in EXPECTED_OCCURRENCES
    )
    assert all(
        "unsupported sense 'complementizer'" not in blocker
        for item in availability.values()
        for blocker in item.blockers
    )
    assert len(exploration_status(project)["fillers"]) == 2628


@pytest.mark.parametrize("rule_id", sorted(EXPECTED_OCCURRENCES))
def test_every_complementizer_rule_generates_a_reviewable_match(
    rule_id: str,
) -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id=rule_id,
        seed=0,
        locked_bindings={"c": "that"},
    )
    premise = next(row for row in candidate.premises if row.slot == "c")

    assert candidate.generator_version == "g6-strict-boundary-modes"
    assert candidate.target_status == "matched"
    assert premise.binding == "that"
    assert premise.status == "passed"
    assert premise.category_path == ("that", "complementizer")
    assert {"rule-token", "lexicon"} <= {
        source["kind"] for source in premise.sources
    }


def test_optional_complementizer_can_remain_present_or_absent() -> None:
    project = load_project(CURATED)
    included = generate_candidate(
        project,
        rule_id="arithmetic/fraction-frame-relation",
        seed=0,
        locked_bindings={"c": "that"},
    )
    omitted = generate_candidate(
        project,
        rule_id="arithmetic/fraction-frame-relation",
        seed=1,
    )
    included_row = next(row for row in included.premises if row.slot == "c")
    omitted_row = next(row for row in omitted.premises if row.slot == "c")

    assert included.target_status == omitted.target_status == "matched"
    assert (included_row.binding, included_row.status) == ("that", "passed")
    assert (omitted_row.binding, omitted_row.status) == (None, "unverified")


def test_exploration_exposes_both_complementizer_placements() -> None:
    fillers = {
        item["identity"]: item
        for item in exploration_status(load_project(CURATED))["fillers"]
    }
    placements = {
        (placement["rule_id"], placement["slot"])
        for placement in fillers["that"]["placements"]
        if placement["slot"] == "c"
    }

    assert placements == {
        ("arithmetic/affine-frame-relation", "c"),
        ("arithmetic/fraction-frame-relation", "c"),
    }


def test_complementizer_realization_is_category_generic(
    tmp_path: Path,
) -> None:
    _write_invented_project(tmp_path)
    candidate = generate_candidate(
        load_project(tmp_path),
        rule_id="invented/complementizer",
        seed=0,
    )
    premise = next(
        row for row in candidate.premises if row.slot == "linker"
    )

    assert candidate.sentence == "Signal zorch."
    assert candidate.target_status == "matched"
    assert premise.category_path == ("zorch", "complementizer")
    assert {"rule-token", "lexicon"} <= {
        source["kind"] for source in premise.sources
    }
