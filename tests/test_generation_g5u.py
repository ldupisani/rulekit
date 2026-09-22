"""G5u: core adverb ownership and scoped adverb realization."""

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
        "arithmetic/per-member-daily-rates": ((4,), "frequency", ()),
        "arithmetic/two-per-member-daily-rates": ((10,), "frequency2", ()),
        "arithmetic/three-per-member-daily-rates": ((16,), "frequency3", ()),
        "arithmetic/additional-cycling-journey-distance": ((1, 0), "addition", ((1,),)),
        "arithmetic/owned-destination-distance": ((4,), "away", ()),
        "arithmetic/owned-workday-return-schedule": ((4,), "directions", ()),
        "arithmetic/inventory-subtype-particle-withdrawal": ((3,), "particle", ()),
        "arithmetic/inventory-subtype-particle-withdrawal-and-proportion": ((3,), "particle", ()),
        **{
            f"arithmetic/{name}": ((1, 0), "addition", ((1,),))
            for name in (
                "as-many", "times-as-many", "fraction-as-many",
                "affine-times-as-many", "affine-fraction-as-many",
                "as-many-qualified-measures", "times-as-many-qualified-measures",
                "fraction-as-many-qualified-measures", "affine-times-as-many-qualified-measures",
            )
        },
        "arithmetic/affine-fraction-qualified-measures": ((1, 0), "addition", ((1,),)),
        "arithmetic/anchored-relation": (
            (10, 1, 0),
            "conjunction_adv",
            ((10,), (10, 1)),
        ),
        "arithmetic/container-remainder-after-fill-observation": (
            (2,),
            "continuation",
            (),
        ),
        "arithmetic/performed-activity-duration": (
            (4, 0),
            "focus_after",
            ((4,),),
        ),
        "arithmetic/goal-progress-fraction-needed": (
            (2, 0),
            "focus",
            ((2,),),
        ),
        "arithmetic/measured-content-add-quantity": (
            (1, 0),
            "sequence",
            ((1,),),
        ),
        "arithmetic/measured-content-multiply-total": (
            (7, 0),
            "repetition",
            ((7,),),
        ),
        "arithmetic/measured-content-causative-multiply-total": (
            (9, 0),
            "repetition",
            ((9,),),
        ),
        "arithmetic/measured-content-resulting-total-preposed-goal": (
            (1, 0),
            "sequence",
            ((1,),),
        ),
        "arithmetic/measured-content-resulting-total": (
            (1, 0),
            "sequence",
            ((1,),),
        ),
        "arithmetic/measured-content-resulting-total-gapped": (
            (0, 0),
            "sequence",
            ((0,),),
        ),
        "arithmetic/measurement-container-on-instrument": (
            (1, 0),
            "sequence",
            ((1,),),
        ),
        "arithmetic/partition-aggregate-share": (
            (2, 0),
            "focus",
            ((2,),),
        ),
        "arithmetic/recipient-count-transfer-proportional-periods": (
            (11,),
            "sequence",
            (),
        ),
        "arithmetic/recipient-counted-transfer-proportional-periods": (
            (8,),
            "sequence",
            (),
        ),
        TARGET_RULE: ((10, 0), "trailing_adv", ((10,),)),
        "arithmetic/resource-accumulation-window": ((3, 0), "particle", ((3,),)),
        "arithmetic/ordered-two-part-allocation": ((15,), "order", ()),
        "arithmetic/ordered-two-part-allocation-unqualified": ((13,), "order", ()),
    }
    assert MOVED_WORD in core.lexicon
    assert set(project.registry.lexicon[MOVED_WORD].senses) == {"adverb"}
    assert project.registry.word_categories.get(MOVED_WORD, ()) == (
        "current_holding_anchor_adverb",
    )
    assert project.registry.word_categories.get("then", ()) == (
        "conditional_consequent_marker",
        "narration_sequence_adverb",
    )
    assert project.registry.word_categories.get("finally", ()) == (
        "narration_sequence_adverb",
    )
    assert (
        project.source_index.lexicon[MOVED_WORD].path.resolve()
        == (ROOT / "packs/core-english/lexicon/core.yaml").resolve()
    )
    assert [
        word
        for word, entry in sorted(project.registry.lexicon.items())
        if "adverb" in entry.senses
    ] == [
        "again", "ago", "also", "away", "back and forth", MOVED_WORD, "daily", "down", "far", "finally", "individually",
        "just", "next", "off", "once again", "online", "only", "outside", "respectively", "safely", "still", "then", "up",
    ]


def test_combined_pack_semantics_are_identical_to_legacy_ownership() -> None:
    project = load_project(GSM8K)
    core, arithmetic, physics, chemistry, mined = project.packs
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


def test_g5u_reaches_the_complete_premise_generation_frontier() -> None:
    project = load_project(CURATED)
    availability = list_rule_availability(project)

    assert len(availability) == 258
    assert sum(item.supported for item in availability) == 249
    assert sum(not item.supported for item in availability) == 9
    assert all(
        not item.blockers
        or item.id
        in {
                "arithmetic/dangling-comparative-safety",
                "arithmetic/measured-content-resulting-total-gapped",
                "arithmetic/capacity-progress-anaphoric-multiplier-safety",
                "arithmetic/partition-membership-of-mass-measure-safety",
                "arithmetic/realized-progress-anaphoric-multiplier-safety",
                "arithmetic/realized-progress-deictic-anaphoric-multiplier-safety",
                "arithmetic/ratio-split-of-to-possession-safety",
                "logic-arithmetic/universal-all-have-incompatible-item-safety",
                "logic-arithmetic/universal-all-have-quantity-pp-incompatible-item-safety",
            }
        for item in availability
    )
    assert len(exploration_status(project)["fillers"]) == 561


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

    assert candidate.generator_version == "g6-strict-boundary-modes"
    assert candidate.target_status == "matched"
    assert premise.binding == MOVED_WORD
    assert premise.status == "passed"
    assert premise.category_path == (
        MOVED_WORD,
        "current_holding_anchor_adverb",
        "holding_anchor_adverb",
        "adverb",
    )
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


def test_combined_project_exposes_only_declared_holding_anchor_adverbs() -> None:
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

    assert len(adverbs) == 49
    holding_anchor_adverbs = {
        word
        for word in adverbs
        if project.registry.word_in_category(word, "holding_anchor_adverb")
    }

    assert holding_anchor_adverbs == {
        "already",
        "also",
        "always",
        "currently",
        "initially",
        "later",
        "originally",
        "recently",
        "still",
        "then",
    }
    assert all(
        (TARGET_RULE, "trailing_adv")
        in {
            (placement["rule_id"], placement["slot"])
            for placement in fillers[word]["placements"]
        }
        for word in holding_anchor_adverbs
    )
    assert (TARGET_RULE, "trailing_adv") not in {
        (placement["rule_id"], placement["slot"])
        for placement in fillers["off"]["placements"]
    }


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
