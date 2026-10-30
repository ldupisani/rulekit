"""G5j: category-generic comparative realization."""

from collections import Counter
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate, list_rule_availability
from rulekit.generation.exploration import exploration_status
from rulekit.generation.sample import _flat_sentence, _leaf_tokens


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"

NEWLY_SUPPORTED = {
    "arithmetic/affine-fraction-as-many",
    "arithmetic/affine-frame-relation-clause",
    "arithmetic/affine-item-relation-clause",
    "arithmetic/affine-times-as-many",
    "arithmetic/affine-times-as-many-possessive-standard",
    "arithmetic/affine-times-as-much",
    "arithmetic/affine-times-as-much-elided",
    "arithmetic/anchored-relation-elided",
    "arithmetic/dangling-comparative-relation",
    "arithmetic/fraction-delta-relation",
    "arithmetic/fraction-delta-relation-elided",
}


def _write_invented_project(root: Path) -> None:
    pack = root / "pack"
    pack.mkdir()
    (root / "project.yaml").write_text(
        """\
format: rulekit/project@1
name: invented-comparative-generation
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
name: invented-comparative
version: 0.1.0
"""
    )
    (pack / "lexicon.yaml").write_text(
        """\
format: rulekit/lexicon@1
entries:
  zigher: {senses: [comparative]}
"""
    )
    (pack / "categories.yaml").write_text(
        """\
format: rulekit/categories@1
categories:
  invented_delta: {parent: comparative}
members:
  invented_delta: [zigher]
"""
    )
    (pack / "rules.yaml").write_text(
        """\
format: rulekit/rules@1
rules:
  - id: invented/comparative
    phase: read
    match:
      sentence:
        - {lit: behold}
        - {slot: dir, cat: invented_delta}
    emits:
      - fact: atom
        entity: sample
        pred: "{dir}"
"""
    )


def test_g5j_profiles_the_complete_comparative_category_class() -> None:
    project = load_project(CURATED)
    occurrences = Counter(
        token.cat
        for rule in project.registry.rules
        for _, token, _ in _leaf_tokens(_flat_sentence(rule) or [])
        if (
            token.cat is not None
            and project.registry.root_sense(token.cat) == "comparative"
        )
    )

    assert occurrences == {
        "less_dir": 2,
        "delta": 6,
        "quantity_delta": 9,
        "count_quantity_delta": 20,
        "mass_quantity_delta": 6,
        "age_comparative": 3,
        "count_intensifier": 1,
        "dimension_comparative": 1,
        "measured_comparative": 2,
        "sequence_growth_descriptor": 1,
        "text_length_comparative": 2,
        "batch_additional_marker": 6,
    }


def test_g5j_unlocks_exactly_the_preregistered_frontier() -> None:
    project = load_project(CURATED)
    availability = {
        item.id: item for item in list_rule_availability(project)
    }

    assert len(availability) == 642
    assert sum(item.supported for item in availability.values()) == 566
    assert sum(not item.supported for item in availability.values()) == 76
    assert availability[
        "arithmetic/dangling-comparative-safety"
    ].blockers == ("declared non-generative safety consumer",)
    assert availability[
        "arithmetic/affine-frame-relation-as-standard"
    ].supported
    assert all(availability[rule_id].supported for rule_id in NEWLY_SUPPORTED)
    assert all(
        "unsupported sense 'comparative'" not in blocker
        for item in availability.values()
        for blocker in item.blockers
    )
    assert len(exploration_status(project)["fillers"]) == 2554


def test_owned_comparative_categories_have_project_backed_fillers() -> None:
    availability = {
        item.id: item
        for item in list_rule_availability(load_project(CURATED))
    }

    assert availability[
        "arithmetic/times-comparative-age-relation"
    ].supported
    assert availability[
        "arithmetic/anchored-relation-postfix-dimension"
    ].supported
    assert "unsupported sense 'comparative'" not in " ".join(
        availability[
            "arithmetic/temporal-offset-age-future-intensified"
        ].blockers
    )


@pytest.mark.parametrize("rule_id", sorted(NEWLY_SUPPORTED))
def test_every_new_comparative_rule_generates_a_reviewable_match(
    rule_id: str,
) -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id=rule_id,
        seed=0,
    )

    assert candidate.generator_version == "g6-strict-boundary-modes"
    assert candidate.target_status == "matched"
    premise = next(
        row
        for row in candidate.premises
        if row.slot_type in {
            "delta",
            "quantity_delta",
            "count_quantity_delta",
            "mass_quantity_delta",
            "measured_comparative",
        }
    )
    assert premise.binding is not None
    assert premise.category_path[-1] == "comparative"
    if premise.slot_type == "count_quantity_delta":
        assert premise.binding in {"fewer", "more"}
        assert premise.category_path[-3:] == (
            "count_quantity_delta",
            "quantity_delta",
            "comparative",
        )
    elif premise.slot_type == "quantity_delta":
        assert premise.binding in {"fewer", "less", "more"}
        assert premise.category_path[-2:] == (
            "quantity_delta",
            "comparative",
        )
    elif premise.slot_type == "mass_quantity_delta":
        assert premise.binding in {"less", "more"}
        assert premise.category_path[-3:] == (
            "mass_quantity_delta",
            "quantity_delta",
            "comparative",
        )
    elif premise.slot_type == "delta":
        assert premise.category_path[-2:] == ("delta", "comparative")
    else:
        assert premise.category_path[-2:] == (
            "measured_comparative",
            "comparative",
        )
    assert {"lexicon", "category-member", "category"} <= {
        source["kind"] for source in premise.sources
    }


@pytest.mark.parametrize(
    "surface",
    ["heavier", "lighter", "longer", "older", "shorter", "younger"],
)
def test_compatible_measured_comparatives_can_be_deliberately_probed(
    surface: str,
) -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id="arithmetic/dangling-comparative-relation",
        seed=517,
        locked_bindings={"dir": surface},
    )

    assert candidate.target_status == "matched"
    assert candidate.requested_bindings["dir"] == surface


def test_comparative_realization_is_category_generic(
    tmp_path: Path,
) -> None:
    _write_invented_project(tmp_path)
    candidate = generate_candidate(
        load_project(tmp_path),
        rule_id="invented/comparative",
        seed=73,
    )

    assert candidate.target_status == "matched"
    assert candidate.requested_bindings == {"dir": "zigher"}
    premise = next(row for row in candidate.premises if row.slot == "dir")
    assert premise.category_path == (
        "zigher",
        "invented_delta",
        "comparative",
    )
