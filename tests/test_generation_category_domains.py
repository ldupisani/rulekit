"""Core-owned exploratory category domains.

Generation support is mechanical, not a linguistic-validity verdict.  These
tests keep every project-backed filler visible to the review workbench; human
reviews are expected to expose premises that need tightening.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
GSM8K = ROOT / "projects" / "gsm8k"
CORE_CATEGORIES = (ROOT / "packs/core-english/categories/core.yaml").resolve()
CORE_LEXICON = (ROOT / "packs/core-english/lexicon/core.yaml").resolve()

CORE_DOMAINS = {
    "aggregate_noun": {"amount", "number"},
    "quantity_anaphor": {"amount", "number"},
    "price_anaphor": {"cost", "price"},
    "remnant": {"remainder", "rest"},
    "finite_infinitival_goal_predicate": {
        "hope",
        "hoped",
        "hopes",
        "intend",
        "intended",
        "intends",
        "want",
        "wanted",
        "wants",
    },
    "direct_quantity_goal_predicate": {
        "need",
        "needed",
        "needs",
        "require",
        "required",
        "requires",
    },
    "purpose_resource_goal_activity": {
        "raise",
        "raised",
        "raises",
        "raising",
        "save",
        "saved",
        "saves",
        "saving",
    },
    "duration_verb": {"takes", "took"},
}

DOMAIN_RULES = {
    "arithmetic/extraposed-duration-rate",
    "arithmetic/fraction-of-remnant",
    "arithmetic/rest-of-pool",
    "arithmetic/goal-desire-quantity",
    "arithmetic/goal-need-quantity",
}


def test_all_profiled_domains_are_core_owned_without_project_shadowing() -> None:
    words = set().union(*CORE_DOMAINS.values())
    for project_root in (CURATED, GSM8K):
        project = load_project(project_root)

        for word in words:
            assert project.source_index.lexicon[word].path == CORE_LEXICON
        for category, members in CORE_DOMAINS.items():
            for member in members:
                assert project.registry.word_in_category(member, category)
                assert project.source_index.category_members[
                    (category, member)
                ].path == CORE_CATEGORIES


def test_mining_pack_can_extend_core_words_with_independent_categories() -> None:
    project = load_project(GSM8K)

    assert project.registry.word_in_category("take", "accompany")
    assert project.registry.word_in_category(
        "need", "direct_quantity_goal_predicate"
    )
    assert project.registry.word_in_category("cost", "price_verb")
    assert project.registry.word_in_category("cost", "dimension_noun")
    assert project.registry.word_in_category("cost", "currency_measure")


def test_category_domains_rule_availability(curated_availability) -> None:
    assert all(curated_availability[rule_id].supported for rule_id in DOMAIN_RULES)


@pytest.mark.parametrize("rule_id", sorted(DOMAIN_RULES))
def test_rules_with_category_domains_generate_reviewable_matches(
    rule_id: str,
) -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id=rule_id,
        seed=0,
    )

    assert candidate.generator_version == "g6-strict-boundary-modes"
    assert candidate.target_status in {"matched", "shadowed"}
    assert candidate.sentence
    assert rule_id in {match.rule_id for match in candidate.actual_matches}
