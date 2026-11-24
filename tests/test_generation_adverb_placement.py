"""Core adverb ownership and scoped adverb realization."""

from dataclasses import fields, replace
from pathlib import Path

from rulekit.data.project import load_project
from rulekit.data.registry import compile_registry
from rulekit.generation import generate_candidate
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
        "arithmetic/ordinary-and-reduced-price": ((4,), "normal", ()),
        "arithmetic/ordinary-purchase-lot-price": ((3,), "normal", ()),
        "arithmetic/whole-sections-completed": ((8,), "time", ()),
        "arithmetic/skipped-indexed-section-remainder": ((2,), "time", ()),
        "arithmetic/skipped-remainder-and-further-sections": ((2,), "time", ()),
        "arithmetic/additional-ratio-acquisition": ((1, 0), "sequence", ((1,),)),
        "arithmetic/additive-purchase-target": ((1,), "also", ()),
        "arithmetic/equal-account-division-among-payers": ((3,), "equal", ()),
        "arithmetic/equal-division-within-group": ((5,), "equal", ()),
        "arithmetic/named-equal-account-division": ((4,), "equal", ()),
        "arithmetic/current-dimension-amount": ((2, 0), "now", ((2,),)),
        "arithmetic/member-rated-workforce-expansion": ((10, 1, 0), "also", ((10,), (10, 1))),
        "arithmetic/ordinal-relative-event-rate": ((5,), "extent", ()),
        "arithmetic/packaged-offer-with-stated-lot-count": ((8, 0), "only", ((8,),)),
        "arithmetic/equal-population-arrival-with-return-share": ((9, 0), 'then', ((9,),)),
        "arithmetic/remaining-relative-receipt": ((0, 0), 'next', ((0,),)),
        "arithmetic/separately-required-documents": ((1, 0), 'also', ((1,),)),
        'arithmetic/qualitative-location-flow-context': ((2,), 'degree', ()),
        'arithmetic/required-account-correction': ((8,), 'quality', ()),
        'arithmetic/affine-recipient-transfer': ((2, 0), 'then', ((2,),)),
        'arithmetic/exhaustive-section-remaining-list': ((0, 0), 'then', ((0,),)),
        'arithmetic/measured-item-quote': ((1, 0), 'also', ((1,),)),
        'arithmetic/relative-measured-item-quote': ((1, 0), 'also', ((1,),)),
        'arithmetic/relative-recipient-transfer': ((2, 0), 'then', ((2,),)),
        'arithmetic/removed-section-fraction': ((11, 0), 'quickly', ((11,),)),
        'arithmetic/stated-recipient-transfer': ((2, 0), 'then', ((2,),)),
'arithmetic/pooled-stock-shared-within-group': ((8,), 'equally', ()),
                           'arithmetic/sequenced-measured-age-comparison': ((0,), 'sequence', ()),
                           'arithmetic/container-content-scale': ((0, 0), 'sequence', ((0,),)),
                           'arithmetic/container-content-scale-by-number': ((0, 0), 'sequence', ((0,),)),
                           'arithmetic/container-content-scale-by-fraction': ((0, 0), 'sequence', ((0,),)),
                           'arithmetic/deposit-sale-proceeds': ((0, 0), 'sequence', ((0,),)),
                           'arithmetic/deposit-owned-proceeds': ((0, 0), 'sequence', ((0,),)),
                           'arithmetic/deposit-without-stated-source': ((0, 0), 'sequence', ((0,),)),
                           'arithmetic/fractional-container-fill-with-departure': ((3,), 'fraction', ()),
                           'arithmetic/fractional-fill-of-named-container': ((4,), 'fraction', ()),
                           'arithmetic/temporary-departure-for-response': ((1,), 'sequence', ()),
                           'arithmetic/population-rate-assessment-finite': ((3, 0), 'frequency', ((3,),)),
                           'arithmetic/population-rate-assessment-progressive': ((4, 0), 'frequency', ((4,),)),
                           'arithmetic/population-rate-inquiry': ((6, 0), 'frequency', ((6,),)),
                           'arithmetic/population-rate-inquiry-qualified-attribute': ((4, 0), 'particle', ((4,),)),
                           'arithmetic/acquired-batch-counted-classify': ((4, 0), 'again', ((4,),)),
                           'arithmetic/acquired-batch-counted-classify-negative': ((4, 0), 'again', ((4,),)),
                           'arithmetic/acquired-batch-counted-discard': ((4, 0), 'again', ((4,),)),
                           'arithmetic/acquired-batch-counted-discard-negative-reason': ((4, 0), 'again', ((4,),)),
                           'arithmetic/acquired-batch-counted-discard-reason': ((4, 0), 'again', ((4,),)),
                           'arithmetic/acquired-batch-more-classify': ((6, 0), 'again', ((6,),)),
                           'arithmetic/acquired-batch-more-classify-negative': ((6, 0), 'again', ((6,),)),
                           'arithmetic/acquired-batch-more-discard': ((6, 0), 'again', ((6,),)),
                           'arithmetic/acquired-batch-more-discard-negative-reason': ((6, 0), 'again', ((6,),)),
                           'arithmetic/acquired-batch-more-discard-reason': ((6, 0), 'again', ((6,),)),
                           'arithmetic/additional-cycling-journey-distance': ((1, 0), 'addition', ((1,),)),
                           'arithmetic/affine-fraction-as-many': ((1, 0), 'addition', ((1,),)),
                           'arithmetic/affine-fraction-qualified-measures': ((1, 0), 'addition', ((1,),)),
                           'arithmetic/affine-times-as-many': ((1, 0), 'addition', ((1,),)),
                           'arithmetic/affine-times-as-many-qualified-measures': ((1, 0), 'addition', ((1,),)),
                           'arithmetic/allocation-retained-remainder': ((6,), 'equal', ()),
                           'arithmetic/anchored-relation': ((10, 1, 0), 'conjunction_adv', ((10,), (10, 1))),
                           'arithmetic/anchored-relation-conjoined-anchor': ((10, 0), 'trailing_adv', ((10,),)),
                           'arithmetic/as-many': ((1, 0), 'addition', ((1,),)),
                           'arithmetic/as-many-qualified-measures': ((1, 0), 'addition', ((1,),)),
                           'arithmetic/bounded-process-rates': ((21,), 'rest', ()),
                           'arithmetic/bounded-process-rates-compact': ((18,), 'rest', ()),
                           'arithmetic/comparison-repeated-predicate-fraction': ((2, 0), 'only', ((2,),)),
                           'arithmetic/comparison-repeated-predicate-fraction-auxiliary': ((2, 0), 'only', ((2,),)),
                           'arithmetic/container-remainder-after-fill-observation': ((2,), 'continuation', ()),
                           'arithmetic/equal-resource-transfer-count': ((3,), 'equal', ()),
                           'arithmetic/equal-resource-transfer-count-passive': ((3,), 'equal', ()),
                           'arithmetic/equal-resource-transfer-length': ((5,), 'equal', ()),
                           'arithmetic/equal-resource-transfer-length-passive': ((5,), 'equal', ()),
                           'arithmetic/equal-resource-transfer-mass': ((5,), 'equal', ()),
                           'arithmetic/equal-resource-transfer-mass-passive': ((5,), 'equal', ()),
                           'arithmetic/equal-resource-transfer-volume': ((5,), 'equal', ()),
                           'arithmetic/equal-resource-transfer-volume-passive': ((5,), 'equal', ()),
                           'arithmetic/explicit-equal-bill-division': ((4,), 'equal', ()),
                           'arithmetic/fraction-as-many': ((1, 0), 'addition', ((1,),)),
                           'arithmetic/fraction-of-comparative-count': ((1, 0), 'addition', ((1,),)),
                           'arithmetic/fraction-as-many-qualified-measures': ((1, 0), 'addition', ((1,),)),
                           'arithmetic/goal-progress-fraction-needed': ((2, 0), 'focus', ((2,),)),
                           'arithmetic/inactive-period-saving-plan': ((12, 0), 'up', ((12,),)),
                           'arithmetic/inactive-period-saving-plan-explicit-copula': ((12, 0), 'up', ((12,),)),
                           'arithmetic/income-increase-with-expense-copula': ((3, 0), 'recent', ((3,),)),
                           'arithmetic/income-increase-with-expense-share': ((3, 0), 'recent', ((3,),)),
                           'arithmetic/inventory-subtype-particle-withdrawal': ((3,), 'particle', ()),
                           'arithmetic/inventory-subtype-particle-withdrawal-and-proportion': ((3,), 'particle', ()),
                           'arithmetic/measured-content-add-quantity': ((1, 0), 'sequence', ((1,),)),
                           'arithmetic/measured-content-causative-multiply-total': ((9, 0), 'repetition', ((9,),)),
                           'arithmetic/measured-content-multiply-total': ((7, 0), 'repetition', ((7,),)),
                           'arithmetic/measured-content-resulting-total': ((1, 0), 'sequence', ((1,),)),
                           'arithmetic/measured-content-resulting-total-gapped': ((0, 0), 'sequence', ((0,),)),
                           'arithmetic/measured-content-resulting-total-preposed-goal': ((1, 0), 'sequence', ((1,),)),
                           'arithmetic/measurement-container-on-instrument': ((1, 0), 'sequence', ((1,),)),
                           'arithmetic/ordered-two-part-allocation': ((15,), 'order', ()),
                           'arithmetic/ordered-two-part-allocation-unqualified': ((13,), 'order', ()),
                           'arithmetic/owned-destination-distance': ((4,), 'away', ()),
                           'arithmetic/owned-workday-return-schedule': ((4,), 'directions', ()),
                           'arithmetic/partition-aggregate-share': ((2, 0), 'focus', ((2,),)),
                           'arithmetic/passive-share-of-demonstrative-earnings': ((0, 0), 'contrast', ((0,),)),
                           'arithmetic/passive-share-of-referenced-earnings': ((0, 0), 'contrast', ((0,),)),
                           'arithmetic/passive-share-of-stated-earnings': ((0, 0), 'contrast', ((0,),)),
                           'arithmetic/path-gap-and-exit-numeric-numeric': ((12,), 'immediate', ()),
                           'arithmetic/path-gap-and-exit-numeric-numeric-reference01': ((12,), 'immediate', ()),
                           'arithmetic/path-gap-and-exit-numeric-numeric-reference10': ((12,), 'immediate', ()),
                           'arithmetic/path-gap-and-exit-numeric-numeric-reference11': ((12,), 'immediate', ()),
                           'arithmetic/path-gap-and-exit-numeric-word': ((11,), 'immediate', ()),
                           'arithmetic/path-gap-and-exit-numeric-word-reference01': ((11,), 'immediate', ()),
                           'arithmetic/path-gap-and-exit-numeric-word-reference10': ((11,), 'immediate', ()),
                           'arithmetic/path-gap-and-exit-numeric-word-reference11': ((11,), 'immediate', ()),
                           'arithmetic/path-gap-and-exit-word-numeric': ((11,), 'immediate', ()),
                           'arithmetic/path-gap-and-exit-word-numeric-reference01': ((11,), 'immediate', ()),
                           'arithmetic/path-gap-and-exit-word-numeric-reference10': ((11,), 'immediate', ()),
                           'arithmetic/path-gap-and-exit-word-numeric-reference11': ((11,), 'immediate', ()),
                           'arithmetic/path-gap-and-exit-word-word': ((10,), 'immediate', ()),
                           'arithmetic/path-gap-and-exit-word-word-reference01': ((10,), 'immediate', ()),
                           'arithmetic/path-gap-and-exit-word-word-reference10': ((10,), 'immediate', ()),
                           'arithmetic/path-gap-and-exit-word-word-reference11': ((10,), 'immediate', ()),
                           'arithmetic/path-immediate-exit-numeric': ((4,), 'immediate', ()),
                           'arithmetic/path-immediate-exit-numeric-reference': ((4,), 'immediate', ()),
                           'arithmetic/path-immediate-exit-word': ((3,), 'immediate', ()),
                           'arithmetic/path-immediate-exit-word-reference': ((3,), 'immediate', ()),
                           'arithmetic/path-unknown-leg-numeric': ((6,), 'further', ()),
                           'arithmetic/path-unknown-leg-numeric-reference': ((6,), 'further', ()),
                           'arithmetic/path-unknown-leg-word': ((5,), 'further', ()),
                           'arithmetic/path-unknown-leg-word-reference': ((5,), 'further', ()),
                           'arithmetic/per-member-daily-rates': ((4,), 'frequency', ()),
                           'arithmetic/performed-activity-duration': ((4, 0), 'focus_after', ((4,),)),
                           'arithmetic/recipient-count-transfer-proportional-periods': ((11,), 'sequence', ()),
                           'arithmetic/recipient-counted-transfer-proportional-periods': ((8,), 'sequence', ()),
                           'arithmetic/remainder-period-saving-plan': ((4, 0), 'up', ((4,),)),
                           'arithmetic/resource-accumulation-window': ((3, 0), 'particle', ((3,),)),
                           'arithmetic/retained-and-shared-remainder': ((6,), 'equally', ()),
                           'arithmetic/three-per-member-daily-rates': ((16,), 'frequency3', ()),
                           'arithmetic/threshold-share-reported': ((2, 0), 'particle', ((2,),)),
                           'arithmetic/threshold-share-reported-numeric': ((2, 0), 'particle', ((2,),)),
                           'arithmetic/times-as-many': ((1, 0), 'addition', ((1,),)),
                           'arithmetic/times-as-many-qualified-measures': ((1, 0), 'addition', ((1,),)),
                           'arithmetic/two-per-member-daily-rates': ((10,), 'frequency2', ()),
                           'arithmetic/uniform-price-purchase-lot': ((1, 0), 'addition', ((1,),))}
    assert MOVED_WORD in core.lexicon
    assert set(project.registry.lexicon[MOVED_WORD].senses) == {"adverb"}
    assert project.registry.word_categories.get(MOVED_WORD, ()) == (
        "current_holding_anchor_adverb",
        "current_snapshot_adverb",
    )
    assert project.registry.word_categories.get("then", ()) == (
        "conditional_consequent_marker",
        "flexible_holding_anchor_adverb",
        "narration_sequence_adverb",
        "transaction_sequence_adverb",
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
    ] == sorted([
        "actively", "actually", "afterward", "all-around", "already", "always", "back", "continuously", "correctly", "downhill", "earlier", "exactly", "forever", "forth", "initially", "instead", "later", "normally", "otherwise", "quickly", "separately", "strictly", "incorrectly", "very",
        "usually", "o'clock", "again", "ago", "also", "away", "back and forth", "completely", MOVED_WORD, "daily", "down", "entirely", "equally", "evenly", "far", "finally", "fully", "further", "however", "immediately", "individually",
        "frequently", "halfway", "just", "next", "off", "once again", "online", "only", "originally", "out", "outside", "recently", "respectively", "safely", "still", "then", "thereafter", "too", "up", "upstairs", "vertically", "yet",
    ])


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

    assert len(adverbs) == 67
    assert "evenly" in adverbs
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
