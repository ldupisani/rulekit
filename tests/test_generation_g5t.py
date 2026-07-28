"""G5t: core temporal-marker ownership and generic time realization."""

from dataclasses import fields, replace
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.data.registry import compile_registry
from rulekit.data.schemas import CategoriesDoc
from rulekit.generation import generate_candidate, list_rule_availability
from rulekit.generation.exploration import exploration_status
from rulekit.generation.sample import _flat_sentence, _leaf_tokens


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
GSM8K = ROOT / "projects" / "gsm8k"

MOVED_WORDS = {"now", "today"}
MOVED_MEMBERS = {"temporal_marker": ["today", "now"]}
TARGET_RULE = (
    "arithmetic/temporal-offset-times-as-old-as-future-std-now"
)


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


def _write_invented_project(root: Path) -> None:
    pack = root / "pack"
    pack.mkdir()
    (root / "project.yaml").write_text(
        """\
format: rulekit/project@1
name: invented-time-generation
packs: [./pack]
"""
    )
    (pack / "pack.yaml").write_text(
        """\
format: rulekit/pack@1
name: invented-time
version: 0.1.0
"""
    )
    (pack / "lexicon.yaml").write_text(
        """\
format: rulekit/lexicon@1
entries:
  zwhen: {senses: [time]}
"""
    )
    (pack / "categories.yaml").write_text(
        """\
format: rulekit/categories@1
categories:
  invented_marker: {parent: time}
members:
  invented_marker: [zwhen]
"""
    )
    (pack / "rules.yaml").write_text(
        """\
format: rulekit/rules@1
rules:
  - id: invented/time
    phase: read
    match:
      sentence:
        - {lit: signal}
        - {slot: mark, cat: invented_marker}
    emits:
      - fact: atom
        entity: sample
        pred: "{mark}"
"""
    )


def test_temporal_marker_occurrence_and_core_ownership_are_complete() -> None:
    project = load_project(CURATED)
    core = next(pack for pack in project.packs if pack.name == "core-english")
    occurrences = {
        rule.id: (path, token.slot, optional_ancestors)
        for rule in project.registry.rules
        for path, token, optional_ancestors in _leaf_tokens(
            _flat_sentence(rule) or []
        )
        if token.cat == "temporal_marker"
    }
    expected_source = (
        ROOT / "packs/core-english/lexicon/core.yaml"
    ).resolve()

    assert occurrences == {TARGET_RULE: ((12,), "mark", ())}
    assert MOVED_WORDS <= set(core.lexicon)
    assert {
        project.source_index.lexicon[word].path.resolve()
        for word in MOVED_WORDS
    } == {expected_source}
    assert all(
        set(project.registry.lexicon[word].senses) == {"time"}
        for word in MOVED_WORDS
    )
    assert all(
        project.registry.word_categories[word] == ("temporal_marker",)
        for word in MOVED_WORDS
    )
    assert project.registry.cat_ancestors("temporal_marker") == [
        "temporal_marker",
        "time",
    ]


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


def test_g5t_unlocks_exactly_the_preregistered_frontier() -> None:
    project = load_project(CURATED)
    availability = {
        item.id: item for item in list_rule_availability(project)
    }

    assert len(availability) == 95
    assert sum(item.supported for item in availability.values()) == 95
    assert sum(not item.supported for item in availability.values()) == 0
    assert availability[TARGET_RULE].supported
    # G5u subsequently supplied the loaded direct-adverb domain.
    assert availability[
        "arithmetic/anchored-relation-conjoined-anchor"
    ].supported
    assert all(
        "unsupported sense 'time'" not in blocker
        for item in availability.values()
        for blocker in item.blockers
    )
    assert len(exploration_status(project)["fillers"]) == 151


@pytest.mark.parametrize("marker", sorted(MOVED_WORDS))
def test_every_temporal_marker_generates_a_matcher_confirmed_specimen(
    marker: str,
) -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id=TARGET_RULE,
        seed=0,
        locked_bindings={"mark": marker},
    )
    premise = next(row for row in candidate.premises if row.slot == "mark")

    assert candidate.generator_version == "g6-reviewed-premise-boundaries"
    assert candidate.target_status == "matched"
    assert premise.binding == marker
    assert premise.status == "passed"
    assert premise.category_path == (
        marker,
        "temporal_marker",
        "time",
    )
    assert {
        "rule-token",
        "lexicon",
        "category-member",
        "category",
    } <= {source["kind"] for source in premise.sources}


def test_exploration_exposes_both_markers_on_the_new_rule() -> None:
    fillers = {
        item["identity"]: item
        for item in exploration_status(load_project(CURATED))["fillers"]
    }

    for marker in MOVED_WORDS:
        placements = {
            (placement["rule_id"], placement["slot"])
            for placement in fillers[marker]["placements"]
            if placement["slot"] == "mark"
        }
        assert placements == {(TARGET_RULE, "mark")}


def test_time_realization_uses_loaded_project_vocabulary(
    tmp_path: Path,
) -> None:
    _write_invented_project(tmp_path)
    candidate = generate_candidate(
        load_project(tmp_path),
        rule_id="invented/time",
        seed=0,
    )
    premise = next(row for row in candidate.premises if row.slot == "mark")

    assert candidate.target_status == "matched"
    assert premise.binding == "zwhen"
    assert premise.category_path == ("zwhen", "invented_marker", "time")
