"""G5u: core adverb ownership and direct loaded-adverb realization."""

from dataclasses import fields, replace
from pathlib import Path

from rulekit.data.project import load_project
from rulekit.data.registry import compile_registry
from rulekit.generation import generate_candidate, list_rule_availability
from rulekit.generation.exploration import exploration_status
from rulekit.generation.sample import _flat_sentence, _leaf_tokens


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
GSM8K = ROOT / "projects" / "gsm8k"

MOVED_WORD = "currently"
TARGET_RULE = "arithmetic/anchored-relation-conjoined-anchor"


def _write_invented_project(root: Path) -> None:
    pack = root / "pack"
    pack.mkdir()
    (root / "project.yaml").write_text(
        """\
format: rulekit/project@1
name: invented-adverb-generation
packs: [./pack]
"""
    )
    (pack / "pack.yaml").write_text(
        """\
format: rulekit/pack@1
name: invented-adverb
version: 0.1.0
"""
    )
    (pack / "lexicon.yaml").write_text(
        """\
format: rulekit/lexicon@1
entries:
  zadverb: {senses: [adverb]}
"""
    )
    (pack / "rules.yaml").write_text(
        """\
format: rulekit/rules@1
rules:
  - id: invented/adverb
    phase: read
    match:
      sentence:
        - {lit: signal}
        - {slot: manner, cat: adverb}
    emits:
      - fact: atom
        entity: sample
        pred: "{manner}"
"""
    )


def test_direct_adverb_occurrence_and_core_ownership_are_complete() -> None:
    project = load_project(CURATED)
    core = next(pack for pack in project.packs if pack.name == "core-english")
    occurrences = {
        rule.id: (path, token.slot, optional_ancestors)
        for rule in project.registry.rules
        for path, token, optional_ancestors in _leaf_tokens(
            _flat_sentence(rule) or []
        )
        if (
            token.cat is not None
            and project.registry.root_sense(token.cat) == "adverb"
        )
    }

    assert occurrences == {
        TARGET_RULE: ((10, 0), "trailing_adv", ((10,),))
    }
    assert MOVED_WORD in core.lexicon
    assert set(project.registry.lexicon[MOVED_WORD].senses) == {"adverb"}
    assert project.registry.word_categories.get(MOVED_WORD, ()) == ()
    assert (
        project.source_index.lexicon[MOVED_WORD].path.resolve()
        == (ROOT / "packs/core-english/lexicon/core.yaml").resolve()
    )
    assert [
        word
        for word, entry in sorted(project.registry.lexicon.items())
        if "adverb" in entry.senses
    ] == [MOVED_WORD, "far"]


def test_combined_pack_semantics_are_identical_to_legacy_ownership() -> None:
    project = load_project(GSM8K)
    core, arithmetic, mined = project.packs
    legacy_core = replace(
        core,
        lexicon={
            word: entry
            for word, entry in core.lexicon.items()
            if word != MOVED_WORD
        },
        lexicon_sources={
            word: path
            for word, path in core.lexicon_sources.items()
            if word != MOVED_WORD
        },
    )
    legacy_mined = replace(
        mined,
        lexicon={
            **mined.lexicon,
            MOVED_WORD: core.lexicon[MOVED_WORD],
        },
        lexicon_sources={
            **mined.lexicon_sources,
            MOVED_WORD: core.lexicon_sources[MOVED_WORD],
        },
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


def test_g5u_reaches_the_complete_premise_generation_frontier() -> None:
    project = load_project(CURATED)
    availability = list_rule_availability(project)

    assert len(availability) == 105
    assert sum(item.supported for item in availability) == 105
    assert sum(not item.supported for item in availability) == 0
    assert all(not item.blockers for item in availability)
    assert len(exploration_status(project)["fillers"]) == 154


def test_currently_generates_a_matcher_confirmed_anchor() -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id=TARGET_RULE,
        seed=0,
        locked_bindings={"trailing_adv": MOVED_WORD},
    )
    premise = next(
        row for row in candidate.premises if row.slot == "trailing_adv"
    )

    assert candidate.generator_version == "g6-reviewed-premise-boundaries"
    assert candidate.target_status == "matched"
    assert premise.binding == MOVED_WORD
    assert premise.status == "passed"
    assert premise.category_path == (MOVED_WORD, "adverb")
    assert {"rule-token", "lexicon"} <= {
        source["kind"] for source in premise.sources
    }


def test_optional_adverb_can_remain_omitted() -> None:
    project = load_project(CURATED)
    candidates = (
        generate_candidate(
            project,
            rule_id=TARGET_RULE,
            seed=seed,
        )
        for seed in range(16)
    )
    candidate = next(
        candidate
        for candidate in candidates
        if next(
            row
            for row in candidate.premises
            if row.slot == "trailing_adv"
        ).binding is None
    )
    premise = next(
        row for row in candidate.premises if row.slot == "trailing_adv"
    )
    branch = next(
        row
        for row in candidate.premises
        if row.slot_type == "optional" and row.index == premise.index - 1
    )

    assert candidate.target_status == "matched"
    assert (branch.binding, branch.status) == ("omitted", "passed")
    assert (premise.binding, premise.status) == (None, "unverified")


def test_combined_project_exposes_every_loaded_adverb() -> None:
    project = load_project(GSM8K)
    adverbs = {
        word
        for word, entry in project.registry.lexicon.items()
        if "adverb" in entry.senses and not any(ch.isspace() for ch in word)
    }
    fillers = {
        item["identity"]: item
        for item in exploration_status(project)["fillers"]
    }

    assert len(adverbs) == 45
    assert all(
        (TARGET_RULE, "trailing_adv")
        in {
            (placement["rule_id"], placement["slot"])
            for placement in fillers[word]["placements"]
        }
        for word in adverbs
    )


def test_adverb_realization_uses_loaded_project_vocabulary(
    tmp_path: Path,
) -> None:
    _write_invented_project(tmp_path)
    candidate = generate_candidate(
        load_project(tmp_path),
        rule_id="invented/adverb",
        seed=0,
    )
    premise = next(row for row in candidate.premises if row.slot == "manner")

    assert candidate.target_status == "matched"
    assert premise.binding == "zadverb"
    assert premise.category_path == ("zadverb", "adverb")
