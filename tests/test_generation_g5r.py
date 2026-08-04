"""G5r: core ownership of generic dimension comparatives."""

from dataclasses import fields, replace
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.data.registry import compile_registry
from rulekit.data.schemas import CategoriesDoc
from rulekit.generation import generate_candidate, list_rule_availability
from rulekit.generation.exploration import exploration_status


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
GSM8K = ROOT / "projects" / "gsm8k"

MORE = {"heavier", "higher", "larger", "longer", "taller", "wider"}
LESS = {"lighter", "shorter", "smaller"}
MOVED_WORDS = MORE | LESS
MOVED_MEMBERS = {
    "dimension_more": sorted(MORE),
    "dimension_less": sorted(LESS),
    "linear_dimension_comparative": sorted(
        {"higher", "larger", "longer", "taller", "wider", "shorter", "smaller"}
    ),
    "mass_dimension_comparative": ["heavier", "lighter"],
    "duration_dimension_comparative": ["longer", "shorter"],
}
CORE_MEMBERSHIPS = {
    word: tuple(
        sorted(category for category, words in MOVED_MEMBERS.items() if word in words)
    )
    for word in MOVED_WORDS
}


def _without_moved_members(doc: CategoriesDoc) -> CategoriesDoc:
    members = {
        category: [
            word
            for word in words
            if word not in MOVED_MEMBERS.get(category, ())
        ]
        for category, words in doc.members.items()
    }
    return doc.model_copy(update={"members": members})


def test_dimension_comparatives_and_signed_memberships_share_ownership() -> None:
    project = load_project(CURATED)
    core = next(pack for pack in project.packs if pack.name == "core-english")
    expected_source = (
        ROOT / "packs/core-english/lexicon/core.yaml"
    ).resolve()

    assert MOVED_WORDS <= set(core.lexicon)
    assert {
        project.source_index.lexicon[word].path.resolve()
        for word in MOVED_WORDS
    } == {expected_source}
    assert all(
        project.registry.word_categories[word] == CORE_MEMBERSHIPS[word]
        for word in MOVED_WORDS
    )
    assert project.registry.category_polarity["dimension_more"] == 1
    assert project.registry.category_polarity["dimension_less"] == -1


def test_combined_pack_semantics_are_identical_to_legacy_ownership() -> None:
    project = load_project(GSM8K)
    core, arithmetic, mined = project.packs
    legacy_core = replace(
        core,
        lexicon={
            word: entry
            for word, entry in core.lexicon.items()
            if word not in MOVED_WORDS
        },
        lexicon_sources={
            word: path
            for word, path in core.lexicon_sources.items()
            if word not in MOVED_WORDS
        },
        categories=[
            _without_moved_members(doc) for doc in core.categories
        ],
    )
    legacy_mined = replace(
        mined,
        lexicon={
            **mined.lexicon,
            **{word: core.lexicon[word] for word in MOVED_WORDS},
        },
        lexicon_sources={
            **mined.lexicon_sources,
            **{
                word: core.lexicon_sources[word]
                for word in MOVED_WORDS
            },
        },
        categories=[
            *mined.categories,
            CategoriesDoc.model_validate(
                {
                    "format": "rulekit/categories@1",
                    "members": MOVED_MEMBERS,
                }
            ),
        ],
    )
    legacy = compile_registry([legacy_core, arithmetic, legacy_mined])
    compared_fields = {
        field.name
        for field in fields(project.registry)
        if field.name != "fingerprint"
    }

    assert {
        name
        for name in compared_fields
        if getattr(project.registry, name) != getattr(legacy, name)
    } == set()
    for word in MORE - {"wider"}:
        assert set(project.registry.word_categories[word]) == {
            *CORE_MEMBERSHIPS[word],
            "higher",
        }
    assert project.registry.word_categories["wider"] == CORE_MEMBERSHIPS["wider"]
    for word in LESS:
        assert set(project.registry.word_categories[word]) == {
            *CORE_MEMBERSHIPS[word],
            "lower",
        }


def test_g5r_unlocks_exactly_the_preregistered_rule() -> None:
    project = load_project(CURATED)
    availability = {
        item.id: item for item in list_rule_availability(project)
    }

    assert len(availability) == 101
    assert sum(item.supported for item in availability.values()) == 101
    assert sum(not item.supported for item in availability.values()) == 0
    assert availability[
        "arithmetic/anchored-relation-postfix-dimension"
    ].supported
    assert availability[
        "arithmetic/anchored-relation-conjoined-anchor"
    ].supported
    assert len(exploration_status(project)["fillers"]) == 152


@pytest.mark.parametrize("comparative", sorted(MOVED_WORDS))
def test_every_dimension_comparative_generates_a_matcher_confirmed_specimen(
    comparative: str,
) -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id="arithmetic/anchored-relation-postfix-dimension",
        seed=0,
        locked_bindings={"dir": comparative},
    )
    premise = next(row for row in candidate.premises if row.slot == "dir")
    direct = "dimension_more" if comparative in MORE else "dimension_less"

    assert candidate.generator_version == "g6-reviewed-premise-boundaries"
    assert candidate.target_status == "matched"
    assert premise.binding == comparative
    assert premise.status == "passed"
    assert premise.category_path == (
        comparative,
        direct,
        "dimension_comparative",
        "comparative",
    )
    assert {
        "rule-token",
        "lexicon",
        "category-member",
        "category",
    } <= {source["kind"] for source in premise.sources}


def test_exploration_exposes_all_dimension_comparatives_on_the_new_rule() -> None:
    fillers = {
        item["identity"]: item
        for item in exploration_status(load_project(CURATED))["fillers"]
    }

    for comparative in MOVED_WORDS:
        placements = {
            (placement["rule_id"], placement["slot"])
            for placement in fillers[comparative]["placements"]
        }
        assert (
            "arithmetic/anchored-relation-postfix-dimension",
            "dir",
        ) in placements
