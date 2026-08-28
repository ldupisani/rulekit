"""G5s: core modal ownership and generic modal realization."""

from dataclasses import fields, replace
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.data.registry import compile_registry
from rulekit.data.schemas import CategoriesDoc
from rulekit.generation import (
    GenerationError,
    generate_candidate,
    list_rule_availability,
)
from rulekit.generation.exploration import exploration_status
from rulekit.generation.sample import _flat_sentence, _leaf_tokens


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
GSM8K = ROOT / "projects" / "gsm8k"

CAPACITY = {"can", "could", "may", "might", "must", "should"}
FUTURE = {"will", "would"}
MOVED_WORDS = CAPACITY | FUTURE
MOVED_MEMBERS = {
    "capacity_modal": sorted(CAPACITY),
    "future_modal": sorted(FUTURE),
}
FUTURE_RULES = {
    "arithmetic/temporal-offset-age-future",
    "arithmetic/temporal-offset-age-future-intensified",
    "arithmetic/temporal-offset-times-as-old-as-future",
}
EXPECTED_OCCURRENCES = {
    "logic-arithmetic/universal-location-exit-impossibility": (
        (1,),
        None,
        (),
    ),
    "arithmetic/periodic-rate-every-span": ((1, 0), "modal", ((1,),)),
    "arithmetic/temporal-offset-age-future": (
        (3,),
        "future_modal",
        (),
    ),
    "arithmetic/temporal-offset-age-future-intensified": (
        (5,),
        "future_modal",
        (),
    ),
    "arithmetic/temporal-offset-times-as-old-as-future": (
        (3,),
        "future_modal",
        (),
    ),
    "arithmetic/temporal-offset-times-as-old-as-future-std-now": (
        (3,),
        "future_modal",
        (),
    ),
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


def test_modal_occurrence_and_core_ownership_maps_are_complete() -> None:
    project = load_project(CURATED)
    core = next(pack for pack in project.packs if pack.name == "core-english")
    occurrences = {
        rule.id: (
            path,
            token.type
            or ("future_modal" if token.cat == "future_modal" else None),
            optional_ancestors,
        )
        for rule in project.registry.rules
        for path, token, optional_ancestors in _leaf_tokens(
            _flat_sentence(rule) or []
        )
        if token.type in {"modal", "future_modal"}
        or token.cat in {"future_modal", "location_impossibility_modal"}
    }
    expected_source = (
        ROOT / "packs/core-english/lexicon/core.yaml"
    ).resolve()

    assert occurrences == EXPECTED_OCCURRENCES
    assert MOVED_WORDS <= set(core.lexicon)
    assert {
        project.source_index.lexicon[word].path.resolve()
        for word in MOVED_WORDS
    } == {expected_source}
    assert all(
        project.registry.word_categories[word] == ("capacity_modal",)
        for word in CAPACITY - {"can", "may", "should"}
    )
    assert project.registry.word_categories["may"] == (
        "capacity_modal",
        "named_calendar_period",
        "named_month",
        "temporal_in_point_object",
        "timeperiod",
    )
    assert project.registry.word_categories["should"] == (
        "capacity_modal",
        "planned_progress_modal",
    )
    assert project.registry.word_categories["can"] == (
        "capacity_modal",
        "location_impossibility_modal",
        "transferable_quantity_object",
    )
    assert all(
        project.registry.word_categories[word] == ("future_modal",)
        for word in FUTURE
    )
    assert set(project.registry.lexicon["can"].senses) == {"modal", "noun"}
    assert project.registry.lexicon["can"].plural == "cans"


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
    assert project.registry.word_categories["can"] == (
        "capacity_modal",
        "litter",
        "location_impossibility_modal",
        "transferable_quantity_object",
    )


def test_g5s_unlocks_exactly_the_preregistered_frontier() -> None:
    project = load_project(CURATED)
    availability = {
        item.id: item for item in list_rule_availability(project)
    }

    assert len(availability) == 168
    assert sum(item.supported for item in availability.values()) == 159
    assert sum(not item.supported for item in availability.values()) == 9
    assert availability["arithmetic/periodic-rate-every-span"].supported
    assert all(availability[rule_id].supported for rule_id in FUTURE_RULES)
    # G5t subsequently supplied the temporal-marker domain for the fourth
    # future rule, so the entire modal occurrence map must remain unlocked.
    assert availability[
        "arithmetic/temporal-offset-times-as-old-as-future-std-now"
    ].supported
    assert availability[
        "arithmetic/anchored-relation-conjoined-anchor"
    ].supported
    assert len(exploration_status(project)["fillers"]) == 391


@pytest.mark.parametrize("modal", sorted(MOVED_WORDS))
def test_periodic_rule_exposes_every_loaded_modal(modal: str) -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id="arithmetic/periodic-rate-every-span",
        seed=0,
        locked_bindings={"aux": modal},
    )
    premise = next(row for row in candidate.premises if row.slot == "aux")
    direct = "capacity_modal" if modal in CAPACITY else "future_modal"

    assert candidate.generator_version == "g6-strict-boundary-modes"
    assert candidate.target_status == "matched"
    assert premise.binding == modal
    assert premise.category_path == (modal, direct, "modal")
    assert {
        "rule-token",
        "lexicon",
        "category-member",
        "category",
    } <= {source["kind"] for source in premise.sources}


@pytest.mark.parametrize("rule_id", sorted(FUTURE_RULES))
@pytest.mark.parametrize("modal", sorted(FUTURE))
def test_future_slots_expose_only_future_modals(
    rule_id: str,
    modal: str,
) -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id=rule_id,
        seed=0,
        locked_bindings={"aux": modal},
    )
    premise = next(row for row in candidate.premises if row.slot == "aux")

    assert candidate.target_status == "matched"
    assert premise.binding == modal
    assert premise.category_path == (modal, "future_modal", "modal")


def test_capacity_modal_cannot_enter_a_future_slot() -> None:
    with pytest.raises(
        GenerationError,
        match="constraints left no filler for aux",
    ):
        generate_candidate(
            load_project(CURATED),
            rule_id="arithmetic/temporal-offset-age-future",
            seed=0,
            locked_bindings={"aux": "can"},
        )


def test_numeric_round_trip_errors_resample_instead_of_crashing() -> None:
    project = load_project(CURATED)
    recovered = generate_candidate(
        project,
        rule_id="arithmetic/periodic-rate-every-span",
        seed=31,
    )

    assert recovered.target_status == "matched"
    assert recovered.attempts == 1
    with pytest.raises(
        GenerationError,
        match="ordinary round trip rejected generated numeric values",
    ):
        generate_candidate(
            project,
            rule_id="arithmetic/periodic-rate-every-span",
            seed=0,
            max_attempts=3,
            locked_bindings={"span": "0 years"},
        )
