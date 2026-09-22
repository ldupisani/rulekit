"""Contextual synonyms preserve pairwise versus unique-meaning policies."""

from types import SimpleNamespace

from rulekit.kernel.predicate_compatibility import predicate_concepts, predicates_compatible


def registry(groups):
    return SimpleNamespace(context_synonyms=groups,
                           word_in_category=lambda theme, gate: theme == gate)


def test_predicate_meaning_is_local_to_the_object_category():
    reg = registry({"consumption": ("food", ("eat", "consume"))})
    assert predicates_compatible("eat", "consume", "food", reg)
    assert not predicates_compatible("eat", "consume", "fuel", reg)
    assert predicates_compatible("consume", "consume", "fuel", reg)


def test_overlapping_groups_do_not_create_transitive_synonyms():
    reg = registry({"one": ("item", ("a", "b")), "two": ("item", ("b", "c"))})
    assert predicates_compatible("a", "b", "item", reg)
    assert predicates_compatible("b", "c", "item", reg)
    assert not predicates_compatible("a", "c", "item", reg)


def test_lookup_preserves_ambiguity_for_the_consumer_to_decide():
    reg = registry({"one": ("item", ("a", "b")), "two": ("item", ("a", "b"))})
    left = predicate_concepts("a", "item", reg, fallback_to_verb=True)
    right = predicate_concepts("b", "item", reg, fallback_to_verb=True)
    assert len(left & right) == 2  # The sequence consumer must still decline.
    assert predicates_compatible("a", "b", "item", reg)  # Existing pairwise policy.


def test_unlicensed_fallback_does_not_treat_concept_labels_as_verbs():
    reg = registry({"a": ("item", ("b", "c"))})
    assert predicate_concepts("a", "item", reg) == frozenset()
    assert predicate_concepts("a", "item", reg, fallback_to_verb=True) == {"a"}
    assert not predicates_compatible("a", "b", "item", reg)
