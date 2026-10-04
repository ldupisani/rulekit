"""Review-led adjective/noun compatibility is declarative and many-to-many."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from rulekit.data.project import load_project
from rulekit.data.registry import CompileError
from rulekit.data.schemas import (
    AttributeCompatibilityPredicate,
    CategoriesDoc,
)
from rulekit.generation import (
    generate_candidate,
    list_rule_availability,
)
from rulekit.generation.reviews import review_path
from rulekit.kernel.engine import solve


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
GSM8K = ROOT / "projects" / "gsm8k"
RULE_ID = "arithmetic/partition-attribute-of-noun"
REVIEW_ID = "rev-e7fd1d7166c14f32"


def _matched_rules(text: str, registry) -> set[str]:
    result = solve(text, registry)
    return {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


def _rule_tokens(rule):
    for sequence in rule.match.values():
        if sequence and isinstance(sequence[0], list):
            for branch in sequence:
                yield from branch
        else:
            yield from sequence


def _write_many_to_many_project(root: Path, *, bad_target: str | None = None) -> None:
    pack = root / "pack"
    pack.mkdir(parents=True)
    (root / "project.yaml").write_text(
        """\
format: rulekit/project@1
name: invented-compatibility
packs: [./pack]
"""
    )
    (pack / "pack.yaml").write_text(
        """\
format: rulekit/pack@1
name: invented
version: 0.1.0
"""
    )
    (pack / "lexicon.yaml").write_text(
        """\
format: rulekit/lexicon@1
entries:
  two: {senses: [number]}
  of: {senses: [preposition]}
  the: {senses: [article]}
  are: {senses: [verb]}
  bright: {senses: [adjective]}
  pebble: {senses: [noun], plural: pebbles}
  cloud: {senses: [noun], plural: clouds}
  idea: {senses: [noun], plural: ideas}
"""
    )
    targets = (
        f"[solid_noun, {bad_target}]" if bad_target is not None
        else "[solid_noun, display_noun]"
    )
    (pack / "categories.yaml").write_text(
        f"""\
format: rulekit/categories@1
categories:
  appearance_attribute: {{parent: adjective}}
  solid_noun: {{parent: noun}}
  display_noun: {{parent: noun}}
  abstract_noun: {{parent: noun}}
members:
  appearance_attribute: [bright]
  solid_noun: [pebble]
  display_noun: [cloud]
  abstract_noun: [idea]
attribute_compatibility:
  appearance_attribute: {targets}
"""
    )
    (pack / "numbers.yaml").write_text(
        """\
format: rulekit/numbers@1
numbers:
  two: 2
"""
    )
    (pack / "rules.yaml").write_text(
        """\
format: rulekit/rules@1
rules:
  - id: invented/compatible-description
    phase: read
    match:
      sentence:
        - {slot: n, type: number}
        - {lit: of}
        - {lit: the, consume_skipped: true}
        - {slot: coll, type: plural}
        - {lit: are}
        - {slot: attr, type: adjective}
    where:
      - attribute_compatible: {attribute: attr, noun: coll}
"""
    )


def test_compatibility_predicate_requires_both_named_slots() -> None:
    predicate = AttributeCompatibilityPredicate(attribute="attr", noun="coll")
    assert predicate.attribute == "attr"
    assert predicate.noun == "coll"

    with pytest.raises(ValidationError):
        AttributeCompatibilityPredicate(attribute="attr")


def test_compatibility_mapping_requires_distinct_nonempty_targets() -> None:
    with pytest.raises(ValidationError, match="needs a noun category"):
        CategoriesDoc.model_validate(
            {
                "format": "rulekit/categories@1",
                "attribute_compatibility": {"appearance_attribute": []},
            }
        )
    with pytest.raises(ValidationError, match="repeats a noun category"):
        CategoriesDoc.model_validate(
            {
                "format": "rulekit/categories@1",
                "attribute_compatibility": {
                    "appearance_attribute": ["solid_noun", "solid_noun"]
                },
            }
        )


def test_compile_rejects_an_unknown_compatible_noun_category(
    tmp_path: Path,
) -> None:
    _write_many_to_many_project(tmp_path, bad_target="missing_noun")

    with pytest.raises(CompileError, match="unknown noun category 'missing_noun'"):
        load_project(tmp_path)


def test_compile_rejects_a_non_descriptor_compatibility_slot(
    tmp_path: Path,
) -> None:
    _write_many_to_many_project(tmp_path)
    rules = tmp_path / "pack" / "rules.yaml"
    rules.write_text(
        rules.read_text().replace(
            "{slot: attr, type: adjective}",
            "{slot: attr, type: verb}",
        )
    )

    with pytest.raises(CompileError, match="is not descriptor-rooted"):
        load_project(tmp_path)


def test_curated_compatibility_domain_is_the_current_complete_domain() -> None:
    registry = load_project(CURATED).registry
    adjectives = {
        word
        for word, entry in registry.lexicon.items()
        if "adjective" in entry.senses and not any(ch.isspace() for ch in word)
    }
    plural_nouns = {
        word
        for word, entry in registry.lexicon.items()
        if "noun" in entry.senses and entry.plural is not None
    }

    assert adjectives == {
        "helpful", "useful", "relevant", "valuable", "irrelevant",
        "unrelated", "unhelpful", "useless", "second", "third",
        "entire", "full", "specific", "particular", "stranded",
        "additive", "pure", "homogeneous", "uniform",
        "favorite", "favourite", "same",
        "weekend",
        "pink",
        "able",
        "beige",
        "blue",
        "business",
        "button-up",
        "deep-sea",
        "different",
        "done",
        "eligible",
        "enough",
        "final",
        "first",
        "following",
        "gravitational",
        "green",
        "humanities",
        "hourly",
        "large",
        "last",
        "left",
        "media",
        "molar",
        "new",
        "next",
        "old",
        "online",
        "purple",
        "potential",
        "previous",
        "red",
        "remaining",
        "science",
        "small",
        "tall",
        "turquoise",
        "violet",
        "yellow",
    }
    # The core generation vocabulary adds ordinary count nouns and the
    # reviewed descriptor vocabulary. Core-owned literal adjectives such as
    # `old` and `different` remain outside descriptor compatibility categories.
    # Compatibility still comes from category membership, never broader senses.
    # `head` and `university` are core-owned for the logic bridge, while
    # `topic` supports reviewed topical quantities. `page` and `week` support
    # measured-output cadence; `last` is licensed only for duration measures.
    # Core-owned `remaining` now inherits the established remnant-noun domain
    # and additionally licenses the content-progress measure. The terminal
    # measurement construction declares exactly one further pair: final weight.
    # `boy` and `girl` are now shared core complement-label vocabulary. Parent,
    # grandparent, purpose, and wallet likewise belong to ordinary core English;
    # their semantic roles remain separately declared by categories. Portable
    # physical containers share the qualified-package role and therefore the
    # reviewed small/large pairs; large appliances remain outside that class.
    # Capacity and content are ordinary core nouns used by the container
    # inquiry frames; neither broadens descriptor compatibility.
    # Day, pizza, slice, and piece are shared vocabulary for bounded
    # portioned-food events; day accepts `last`, while only pizza joins the
    # small/large whole domain.
    # The reusable science packs contribute meter, object, speed, height,
    # joule, moles, and the compound velocity unit as pluralizable nouns;
    # seconds and moles are deliberately plural-only identities.
    # Rate policies add shift/wage and license hourly for hour/wage.
    # Savings adds six pluralizable nouns; month reuses duration descriptors.
    # Batch acquisition adds eight plural nouns and relevance descriptors.
    assert len(plural_nouns) == 237
    assert {
        "boy",
        "day",
        "fridge",
        "girl",
        "grandparent",
        "head",
        "parent",
        "purpose",
        "pizza",
        "piece",
        "slice",
        "topic",
        "university",
        "wallet",
    } <= plural_nouns
    assert registry.attribute_applies_to("final", "weight")
    # The business descriptor follows the shared allocation-participant
    # family, adding fourteen compatible nouns without another word list.
    assert sum(
        registry.attribute_applies_to(attribute, noun)
        for attribute in adjectives
        for noun in plural_nouns
    ) == 878


def test_only_reviewed_descriptor_or_pp_rules_have_compatibility_premises() -> None:
    registry = load_project(CURATED).registry
    adjective_rules = {
        rule.id
        for rule in registry.rules
        if any(token.type == "adjective" for token in _rule_tokens(rule))
    }
    compatible_rules = {
        rule.id
        for rule in registry.rules
        if any(pred.attribute_compatible is not None for pred in rule.where)
    }

    assert adjective_rules == {
        "arithmetic/partition-attribute",
        "arithmetic/partition-attribute-fraction",
        "arithmetic/partition-attribute-of-noun",
        "arithmetic/partition-rest-attribute",
    }
    assert compatible_rules == {
        "arithmetic/located-quantity-event-context",
        "arithmetic/collection-two-shared-attributes",
        "arithmetic/collection-three-shared-attributes",
        "arithmetic/collection-four-shared-attributes",
        "arithmetic/located-class-population",
        "arithmetic/fronted-located-class-population",
        "arithmetic/resident-class-population",
        RULE_ID,
        "arithmetic/anaphoric-multiplier-conjunct-many",
        "arithmetic/as-many",
        "arithmetic/affine-fraction-as-many",
        "arithmetic/affine-times-as-many",
        "arithmetic/affine-times-as-much",
        "arithmetic/anchored-relation",
        "arithmetic/anchored-relation-conjoined-anchor",
        "arithmetic/anchored-relation-elided-standard",
        "arithmetic/anchored-relation-possessive-kinship-standard",
        "arithmetic/anchored-relation-postfix-dimension",
        "arithmetic/container-capacity-inquiry-frame",
        "arithmetic/container-capacity-progressive-inquiry-frame",
        "arithmetic/container-capacity-checking-inquiry-frame",
        "arithmetic/container-package-groups-totality-transfer",
        "arithmetic/container-package-contents-totality-transfer",
        "arithmetic/dangling-comparative-relation",
        "arithmetic/existential-premise",
        "arithmetic/existential-premise-distributive",
        "arithmetic/fraction-as-many",
        "arithmetic/fraction-as-many-elided-standard",
        "arithmetic/fraction-as-much",
        "arithmetic/fraction-as-much-elided-standard",
        "arithmetic/fraction-delta-relation",
        "arithmetic/fraction-delta-relation-mass",
        "arithmetic/partition-aggregate-share",
        "arithmetic/partition-rest-attribute",
        "arithmetic/recipient-counted-transfer-proportional-periods",
        "arithmetic/recipient-count-transfer-proportional-periods",
        "arithmetic/times-as-many",
        "arithmetic/times-as-many-conjunct",
        "arithmetic/times-as-many-conjunct-elided-standard",
        "arithmetic/times-as-many-conjunct-elided-item",
        "arithmetic/times-as-many-elided-standard",
        "arithmetic/times-as-many-possessive-kinship-standard",
        "arithmetic/times-as-much",
        "arithmetic/times-as-much-elided-standard",
        "arithmetic/times-the-number-of",
        "logic-arithmetic/coordinated-named-verbal-pp",
        "logic-arithmetic/ground-copular-nominal-pp",
        "logic-arithmetic/universal-all-have-quantity-pp",
        "logic-arithmetic/universal-all-have-quantity-pp-incompatible-item-safety",
    }


def test_compatibility_rule_remains_supported_after_g5j_expansion() -> None:
    availability = list_rule_availability(load_project(CURATED))

    assert sum(item.supported for item in availability) == 314
    target = next(item for item in availability if item.id == RULE_ID)
    assert target.supported
    assert target.blockers == ()


@pytest.mark.parametrize(
    "text",
    [
        "2 of the marbles are red.",
        "2 of the areas are large.",
        "2 of the books are left.",
    ],
)
def test_declared_core_category_pairs_match(text: str, registry) -> None:
    assert RULE_ID in _matched_rules(text, registry)


@pytest.mark.parametrize(
    "text",
    [
        "10 of the years are large.",
        "2 of the years are red.",
        "2 of the ages are left.",
    ],
)
def test_undeclared_category_pairs_are_absent(text: str, registry) -> None:
    assert RULE_ID not in _matched_rules(text, registry)


def test_all_standing_dev_pairs_remain_licensed() -> None:
    registry = load_project(GSM8K).registry
    expected = {
        ("yellow", "flower"),
        ("red", "flower"),
        ("full", "box"),
        ("ripe", "peach"),
        ("white", "rose"),
        ("good", "carrot"),
        ("red", "ticket"),
        ("married", "woman"),
    }

    assert all(
        registry.attribute_applies_to(attribute, noun)
        for attribute, noun in expected
    )


@pytest.mark.parametrize("seed", range(48))
def test_generation_never_selects_an_incompatible_pair(seed: int) -> None:
    project = load_project(CURATED)
    candidate = generate_candidate(project, rule_id=RULE_ID, seed=seed)
    attribute = candidate.requested_bindings["attr"]
    noun = project.registry.plural_to_singular[
        candidate.requested_bindings["coll"]
    ]

    assert candidate.target_status == "matched"
    assert project.registry.attribute_applies_to(attribute, noun)


def test_compatibility_explanation_names_and_sources_the_exact_pair() -> None:
    candidate = generate_candidate(
        load_project(CURATED), rule_id=RULE_ID, seed=0
    )
    premise = next(
        item
        for item in candidate.premises
        if item.kind == "where"
        and item.expression.startswith("attribute_compatible")
    )

    assert premise.status == "passed"
    assert "matched" in premise.reason
    assert " → " in premise.reason
    assert {
        "rule-where",
        "attribute-compatibility",
        "category",
        "category-member",
    } <= {source["kind"] for source in premise.sources}


def test_one_attribute_category_can_license_multiple_noun_categories(
    tmp_path: Path,
) -> None:
    _write_many_to_many_project(tmp_path)
    project = load_project(tmp_path)
    registry = project.registry

    assert registry.attribute_compatibility[
        "appearance_attribute"
    ] == ("display_noun", "solid_noun")
    assert registry.attribute_applies_to("bright", "pebble")
    assert registry.attribute_applies_to("bright", "cloud")
    assert not registry.attribute_applies_to("bright", "idea")
    assert "invented/compatible-description" in _matched_rules(
        "Two of the pebbles are bright.", registry
    )
    assert "invented/compatible-description" in _matched_rules(
        "Two of the clouds are bright.", registry
    )
    assert "invented/compatible-description" not in _matched_rules(
        "Two of the ideas are bright.", registry
    )

    for seed in range(24):
        candidate = generate_candidate(
            project,
            rule_id="invented/compatible-description",
            seed=seed,
            max_attempts=1,
            locked_bindings={"attr": "bright"},
        )
        assert candidate.requested_bindings["coll"] in {"pebbles", "clouds"}
        assert candidate.target_status == "matched"


def test_review_evidence_is_preserved_and_now_retests_absent() -> None:
    project = load_project(CURATED)
    history = [
        json.loads(line)
        for line in review_path(project).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    review = next(
        item for item in history if item["id"] == REVIEW_ID
    )

    assert review["sentence"] == "10 of the years are large."
    assert review["verdict"] == "invalid"
    assert RULE_ID not in _matched_rules(review["sentence"], project.registry)
