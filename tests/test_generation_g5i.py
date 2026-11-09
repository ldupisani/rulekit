"""G5i: recursive optional-branch realization and inspection."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import (
    generate_candidate,
    generate_minimal_pair,
    list_rule_availability,
)


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"

NEWLY_SUPPORTED = {
    "arithmetic/as-many",
    "arithmetic/existential-premise-total",
    "arithmetic/fraction-as-many",
    "arithmetic/fraction-as-many-elided",
    "arithmetic/fraction-as-much",
    "arithmetic/fraction-as-much-elided",
    "arithmetic/group-total-sum-of-age",
    "arithmetic/group-total-trailing",
    "arithmetic/partition-rest-attribute",
    "arithmetic/partition-rest-membership",
    "arithmetic/times-as-many",
    "arithmetic/times-as-many-conjunct",
    "arithmetic/times-as-many-elided",
    "arithmetic/times-as-many-possessive-kinship-standard",
    "arithmetic/times-as-much",
    "arithmetic/times-as-much-elided",
    "arithmetic/times-frame-relation-clause",
    "arithmetic/times-the-number-of",
}


def _optional_profile(project) -> tuple[int, int, int, int]:
    rules = 0
    groups = 0
    nested = 0
    max_depth = 0

    def walk(tokens, depth: int = 1) -> bool:
        nonlocal groups, nested, max_depth
        found = False
        for token in tokens:
            if token.opt is None:
                continue
            found = True
            groups += 1
            nested += depth > 1
            max_depth = max(max_depth, depth)
            walk(token.opt, depth + 1)
        return found

    for rule in project.registry.rules:
        sentence = rule.match.get("sentence")
        if sentence and not isinstance(sentence[0], list) and walk(sentence):
            rules += 1
    return rules, groups, nested, max_depth


def test_g5i_profiles_the_complete_recursive_optional_class() -> None:
    project = load_project(CURATED)

    # The measurement-event shapes and the partition aggregate share admit
    # their scoped optional modifiers. Goal progress additionally admits the
    # explicit fraction marker in "one third of the money", while committed
    # transfers admit the bounded "for that purpose" adjunct. Nesting and the
    # established maximum depth stay unchanged. The rate-premium definition
    # adds one optional fraction-of marker. Carrier sequences add optional
    # origin, event preposition, motive, and construction background groups.
    # The shared comparison family adds four item-layout variants and nine
    # additive-discourse positions; it does not add nesting depth.
    # Equal-price purchases add one optional additive continuation.
    # Liability entries add six optional dates, two draw-frame options and
    # a nested temporal preposition within the demonstrative time adjunct.
    # Loading adds an optional particle and an initial-state adjunct.
    # Mixture frames retain optional holders, solvents, bases and retention
    # quantifiers without increasing the maximum optional nesting depth.
    # Amount references and itemized quote variants add flat optional groups.
    # Content comparisons allow an omitted standard predicate in two forms.
    # Holder comparisons admit a repeated predicate while an optional object
    # beneath it still distinguishes the fuller item-comparison construction.
    # The "in all" total marker rejects a following collection or partitive.
    # Resource contexts, destination ownership, coordinated package quotes,
    # and store-loss variants add flat groups without increasing nesting.
    # Eight scoped recurring-expense forms add optional focus markers.
    # Fractional sources add definite articles and optional residual-stock names.
    # Assessment frames and counted partitives reuse flat frequency/attribute options.
    # Scoped schedules, source partitions and daily goals add bounded optional frames.
    # Service partitives and the payment/deadline paraphrases add flat options.
    assert _optional_profile(project) == (420, 716, 66, 3)


def test_g5i_rules_remain_supported_after_g5j_expansion() -> None:
    availability = {
        item.id: item
        for item in list_rule_availability(load_project(CURATED))
    }

    assert len(availability) == 915
    assert sum(item.supported for item in availability.values()) == 814
    assert sum(not item.supported for item in availability.values()) == 101
    assert all(availability[rule_id].supported for rule_id in NEWLY_SUPPORTED)
    assert all(
        "optional groups have no current realizer" not in item.blockers
        for item in availability.values()
    )


def test_unsupported_optional_descendants_remain_explicit_blockers() -> None:
    availability = {
        item.id: item
        for item in list_rule_availability(load_project(CURATED))
    }

    # G5u subsequently supplied the loaded direct-adverb domain.
    assert availability[
        "arithmetic/anchored-relation-conjoined-anchor"
    ].supported


@pytest.mark.parametrize("rule_id", sorted(NEWLY_SUPPORTED))
def test_every_new_optional_rule_generates_a_reviewable_match(
    rule_id: str,
) -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id=rule_id,
        seed=0,
    )

    assert candidate.generator_version == "g6-strict-boundary-modes"
    assert candidate.target_status == "matched"
    optional_rows = [
        premise
        for premise in candidate.premises
        if premise.slot_type == "optional"
    ]
    assert optional_rows
    assert all(
        row.binding in {"included", "omitted", "inactive"}
        for row in optional_rows
    )
    assert all(
        row.sources and row.sources[0]["kind"] == "rule-token"
        for row in optional_rows
    )


def test_included_and_omitted_branches_are_both_inspectable() -> None:
    from rulekit.generation.sample import _token_nodes

    project = load_project(CURATED)
    rule = next(rule for rule in project.registry.rules
                if rule.id == "arithmetic/partition-rest-attribute")
    optional = next(index for index, (_, token, _) in enumerate(
        _token_nodes(rule.match["sentence"])
    ) if token.opt)
    included = generate_candidate(
        project,
        rule_id="arithmetic/partition-rest-attribute",
        seed=0,
        structural_target=f"optional:{optional}:included",
    )
    omitted = generate_candidate(
        project,
        rule_id="arithmetic/partition-rest-attribute",
        seed=2,
        structural_target=f"optional:{optional}:omitted",
    )

    included_optional = next(
        row for row in included.premises if row.slot_type == "optional"
    )
    omitted_optional = next(
        row for row in omitted.premises if row.slot_type == "optional"
    )
    assert included_optional.binding == "included"
    assert omitted_optional.binding == "omitted"

    included_item = next(row for row in included.premises if row.slot == "item")
    omitted_item = next(row for row in omitted.premises if row.slot == "item")
    assert included_item.status == "passed"
    assert included_item.binding
    assert omitted_item.status == "unverified"
    assert omitted_item.binding is None
    assert included_item.sources[0]["label"].endswith("token 2.3")
    assert omitted_item.sources[0]["label"].endswith("token 2.3")


@pytest.mark.parametrize('comparison', ['difference', 'multiple'])
@pytest.mark.parametrize('branch', ['included', 'omitted'])
def test_content_comparison_standard_predicate_generates_both_forms(comparison, branch):
    from rulekit.generation.sample import _token_nodes

    project = load_project(CURATED)
    rule_id = f'arithmetic/comparison-repeated-predicate-{comparison}-content'
    rule = next(rule for rule in project.registry.rules if rule.id == rule_id)
    optional = next(index for index, (_, token, _) in enumerate(
        _token_nodes(rule.match['sentence'])
    ) if token.opt)
    candidate = generate_candidate(
        project, rule_id=rule_id, seed=0,
        structural_target=f'optional:{optional}:{branch}',
    )
    assert candidate.target_status == 'matched'
    assert next(row.binding for row in candidate.premises
                if row.slot_type == 'optional') == branch


def test_nested_omission_is_distinct_from_an_inactive_child_group() -> None:
    from rulekit.generation.sample import _token_nodes

    project = load_project(CURATED)
    rule = next(rule for rule in project.registry.rules
                if rule.id == "arithmetic/times-as-many")
    parent = next(index for index, (_, token, _) in enumerate(
        _token_nodes(rule.match["sentence"])
    ) if token.opt and any(child.opt is not None for child in token.opt))
    candidate = generate_candidate(
        project,
        rule_id="arithmetic/times-as-many",
        seed=1,
        # Pin the structural outcome under test rather than depending on
        # vocabulary-dependent random draws selecting this optional branch.
        structural_target=f"optional:{parent}:omitted",
    )
    choices = [
        row.binding
        for row in candidate.premises
        if row.slot_type == "optional"
    ]

    assert "omitted" in choices
    assert "inactive" in choices
    assert any(
        row.status == "unverified"
        and "omitted optional branch" in row.reason
        for row in candidate.premises
    )


def test_minimal_pair_preserves_an_included_optional_binding() -> None:
    project = load_project(CURATED)
    before = generate_candidate(
        project,
        rule_id="arithmetic/partition-rest-attribute",
        seed=0,
        # The compatibility boundary deliberately gives temporal collections
        # only the remnant adjective ("years left").  Use a collection with
        # more than one valid predicate so rerolling attr remains satisfiable
        # while this test continues to exercise optional-binding preservation.
        locked_bindings={"item": "apples"},
    )
    paired = generate_minimal_pair(
        project,
        rule_id=before.target_rule,
        base_seed=before.seed,
        original_bindings=before.requested_bindings,
        reroll_slot="attr",
    )

    assert paired.requested_bindings["item"] == before.requested_bindings["item"]
    assert next(
        row.binding
        for row in paired.premises
        if row.slot_type == "optional"
    ) == "included"
