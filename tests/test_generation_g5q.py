"""G5q: core ownership of generic age comparatives."""

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

MOVED_WORDS = {"older", "younger"}
MOVED_MEMBERS = {
    "age_comparative": ["older", "younger"],
    "measured_comparative": ["older", "younger"],
    "more_dir": ["older"],
    "less_dir": ["younger"],
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


def test_age_comparatives_and_core_memberships_share_ownership() -> None:
    project = load_project(CURATED)
    core = next(pack for pack in project.packs if pack.name == "core-english")

    assert MOVED_WORDS <= set(core.lexicon)
    assert {
        word: project.source_index.lexicon[word].path.resolve()
        for word in MOVED_WORDS
    } == {
        word: (ROOT / "packs/core-english/lexicon/core.yaml").resolve()
        for word in MOVED_WORDS
    }
    assert project.registry.word_categories["older"] == (
        "age_comparative",
        "measured_comparative",
        "more_dir",
    )
    assert project.registry.word_categories["younger"] == (
        "age_comparative",
        "less_dir",
        "measured_comparative",
    )


def test_combined_pack_semantics_are_identical_to_legacy_ownership() -> None:
    project = load_project(GSM8K)
    core, arithmetic, physics, chemistry, mined = project.packs
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
    legacy = compile_registry(
        [legacy_core, arithmetic, physics, chemistry, legacy_mined]
    )
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
    assert project.registry.word_categories["older"] == (
        "age_comparative",
        "higher",
        "measured_comparative",
        "more_dir",
    )
    assert project.registry.word_categories["younger"] == (
        "age_comparative",
        "less_dir",
        "lower",
        "measured_comparative",
    )


def test_g5q_unlocks_exactly_the_preregistered_rule() -> None:
    project = load_project(CURATED)
    availability = {
        item.id: item for item in list_rule_availability(project)
    }

    assert len(availability) == 188
    assert sum(item.supported for item in availability.values()) == 179
    assert sum(not item.supported for item in availability.values()) == 9
    assert availability[
        "arithmetic/times-comparative-age-relation"
    ].supported
    assert availability[
        "arithmetic/anchored-relation-postfix-dimension"
    ].supported
    assert availability[
        "arithmetic/anchored-relation-postfix-age"
    ].supported
    assert len(exploration_status(project)["fillers"]) == 490


@pytest.mark.parametrize("comparative", sorted(MOVED_WORDS))
def test_both_age_comparatives_generate_matcher_confirmed_specimens(
    comparative: str,
) -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id="arithmetic/times-comparative-age-relation",
        seed=0,
        locked_bindings={"dir": comparative},
    )
    premise = next(row for row in candidate.premises if row.slot == "dir")

    assert candidate.generator_version == "g6-strict-boundary-modes"
    assert candidate.target_status == "matched"
    assert premise.binding == comparative
    assert premise.status == "passed"
    assert premise.category_path == (
        comparative,
        "age_comparative",
        "comparative",
    )
    assert {
        "rule-token",
        "lexicon",
        "category-member",
        "category",
    } <= {source["kind"] for source in premise.sources}


def test_exploration_exposes_both_age_comparatives_on_the_new_rule() -> None:
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
            "arithmetic/times-comparative-age-relation",
            "dir",
        ) in placements
        assert (
            "arithmetic/anchored-relation-postfix-age",
            "dir",
        ) in placements
