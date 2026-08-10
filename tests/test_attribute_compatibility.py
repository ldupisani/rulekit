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
            "{slot: attr, type: noun}",
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
        "beige",
        "blue",
        "business",
        "following",
        "green",
        "humanities",
        "large",
        "left",
        "old",
        "red",
        "remaining",
        "science",
        "small",
        "turquoise",
        "violet",
    }
    # The core generation vocabulary adds ordinary count nouns and three
    # explicitly colour-compatible adjectives. Core-owned literal adjective
    # `old` also remains outside every descriptor category. Compatibility
    # still comes from category membership, never broader lexical senses.
    # `head` and `university` are core-owned for the logic bridge, while
    # `topic` supports reviewed topical quantities. None silently gains
    # descriptor compatibility.
    assert len(plural_nouns) == 69
    assert {"head", "topic", "university"} <= plural_nouns
    assert sum(
        registry.attribute_applies_to(attribute, noun)
        for attribute in adjectives
        for noun in plural_nouns
    ) == 367


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
        RULE_ID,
        "arithmetic/as-many",
        "arithmetic/affine-fraction-as-many",
        "arithmetic/affine-times-as-many",
        "arithmetic/affine-times-as-much",
        "arithmetic/anchored-relation-elided-standard",
        "arithmetic/anchored-relation-possessive-kinship-standard",
        "arithmetic/anchored-relation-postfix-dimension",
        "arithmetic/dangling-comparative-relation",
        "arithmetic/existential-premise",
        "arithmetic/existential-premise-distributive",
        "arithmetic/fraction-as-many",
        "arithmetic/fraction-as-many-elided-standard",
        "arithmetic/fraction-as-much",
        "arithmetic/fraction-as-much-elided-standard",
        "arithmetic/fraction-delta-relation",
        "arithmetic/fraction-delta-relation-mass",
        "arithmetic/partition-rest-attribute",
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

    assert sum(item.supported for item in availability) == 125
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
