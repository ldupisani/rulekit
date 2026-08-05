"""G5g: core-owned age data and category-qualified possessive generation.

Synthetic sentences only.  The pack-ownership move is tested independently
from the generic structural machinery so a future category can reuse it.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from rulekit.data.project import load_project
from rulekit.data.schemas import MatchToken, WherePredicate
from rulekit.generation import generate_candidate, list_rule_availability
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Relation


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
GSM8K = ROOT / "projects" / "gsm8k"
CORE_CATEGORIES = (ROOT / "packs/core-english/categories/core.yaml").resolve()
CORE_LEXICON = (ROOT / "packs/core-english/lexicon/core.yaml").resolve()

NEWLY_SUPPORTED = {
    "arithmetic/group-total-of-age",
    "arithmetic/times-as-old-as-possessive-standard",
    "arithmetic/times-as-old-as-both-possessive",
}


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


def test_age_lexicon_and_all_generic_memberships_are_core_owned() -> None:
    for project_root in (CURATED, GSM8K):
        project = load_project(project_root)

        assert project.source_index.lexicon["age"].path == CORE_LEXICON
        for category in ("age_noun", "dimension_noun", "time_measure"):
            assert project.source_index.category_members[
                (category, "age")
            ].path == CORE_CATEGORIES


def test_age_noun_has_one_complete_occurrence_set() -> None:
    project = load_project(CURATED)
    occurrences = {
        (
            rule.id,
            token.slot,
            token.possessed,
            token.number,
        )
        for rule in project.registry.rules
        for token in _rule_tokens(rule)
        if token.cat == "age_noun"
    }

    assert occurrences == {
        (
            "arithmetic/group-total-of-age",
            "noun",
            False,
            None,
        ),
        (
            "arithmetic/group-total-sum-of-age",
            "noun",
            False,
            "plural",
        ),
        (
            "arithmetic/times-as-old-as-possessive-standard",
            "std",
            True,
            "singular",
        ),
        (
            "arithmetic/times-as-old-as-both-possessive",
            "who",
            True,
            "singular",
        ),
        (
            "arithmetic/times-as-old-as-both-possessive",
            "std",
            True,
            "singular",
        ),
    }


def test_g5g_rules_remain_supported_after_later_increments() -> None:
    project = load_project(CURATED)
    availability = {
        item.id: item for item in list_rule_availability(project)
    }

    assert all(availability[rule_id].supported for rule_id in NEWLY_SUPPORTED)
    assert availability["arithmetic/group-total-sum-of-age"].supported


@pytest.mark.parametrize("seed", range(12))
def test_group_total_age_generates_and_round_trips(seed: int) -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id="arithmetic/group-total-of-age",
        seed=seed,
    )

    assert candidate.target_status == "matched"
    assert candidate.requested_bindings["noun"] == "age"
    assert any(
        fact["type"] == "GroupTotal"
        and fact["fields"]["measure"] == "year"
        for fact in candidate.facts
    )


@pytest.mark.parametrize("seed", range(24))
def test_one_sided_age_relation_generates_a_singular_owned_age(seed: int) -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id="arithmetic/times-as-old-as-possessive-standard",
        seed=seed,
    )

    assert candidate.target_status == "matched"
    assert candidate.requested_bindings["verb"] in {"is", "was"}
    assert candidate.requested_bindings["std"].endswith("'s age")
    premise = next(
        item for item in candidate.premises if item.slot == "std"
    )
    assert premise.slot_type == "age_noun"
    assert "possessed category" in premise.reason
    assert {"generation-fixture", "contraction", "lexicon",
            "category-member", "category"} <= {
        source["kind"] for source in premise.sources
    }


@pytest.mark.parametrize("seed", range(24))
def test_double_age_relation_generates_distinct_singular_owners(
    seed: int,
) -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id="arithmetic/times-as-old-as-both-possessive",
        seed=seed,
    )

    assert candidate.target_status == "matched"
    assert candidate.requested_bindings["verb"] in {"is", "was"}
    left = candidate.requested_bindings["who"]
    right = candidate.requested_bindings["std"]
    assert left.endswith("'s age")
    assert right.endswith("'s age")
    assert left.split("'s ", 1)[0] != right.split("'s ", 1)[0]
    owner_premise = next(
        item
        for item in candidate.premises
        if item.kind == "where" and item.expression.startswith("distinct_owner")
    )
    assert owner_premise.status == "passed"
    assert "distinct owners" in owner_premise.reason


@pytest.mark.parametrize(
    ("text", "rule_id"),
    [
        (
            "Aven is twice Bira's age.",
            "arithmetic/times-as-old-as-possessive-standard",
        ),
        (
            "Aven's age was twice Bira's age.",
            "arithmetic/times-as-old-as-both-possessive",
        ),
    ],
)
def test_owned_age_surfaces_match_and_emit_owner_scoped_relations(
    text: str, rule_id: str, registry
) -> None:
    result = solve(text, registry)
    assert rule_id in {
        match.match.rule.id for match in result.document.rule_results[0]
    }
    relation = next(
        fact
        for fact in result.store.by_kind(Relation)
        if fact.provenance.source == rule_id
    )
    assert relation.subject == "aven"
    assert relation.standard == "bira"
    assert relation.measure == "year"
    assert relation.factor == 2


@pytest.mark.parametrize(
    ("text", "rule_id"),
    [
        (
            "Aven is twice age.",
            "arithmetic/times-as-old-as-possessive-standard",
        ),
        (
            "Aven is twice Bira's ages.",
            "arithmetic/times-as-old-as-possessive-standard",
        ),
        (
            "Aven owns twice Bira's age.",
            "arithmetic/times-as-old-as-possessive-standard",
        ),
        (
            "Aven's age is twice Aven's age.",
            "arithmetic/times-as-old-as-both-possessive",
        ),
        (
            "Aven's ages are twice Bira's ages.",
            "arithmetic/times-as-old-as-both-possessive",
        ),
    ],
)
def test_owned_age_rules_reject_bare_plural_non_copular_and_self_relations(
    text: str, rule_id: str, registry
) -> None:
    assert rule_id not in _matched_rules(text, registry)


def test_possessed_category_and_number_are_explicit_schema_qualifiers() -> None:
    token = MatchToken(
        slot="asset",
        cat="invented_asset",
        possessed=True,
        number="singular",
    )
    assert token.possessed
    assert token.number == "singular"
    assert WherePredicate(distinct_owner=["left", "right"]).distinct_owner

    with pytest.raises(
        ValidationError, match="only qualifies a category-gated slot"
    ):
        MatchToken(slot="asset", type="possessed", possessed=True)
    with pytest.raises(ValidationError, match="both counted and possessed"):
        MatchToken(
            slot="asset",
            cat="invented_asset",
            counted=True,
            possessed=True,
        )


def _write_invented_project(root: Path) -> None:
    pack = root / "pack"
    pack.mkdir(parents=True)
    (root / "project.yaml").write_text(
        "format: rulekit/project@1\nname: invented-g5g\npacks: [./pack]\n"
    )
    (root / "generation.yaml").write_text(
        "format: rulekit/generation@1\nnames: [Luma, Navo, Pera]\n"
    )
    (pack / "pack.yaml").write_text(
        "format: rulekit/pack@1\nname: invented-g5g\n"
    )
    (pack / "lexicon.yaml").write_text(
        """\
format: rulekit/lexicon@1
entries:
  "'s": {senses: [possessive]}
  equals: {senses: [verb], number: singular, verb: {lemma: equal}}
  relic: {senses: [noun], plural: relics}
"""
    )
    (pack / "categories.yaml").write_text(
        """\
format: rulekit/categories@1
categories:
  invented_asset: {parent: noun}
  invented_copula: {parent: verb}
members:
  invented_asset: [relic]
  invented_copula: [equals]
"""
    )
    (pack / "contractions.yaml").write_text(
        """\
format: rulekit/contractions@1
expansions:
  "'s": "'s"
"""
    )
    (pack / "rules.yaml").write_text(
        """\
format: rulekit/rules@1
rules:
  - id: invented/owned-relation
    phase: read
    match:
      sentence:
        - {slot: left, cat: invented_asset, possessed: true, number: singular}
        - {slot: verb, cat: invented_copula}
        - {slot: right, cat: invented_asset, possessed: true, number: singular}
    where:
      - distinct_owner: [left, right]
    emits:
      - fact: predication
        subject: "{left.owner}"
        verb: "{verb}"
        dobj: "{right.owner}"
"""
    )


def test_qualified_possession_is_generic_not_age_specific(
    tmp_path: Path,
) -> None:
    _write_invented_project(tmp_path)
    project = load_project(tmp_path)

    for seed in range(12):
        candidate = generate_candidate(
            project, rule_id="invented/owned-relation", seed=seed
        )
        assert candidate.target_status == "matched"
        assert candidate.requested_bindings["left"].endswith("'s relic")
        assert candidate.requested_bindings["right"].endswith("'s relic")
        assert (
            candidate.requested_bindings["left"].split("'s ", 1)[0]
            != candidate.requested_bindings["right"].split("'s ", 1)[0]
        )
